# Add this to finance_workflows/execution_tracker.py

import time
import logging
from typing import Dict, List, Any
import json

logger = logging.getLogger(__name__)


class GoTExecutionTracker:
    """Enhanced execution tracker for Graph of Thoughts workflows."""
    
    def __init__(self):
        self.start_time = None
        self.operations_data = []
        self.execution_events = []
        self.current_operation_index = 0
        self.workflow_metadata = {}
        
    def initialize_tracking(self, operations_graph, workflow_type, session_id):
        """Initialize tracking for a workflow execution."""
        self.start_time = time.time()
        self.workflow_metadata = {
            'workflow_type': workflow_type,
            'session_id': session_id,
            'start_time': self.start_time
        }
        
        # Initialize operation tracking data
        self.operations_data = []
        for i, operation in enumerate(operations_graph.operations):
            op_data = {
                'id': f"{operation.__class__.__name__}_{i}",
                'type': operation.__class__.__name__,
                'index': i,
                'status': 'pending',
                'thoughts_generated': 0,
                'execution_time': 0,
                'start_time': None,
                'end_time': None,
                'error': None,
                'parameters': self._extract_operation_parameters(operation),
                'predecessors': [f"{pred.__class__.__name__}_{j}" for j, pred in enumerate(operations_graph.operations) if pred in operation.predecessors],
                'cost_estimate': self._estimate_operation_cost(operation)
            }
            self.operations_data.append(op_data)
        
        logger.info(f"Initialized tracking for {len(self.operations_data)} operations")
    
    def start_operation(self, operation):
        """Mark an operation as started."""
        op_data = self._find_operation_data(operation)
        if op_data:
            op_data['status'] = 'running'
            op_data['start_time'] = time.time()
            
            event = {
                'operation_id': op_data['id'],
                'operation_type': op_data['type'],
                'event': 'started',
                'timestamp': time.time() - self.start_time,
                'thoughts': 0,
                'details': f"Started {op_data['type']} operation"
            }
            self.execution_events.append(event)
            logger.info(f"Started operation: {op_data['type']} (index: {op_data['index']})")
    
    def complete_operation(self, operation, thoughts_generated=0):
        """Mark an operation as completed."""
        op_data = self._find_operation_data(operation)
        if op_data:
            end_time = time.time()
            op_data['status'] = 'completed'
            op_data['end_time'] = end_time
            op_data['execution_time'] = end_time - (op_data['start_time'] or end_time)
            op_data['thoughts_generated'] = thoughts_generated
            
            event = {
                'operation_id': op_data['id'],
                'operation_type': op_data['type'],
                'event': 'completed',
                'timestamp': end_time - self.start_time,
                'execution_time': op_data['execution_time'],
                'thoughts': thoughts_generated,
                'success': True,
                'details': f"Completed {op_data['type']} - generated {thoughts_generated} thoughts"
            }
            self.execution_events.append(event)
            logger.info(f"Completed operation: {op_data['type']} ({thoughts_generated} thoughts, {op_data['execution_time']:.2f}s)")
    
    def fail_operation(self, operation, error_message):
        """Mark an operation as failed."""
        op_data = self._find_operation_data(operation)
        if op_data:
            end_time = time.time()
            op_data['status'] = 'failed'
            op_data['end_time'] = end_time
            op_data['execution_time'] = end_time - (op_data['start_time'] or end_time)
            op_data['error'] = str(error_message)
            
            event = {
                'operation_id': op_data['id'],
                'operation_type': op_data['type'],
                'event': 'failed',
                'timestamp': end_time - self.start_time,
                'execution_time': op_data['execution_time'],
                'error': str(error_message),
                'success': False,
                'details': f"Failed {op_data['type']} - {error_message}"
            }
            self.execution_events.append(event)
            logger.error(f"Failed operation: {op_data['type']} - {error_message}")
    
    def get_execution_trace(self):
        """Get complete execution trace data."""
        total_time = time.time() - self.start_time if self.start_time else 0
        total_thoughts = sum(op['thoughts_generated'] for op in self.operations_data)
        completed_ops = sum(1 for op in self.operations_data if op['status'] == 'completed')
        
        return {
            'operations': self.operations_data,
            'events': self.execution_events,
            'total_time': total_time,
            'total_thoughts': total_thoughts,
            'completion_rate': completed_ops / len(self.operations_data) if self.operations_data else 0,
            'workflow_metadata': self.workflow_metadata
        }
    
    def get_graph_definition(self):
        """Get graph definition for visualization."""
        return [
            {
                'id': op['id'],
                'type': op['type'],
                'index': op['index'],
                'predecessors': op['predecessors'],
                'parameters': op['parameters'],
                'cost_estimate': op['cost_estimate']
            }
            for op in self.operations_data
        ]
    
    def _find_operation_data(self, operation):
        """Find operation data by operation instance."""
        op_type = operation.__class__.__name__
        # Find the first pending or running operation of this type
        for op_data in self.operations_data:
            if (op_data['type'] == op_type and 
                op_data['status'] in ['pending', 'running']):
                return op_data
        return None
    
    def _extract_operation_parameters(self, operation):
        """Extract parameters from an operation instance."""
        params = {}
        
        # Common parameters to extract
        param_names = [
            'num_branches_prompt', 'num_branches_response', 'num_samples',
            'num_responses', 'n', 'higher_is_better', 'improve', 'num_tries'
        ]
        
        for param_name in param_names:
            if hasattr(operation, param_name):
                params[param_name] = getattr(operation, param_name)
        
        return params
    
    def _estimate_operation_cost(self, operation):
        """Estimate the cost of an operation."""
        base_costs = {
            'Generate': 0.02,
            'Score': 0.01,
            'KeepBestN': 0.0,
            'Aggregate': 0.03,
            'ValidateAndImprove': 0.04,
            'Improve': 0.02,
            'KeepValid': 0.0,
            'Selector': 0.0,
            'GroundTruth': 0.01
        }
        
        base_cost = base_costs.get(operation.__class__.__name__, 0.01)
        
        # Apply multipliers based on parameters
        multiplier = 1
        if hasattr(operation, 'num_branches_prompt'):
            multiplier *= operation.num_branches_prompt
        elif hasattr(operation, 'num_samples'):
            multiplier *= operation.num_samples
        elif hasattr(operation, 'num_responses'):
            multiplier *= operation.num_responses
        
        return base_cost * multiplier


def create_tracked_controller(lm, operations_graph, prompter, parser, problem_parameters, workflow_type, session_id):
    """Create a controller with execution tracking."""
    from finance_workflows.local_got import controller
    
    # Create tracker
    tracker = GoTExecutionTracker()
    tracker.initialize_tracking(operations_graph, workflow_type, session_id)
    
    # Create controller
    ctrl = controller.Controller(lm, operations_graph, prompter, parser, problem_parameters)
    
    # Monkey patch the controller's run method to add tracking
    original_run = ctrl.run
    
    def tracked_run():
        logger.info("Starting tracked GoT execution")
        
        # Hook into each operation's execute method
        for operation in operations_graph.operations:
            original_execute = operation.execute
            
            def make_tracked_execute(op, original_exec):
                def tracked_execute(*args, **kwargs):
                    tracker.start_operation(op)
                    try:
                        result = original_exec(*args, **kwargs)
                        # Count thoughts generated
                        thoughts_count = len(op.get_thoughts()) if hasattr(op, 'get_thoughts') else 0
                        tracker.complete_operation(op, thoughts_count)
                        return result
                    except Exception as e:
                        tracker.fail_operation(op, str(e))
                        raise
                return tracked_execute
            
            operation.execute = make_tracked_execute(operation, original_execute)
        
        # Run the original execution
        try:
            result = original_run()
            logger.info("Tracked GoT execution completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tracked GoT execution failed: {e}")
            raise
    
    ctrl.run = tracked_run
    ctrl.tracker = tracker  # Attach tracker to controller for access
    
    return ctrl
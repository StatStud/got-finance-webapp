"""
Event Emitter Module for Graph of Thoughts Finance Web App

Singleton event emitter for GoT operations
Wraps SocketIO emit functionality
Used by controller to broadcast execution events

This module provides a centralized event emission system that allows
the GoT controller to broadcast real-time updates to connected clients
during operation execution.
"""

import logging
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from collections import defaultdict, deque
from flask import has_request_context, request
from flask_socketio import emit

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventBuffer:
    """
    Thread-safe buffer for storing events when no Flask context is available
    """
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.lock = threading.RLock()
    
    def add_event(self, event_name: str, data: Dict[str, Any], room: Optional[str] = None):
        """Add an event to the buffer"""
        with self.lock:
            event = {
                'event_name': event_name,
                'data': data,
                'room': room,
                'timestamp': datetime.utcnow().isoformat(),
                'id': str(uuid.uuid4())
            }
            self.buffer.append(event)
            logger.debug(f"Buffered event: {event_name} (buffer size: {len(self.buffer)})")
    
    def get_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get events from buffer"""
        with self.lock:
            if limit:
                return list(self.buffer)[-limit:]
            return list(self.buffer)
    
    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()
            logger.debug("Event buffer cleared")


class ExecutionTracker:
    """
    Tracks execution state and metrics for sessions
    """
    
    def __init__(self):
        self.sessions = defaultdict(lambda: {
            'start_time': None,
            'end_time': None,
            'status': 'idle',
            'operations': {},
            'total_cost': 0.0,
            'total_thoughts': 0,
            'error_count': 0,
            'paused': False,
            'pause_time': None,
            'total_pause_duration': 0.0
        })
        self.lock = threading.RLock()
    
    def start_execution(self, session_id: str, workflow_id: str):
        """Start tracking execution for a session"""
        with self.lock:
            session = self.sessions[session_id]
            session['start_time'] = time.time()
            session['status'] = 'running'
            session['workflow_id'] = workflow_id
            session['operations'] = {}
            session['total_cost'] = 0.0
            session['total_thoughts'] = 0
            session['error_count'] = 0
            session['paused'] = False
            session['total_pause_duration'] = 0.0
            logger.info(f"Started execution tracking for session {session_id}")
    
    def complete_execution(self, session_id: str):
        """Complete execution tracking"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session['end_time'] = time.time()
                session['status'] = 'completed'
                if session['paused'] and session['pause_time']:
                    session['total_pause_duration'] += time.time() - session['pause_time']
                    session['paused'] = False
                logger.info(f"Completed execution tracking for session {session_id}")
    
    def pause_execution(self, session_id: str):
        """Pause execution"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                session['paused'] = True
                session['pause_time'] = time.time()
                session['status'] = 'paused'
                logger.info(f"Paused execution for session {session_id}")
    
    def resume_execution(self, session_id: str):
        """Resume execution"""
        with self.lock:
            if session_id in self.sessions:
                session = self.sessions[session_id]
                if session['paused'] and session['pause_time']:
                    session['total_pause_duration'] += time.time() - session['pause_time']
                session['paused'] = False
                session['pause_time'] = None
                session['status'] = 'running'
                logger.info(f"Resumed execution for session {session_id}")
    
    def add_operation(self, session_id: str, operation_id: str, operation_data: Dict[str, Any]):
        """Add operation to tracking"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['operations'][operation_id] = {
                    'start_time': time.time(),
                    'end_time': None,
                    'cost': 0.0,
                    'thoughts_generated': 0,
                    'status': 'running',
                    **operation_data
                }
    
    def complete_operation(self, session_id: str, operation_id: str, cost: float, thoughts_count: int):
        """Complete operation tracking"""
        with self.lock:
            if session_id in self.sessions and operation_id in self.sessions[session_id]['operations']:
                operation = self.sessions[session_id]['operations'][operation_id]
                operation['end_time'] = time.time()
                operation['cost'] = cost
                operation['thoughts_generated'] = thoughts_count
                operation['status'] = 'completed'
                
                # Update session totals
                session = self.sessions[session_id]
                session['total_cost'] += cost
                session['total_thoughts'] += thoughts_count
    
    def add_error(self, session_id: str, error_info: Dict[str, Any]):
        """Add error to tracking"""
        with self.lock:
            if session_id in self.sessions:
                self.sessions[session_id]['error_count'] += 1
                if 'errors' not in self.sessions[session_id]:
                    self.sessions[session_id]['errors'] = []
                self.sessions[session_id]['errors'].append({
                    'timestamp': time.time(),
                    **error_info
                })
    
    def get_session_metrics(self, session_id: str) -> Dict[str, Any]:
        """Get metrics for a session"""
        with self.lock:
            if session_id not in self.sessions:
                return {}
            
            session = self.sessions[session_id]
            current_time = time.time()
            
            # Calculate execution time
            if session['start_time']:
                if session['end_time']:
                    execution_time = session['end_time'] - session['start_time']
                else:
                    execution_time = current_time - session['start_time']
                
                # Subtract pause duration
                pause_duration = session['total_pause_duration']
                if session['paused'] and session['pause_time']:
                    pause_duration += current_time - session['pause_time']
                
                execution_time -= pause_duration
            else:
                execution_time = 0
            
            return {
                'session_id': session_id,
                'status': session['status'],
                'execution_time': execution_time,
                'total_cost': session['total_cost'],
                'total_thoughts': session['total_thoughts'],
                'operations_count': len(session['operations']),
                'error_count': session['error_count'],
                'paused': session['paused'],
                'operations': dict(session['operations'])
            }


class EventEmitter:
    """
    Singleton event emitter for GoT operations
    Provides centralized event broadcasting with SocketIO integration
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EventEmitter, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.buffer = EventBuffer()
        self.tracker = ExecutionTracker()
        self.current_session = None
        self.current_workflow = None
        self.enabled = True
        self.debug_mode = False
        
        # Event callbacks for custom handling
        self.event_callbacks = defaultdict(list)
        
        logger.info("EventEmitter initialized")
    
    def set_debug_mode(self, enabled: bool):
        """Enable or disable debug mode"""
        self.debug_mode = enabled
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'}")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable event emission"""
        self.enabled = enabled
        logger.info(f"Event emission {'enabled' if enabled else 'disabled'}")
    
    def set_current_session(self, session_id: str, workflow_id: str = None):
        """Set the current session for event emission"""
        self.current_session = session_id
        self.current_workflow = workflow_id
        if workflow_id:
            self.tracker.start_execution(session_id, workflow_id)
        logger.info(f"Current session set to: {session_id}")
    
    def clear_current_session(self):
        """Clear the current session"""
        if self.current_session:
            self.tracker.complete_execution(self.current_session)
        self.current_session = None
        self.current_workflow = None
        logger.info("Current session cleared")
    
    def add_event_callback(self, event_name: str, callback):
        """Add a callback for specific events"""
        self.event_callbacks[event_name].append(callback)
        logger.debug(f"Added callback for event: {event_name}")
    
    def remove_event_callback(self, event_name: str, callback):
        """Remove a callback for specific events"""
        if callback in self.event_callbacks[event_name]:
            self.event_callbacks[event_name].remove(callback)
            logger.debug(f"Removed callback for event: {event_name}")
    
    def emit_event(self, event_name: str, data: Dict[str, Any], room: Optional[str] = None):
        """
        Emit an event via SocketIO or buffer it if no context is available
        
        Args:
            event_name: Name of the event to emit
            data: Event data to send
            room: Optional room to emit to (defaults to current session)
        """
        if not self.enabled:
            return
        
        # Use current session as room if not specified
        if room is None and self.current_session:
            room = self.current_session
        
        # Add metadata to event data
        enhanced_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': self.current_session,
            'workflow_id': self.current_workflow,
            **data
        }
        
        # Execute custom callbacks
        for callback in self.event_callbacks.get(event_name, []):
            try:
                callback(event_name, enhanced_data)
            except Exception as e:
                logger.error(f"Error in event callback for {event_name}: {e}")
        
        # Try to emit via SocketIO
        try:
            if has_request_context():
                emit(event_name, enhanced_data, room=room, namespace='/')
                if self.debug_mode:
                    logger.debug(f"Emitted event: {event_name} to room: {room}")
            else:
                # No Flask context, buffer the event
                self.buffer.add_event(event_name, enhanced_data, room)
                if self.debug_mode:
                    logger.debug(f"Buffered event: {event_name}")
        except Exception as e:
            logger.error(f"Error emitting event {event_name}: {e}")
            # Fallback to buffering
            self.buffer.add_event(event_name, enhanced_data, room)
    
    def emit_operation_start(self, operation_id: str, operation_type: str, 
                           predecessors: List[str] = None, parameters: Dict[str, Any] = None):
        """Emit operation start event"""
        data = {
            'id': operation_id,
            'type': operation_type,
            'predecessors': predecessors or [],
            'parameters': parameters or {},
            'start_time': time.time()
        }
        
        # Track operation
        if self.current_session:
            self.tracker.add_operation(self.current_session, operation_id, data)
        
        self.emit_event('operation_start', data)
    
    def emit_operation_complete(self, operation_id: str, thoughts: List[Dict[str, Any]], 
                              cost: float, execution_time: float = None, 
                              max_score: float = None):
        """Emit operation completion event"""
        data = {
            'id': operation_id,
            'thoughts': thoughts,
            'cost': cost,
            'execution_time': execution_time,
            'max_score': max_score,
            'end_time': time.time()
        }
        
        # Track operation completion
        if self.current_session:
            self.tracker.complete_operation(
                self.current_session, operation_id, cost, len(thoughts)
            )
        
        self.emit_event('operation_complete', data)
        
        # Also emit cost update
        self.emit_cost_update()
    
    def emit_operation_error(self, operation_id: str, error_message: str, 
                           error_type: str = 'execution_error'):
        """Emit operation error event"""
        data = {
            'id': operation_id,
            'error': error_message,
            'error_type': error_type,
            'timestamp': time.time()
        }
        
        # Track error
        if self.current_session:
            self.tracker.add_error(self.current_session, {
                'operation_id': operation_id,
                'error': error_message,
                'error_type': error_type
            })
        
        self.emit_event('operation_error', data)
    
    def emit_thoughts_generated(self, operation_id: str, thoughts: List[Dict[str, Any]]):
        """Emit thoughts generation event"""
        data = {
            'operation_id': operation_id,
            'thoughts': thoughts,
            'count': len(thoughts)
        }
        self.emit_event('thoughts_generated', data)
    
    def emit_thoughts_scored(self, operation_id: str, thoughts: List[Dict[str, Any]], 
                           scores: List[float]):
        """Emit thoughts scoring event"""
        data = {
            'operation_id': operation_id,
            'thoughts': thoughts,
            'scores': scores,
            'max_score': max(scores) if scores else 0,
            'min_score': min(scores) if scores else 0,
            'avg_score': sum(scores) / len(scores) if scores else 0
        }
        self.emit_event('thoughts_scored', data)
    
    def emit_execution_started(self, workflow_id: str, total_operations: int = None):
        """Emit execution start event"""
        data = {
            'workflow_id': workflow_id,
            'total_operations': total_operations,
            'start_time': time.time()
        }
        self.emit_event('execution_started', data)
    
    def emit_execution_completed(self, workflow_id: str, summary: Dict[str, Any] = None):
        """Emit execution completion event"""
        # Get session metrics
        metrics = {}
        if self.current_session:
            metrics = self.tracker.get_session_metrics(self.current_session)
        
        data = {
            'workflow_id': workflow_id,
            'end_time': time.time(),
            'summary': summary or {},
            'metrics': metrics
        }
        self.emit_event('execution_completed', data)
    
    def emit_execution_paused(self):
        """Emit execution pause event"""
        if self.current_session:
            self.tracker.pause_execution(self.current_session)
        
        data = {'paused_at': time.time()}
        self.emit_event('execution_paused', data)
    
    def emit_execution_resumed(self):
        """Emit execution resume event"""
        if self.current_session:
            self.tracker.resume_execution(self.current_session)
        
        data = {'resumed_at': time.time()}
        self.emit_event('execution_resumed', data)
    
    def emit_cost_update(self):
        """Emit cost update event"""
        if self.current_session:
            metrics = self.tracker.get_session_metrics(self.current_session)
            data = {
                'total': metrics.get('total_cost', 0),
                'current': metrics.get('total_cost', 0),  # For incremental updates
                'operations_count': metrics.get('operations_count', 0)
            }
            self.emit_event('cost_update', data)
    
    def emit_performance_metrics(self):
        """Emit performance metrics event"""
        if self.current_session:
            metrics = self.tracker.get_session_metrics(self.current_session)
            data = {
                'execution_time': metrics.get('execution_time', 0),
                'operations_count': metrics.get('operations_count', 0),
                'thoughts_count': metrics.get('total_thoughts', 0),
                'avg_score': 0,  # Would need to calculate from individual scores
                'cost_per_thought': (
                    metrics.get('total_cost', 0) / max(metrics.get('total_thoughts', 1), 1)
                )
            }
            self.emit_event('performance_metrics', data)
    
    def emit_debug_info(self, message: str, data: Dict[str, Any] = None):
        """Emit debug information"""
        if self.debug_mode:
            debug_data = {
                'message': message,
                'data': data or {},
                'timestamp': time.time()
            }
            self.emit_event('debug_info', debug_data)
    
    def emit_log_message(self, level: str, message: str, operation_id: str = None):
        """Emit log message"""
        data = {
            'level': level,
            'message': message,
            'operation_id': operation_id,
            'timestamp': time.time()
        }
        self.emit_event('log_message', data)
    
    def get_buffered_events(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get buffered events"""
        return self.buffer.get_events(limit)
    
    def clear_buffer(self):
        """Clear the event buffer"""
        self.buffer.clear()
    
    def get_session_metrics(self, session_id: str = None) -> Dict[str, Any]:
        """Get metrics for a session"""
        if session_id is None:
            session_id = self.current_session
        
        if session_id:
            return self.tracker.get_session_metrics(session_id)
        return {}


# Global instance
_emitter = None
_emitter_lock = threading.Lock()


def get_emitter() -> EventEmitter:
    """Get the global EventEmitter instance"""
    global _emitter
    if _emitter is None:
        with _emitter_lock:
            if _emitter is None:
                _emitter = EventEmitter()
    return _emitter


# Convenience functions for easy access
def emit_event(event_name: str, data: Dict[str, Any], room: Optional[str] = None):
    """Emit an event using the global emitter"""
    get_emitter().emit_event(event_name, data, room)


def emit_operation_start(operation_id: str, operation_type: str, 
                        predecessors: List[str] = None, parameters: Dict[str, Any] = None):
    """Emit operation start event"""
    get_emitter().emit_operation_start(operation_id, operation_type, predecessors, parameters)


def emit_operation_complete(operation_id: str, thoughts: List[Dict[str, Any]], 
                           cost: float, execution_time: float = None, max_score: float = None):
    """Emit operation completion event"""
    get_emitter().emit_operation_complete(operation_id, thoughts, cost, execution_time, max_score)


def emit_operation_error(operation_id: str, error_message: str, error_type: str = 'execution_error'):
    """Emit operation error event"""
    get_emitter().emit_operation_error(operation_id, error_message, error_type)


def emit_execution_started(workflow_id: str, total_operations: int = None):
    """Emit execution start event"""
    get_emitter().emit_execution_started(workflow_id, total_operations)


def emit_execution_completed(workflow_id: str, summary: Dict[str, Any] = None):
    """Emit execution completion event"""
    get_emitter().emit_execution_completed(workflow_id, summary)


def emit_cost_update():
    """Emit cost update event"""
    get_emitter().emit_cost_update()


def emit_performance_metrics():
    """Emit performance metrics event"""
    get_emitter().emit_performance_metrics()


def set_current_session(session_id: str, workflow_id: str = None):
    """Set the current session for event emission"""
    get_emitter().set_current_session(session_id, workflow_id)


def clear_current_session():
    """Clear the current session"""
    get_emitter().clear_current_session()


def set_debug_mode(enabled: bool):
    """Enable or disable debug mode"""
    get_emitter().set_debug_mode(enabled)


def get_session_metrics(session_id: str = None) -> Dict[str, Any]:
    """Get metrics for a session"""
    return get_emitter().get_session_metrics(session_id)


# Context manager for session management
class ExecutionSession:
    """Context manager for managing execution sessions"""
    
    def __init__(self, session_id: str, workflow_id: str = None):
        self.session_id = session_id
        self.workflow_id = workflow_id
        self.emitter = get_emitter()
    
    def __enter__(self):
        self.emitter.set_current_session(self.session_id, self.workflow_id)
        if self.workflow_id:
            self.emitter.emit_execution_started(self.workflow_id)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Execution failed
            self.emitter.emit_operation_error(
                'session_error', 
                f"Session failed: {exc_val}",
                'session_error'
            )
        else:
            # Execution completed successfully
            if self.workflow_id:
                self.emitter.emit_execution_completed(self.workflow_id)
        
        self.emitter.clear_current_session()


# Example usage and testing functions
def test_event_emitter():
    """Test function for the event emitter"""
    emitter = get_emitter()
    
    # Test session management
    with ExecutionSession('test_session', 'test_workflow') as session:
        # Test operation events
        emitter.emit_operation_start('op1', 'Generate', [], {'num_thoughts': 3})
        
        # Simulate some thoughts
        thoughts = [
            {'text': 'Test thought 1', 'score': 0.8},
            {'text': 'Test thought 2', 'score': 0.9},
        ]
        
        emitter.emit_operation_complete('op1', thoughts, 0.01, 1500, 0.9)
        
        # Test metrics
        metrics = emitter.get_session_metrics()
        print(f"Session metrics: {metrics}")
    
    print("Event emitter test completed")


if __name__ == "__main__":
    # Run test if executed directly
    test_event_emitter()
from flask import Flask, render_template, request, jsonify, session
import os
import json
import datetime
import logging
import traceback
from typing import Dict, List, Any
import tempfile
import uuid
import time

# GoT imports
from finance_workflows.local_got import controller, operations
# from graph_of_thoughts import controller, operations
#from graph_of_thoughts.controller.controller import Controller
#from graph_of_thoughts.operations import GraphOfOperations, Generate, Score, KeepBestN, Aggregate, ValidateAndImprove, Improve, KeepValid, Selector, GroundTruth
from finance_workflows.cerebras_llm import CerebrasLLM
from finance_workflows.prompters import (
    RiskAnalysisPrompter, 
    DocumentMergePrompter,
    ComplianceAnalysisPrompter,
    FinancialMetricsPrompter
)
from finance_workflows.parsers import (
    RiskAnalysisParser,
    DocumentMergeParser, 
    ComplianceAnalysisParser,
    FinancialMetricsParser
)
from finance_workflows.workflows import FinanceWorkflows
from finance_workflows.utils import format_currency, calculate_cost

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize workflows
workflows = FinanceWorkflows()

@app.route('/')
def index():
    """Main landing page with workflow selection."""
    return render_template('index.html')

@app.route('/demo')
def demo():
    """Interactive demo page for finance workflows."""
    return render_template('demo.html')

@app.route('/advanced')
def advanced():
    """Advanced GoT configuration page."""
    return render_template('advanced.html')

@app.route('/api/workflows')
def get_workflows():
    """Get available finance workflows."""
    return jsonify({
        'workflows': [
            {
                'id': 'risk_analysis',
                'name': 'Risk Analysis & Portfolio Management',
                'description': 'Analyze risk factors across multiple documents and rank by severity',
                'input_type': 'documents',
                'example': 'Upload company 10-K filings for comprehensive risk assessment'
            },
            {
                'id': 'document_merge', 
                'name': 'Financial Document Processing',
                'description': 'Merge multiple financial documents and identify recurring themes',
                'input_type': 'documents',
                'example': 'Process quarterly earnings call transcripts'
            },
            {
                'id': 'compliance_analysis',
                'name': 'Regulatory Compliance Analysis', 
                'description': 'Analyze regulatory requirements across jurisdictions',
                'input_type': 'text',
                'example': 'Compare Basel III requirements across multiple jurisdictions'
            },
            {
                'id': 'financial_metrics',
                'name': 'Financial Metrics Comparison',
                'description': 'Compare financial metrics across multiple targets',
                'input_type': 'data',
                'example': 'Due diligence analysis of acquisition targets'
            }
        ]
    })

@app.route('/api/execute', methods=['POST'])
def execute_workflow():
    """Execute a GoT workflow for finance analysis."""
    start_time = time.time()
    session_id = None
    
    try:
        data = request.get_json()
        workflow_id = data.get('workflow_id')
        inputs = data.get('inputs', {})
        config = data.get('config', {})
        
        if not workflow_id:
            return jsonify({'error': 'Workflow ID required'}), 400
            
        # Create session ID for tracking
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        logger.info(f"Starting workflow execution: {workflow_id} (session: {session_id})")
        
        # Initialize language model with error handling
        try:
            lm = CerebrasLLM()
            logger.info("Successfully initialized Cerebras LLM")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return jsonify({'error': f'Failed to initialize language model: {str(e)}'}), 500
        
        # Execute workflow based on type
        try:
            if workflow_id == 'risk_analysis':
                result = execute_risk_analysis(lm, inputs, config, session_id)
            elif workflow_id == 'document_merge':
                result = execute_document_merge(lm, inputs, config, session_id)
            elif workflow_id == 'compliance_analysis':
                result = execute_compliance_analysis(lm, inputs, config, session_id)
            elif workflow_id == 'financial_metrics':
                result = execute_financial_metrics(lm, inputs, config, session_id)
            else:
                return jsonify({'error': 'Unknown workflow'}), 400
                
            # Add execution time to result
            execution_time = time.time() - start_time
            result['execution_time'] = execution_time
            
            logger.info(f"Workflow completed successfully: {workflow_id} (time: {execution_time:.2f}s)")
            return jsonify(result)
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {workflow_id} - {str(e)}")
            logger.error(traceback.format_exc())
            
            # Return a structured error response
            execution_time = time.time() - start_time
            return jsonify({
                'error': str(e),
                'workflow': workflow_id,
                'session_id': session_id,
                'execution_time': execution_time,
                'cost': format_currency(0.0),
                'results': {
                    'error': str(e),
                    'thought_count': 0
                }
            }), 500
        
    except Exception as e:
        logger.error(f"Request processing error: {str(e)}")
        logger.error(traceback.format_exc())
        
        execution_time = time.time() - start_time
        return jsonify({
            'error': f'Request processing failed: {str(e)}',
            'session_id': session_id,
            'execution_time': execution_time
        }), 500

def execute_risk_analysis(lm, inputs, config, session_id):
    """Execute risk analysis workflow using GoT."""
    documents = inputs.get('documents', [])
    if not documents:
        raise ValueError("Documents required for risk analysis")
    
    logger.info(f"Risk analysis: processing {len(documents)} documents")
    
    try:
        # Create Graph of Operations for risk analysis
        operations_graph = workflows.create_risk_analysis_graph()
        
        # Initialize controller with better error handling
        ctrl = controller.Controller(
            lm,
            operations_graph,
            RiskAnalysisPrompter(),
            RiskAnalysisParser(),
            {
                'documents': documents,
                'session_id': session_id,
                'method': 'got_risk',
                'current': '',
                'risk_factors': [],
                'severity_scores': {}
            }
        )
        
        # Execute workflow
        logger.info("Starting GoT execution for risk analysis")
        ctrl.run()
        logger.info("GoT execution completed for risk analysis")
        
        # Get results
        final_thoughts = ctrl.get_final_thoughts()
        results = parse_risk_analysis_results(final_thoughts)
        
        # Save results
        save_session_results(session_id, 'risk_analysis', results, lm.cost)
        
        return {
            'session_id': session_id,
            'workflow': 'risk_analysis',
            'results': results,
            'cost': format_currency(lm.cost),
            'execution_time': results.get('execution_time', 0)
        }
        
    except Exception as e:
        logger.error(f"Risk analysis execution failed: {e}")
        raise

def execute_document_merge(lm, inputs, config, session_id):
    """Execute document merge workflow using GoT."""
    documents = inputs.get('documents', [])
    if not documents:
        raise ValueError("Documents required for document merge")
    
    logger.info(f"Document merge: processing {len(documents)} documents")
    
    try:
        # Create Graph of Operations for document merging
        operations_graph = workflows.create_document_merge_graph()
        
        # Initialize controller
        ctrl = controller.Controller(
            lm,
            operations_graph,
            DocumentMergePrompter(),
            DocumentMergeParser(),
            {
                'documents': documents,
                'session_id': session_id,
                'method': 'got_merge',
                'current': '',
                'themes': [],
                'parts': set()
            }
        )
        
        # Execute workflow
        logger.info("Starting GoT execution for document merge")
        ctrl.run()
        logger.info("GoT execution completed for document merge")
        
        # Get results
        final_thoughts = ctrl.get_final_thoughts()
        results = parse_document_merge_results(final_thoughts)
        
        # Save results
        save_session_results(session_id, 'document_merge', results, lm.cost)
        
        return {
            'session_id': session_id,
            'workflow': 'document_merge',
            'results': results,
            'cost': format_currency(lm.cost),
            'execution_time': results.get('execution_time', 0)
        }
        
    except Exception as e:
        logger.error(f"Document merge execution failed: {e}")
        raise

def execute_compliance_analysis(lm, inputs, config, session_id):
    """Execute compliance analysis workflow using GoT."""
    regulatory_texts = inputs.get('regulatory_texts', [])
    if not regulatory_texts:
        raise ValueError("Regulatory texts required for compliance analysis")
    
    logger.info(f"Compliance analysis: processing {len(regulatory_texts)} regulatory texts")
    
    try:
        # Create Graph of Operations for compliance analysis
        operations_graph = workflows.create_compliance_analysis_graph()
        
        # Initialize controller
        ctrl = controller.Controller(
            lm,
            operations_graph,
            ComplianceAnalysisPrompter(),
            ComplianceAnalysisParser(),
            {
                'regulatory_texts': regulatory_texts,
                'session_id': session_id,
                'method': 'got_compliance',
                'current': '',
                'requirements': [],
                'conflicts': []
            }
        )
        
        # Execute workflow
        logger.info("Starting GoT execution for compliance analysis")
        ctrl.run()
        logger.info("GoT execution completed for compliance analysis")
        
        # Get results
        final_thoughts = ctrl.get_final_thoughts()
        results = parse_compliance_results(final_thoughts)
        
        # Save results
        save_session_results(session_id, 'compliance_analysis', results, lm.cost)
        
        return {
            'session_id': session_id,
            'workflow': 'compliance_analysis',
            'results': results,
            'cost': format_currency(lm.cost),
            'execution_time': results.get('execution_time', 0)
        }
        
    except Exception as e:
        logger.error(f"Compliance analysis execution failed: {e}")
        raise

def execute_financial_metrics(lm, inputs, config, session_id):
    """Execute financial metrics comparison workflow using GoT."""
    financial_data = inputs.get('financial_data', [])
    if not financial_data:
        raise ValueError("Financial data required for metrics analysis")
    
    logger.info(f"Financial metrics: processing {len(financial_data)} data points")
    
    try:
        # Create Graph of Operations for financial metrics
        operations_graph = workflows.create_financial_metrics_graph()
        
        # Initialize controller
        ctrl = controller.Controller(
            lm,
            operations_graph,
            FinancialMetricsPrompter(),
            FinancialMetricsParser(),
            {
                'financial_data': financial_data,
                'session_id': session_id,
                'method': 'got_metrics',
                'current': '',
                'metrics': [],
                'rankings': []
            }
        )
        
        # Execute workflow
        logger.info("Starting GoT execution for financial metrics")
        ctrl.run()
        logger.info("GoT execution completed for financial metrics")
        
        # Get results
        final_thoughts = ctrl.get_final_thoughts()
        results = parse_financial_metrics_results(final_thoughts)
        
        # Save results
        save_session_results(session_id, 'financial_metrics', results, lm.cost)
        
        return {
            'session_id': session_id,
            'workflow': 'financial_metrics',
            'results': results,
            'cost': format_currency(lm.cost),
            'execution_time': results.get('execution_time', 0)
        }
        
    except Exception as e:
        logger.error(f"Financial metrics execution failed: {e}")
        raise

def parse_risk_analysis_results(final_thoughts):
    """Parse risk analysis results from GoT execution."""
    try:
        if not final_thoughts or not final_thoughts[0]:
            logger.warning("No final thoughts generated for risk analysis")
            return {
                'error': 'No results generated',
                'risk_factors': [],
                'severity_scores': {},
                'ranked_risks': [],
                'thought_count': 0
            }
        
        # Extract risk factors and severity scores
        thoughts = final_thoughts[0]
        if thoughts:
            latest_thought = thoughts[-1]
            risk_factors = latest_thought.state.get('risk_factors', [])
            
            # Ensure risk_factors is a list
            if not isinstance(risk_factors, list):
                logger.warning(f"Risk factors is not a list: {type(risk_factors)}")
                risk_factors = []
            
            return {
                'risk_factors': risk_factors,
                'severity_scores': latest_thought.state.get('severity_scores', {}),
                'ranked_risks': latest_thought.state.get('ranked_risks', []),
                'execution_time': latest_thought.state.get('execution_time', 0),
                'thought_count': len(thoughts)
            }
        
        return {
            'error': 'Failed to parse results',
            'risk_factors': [],
            'severity_scores': {},
            'ranked_risks': [],
            'thought_count': 0
        }
        
    except Exception as e:
        logger.error(f"Error parsing risk analysis results: {e}")
        return {
            'error': f'Parse error: {str(e)}',
            'risk_factors': [],
            'severity_scores': {},
            'ranked_risks': [],
            'thought_count': 0
        }

def parse_document_merge_results(final_thoughts):
    """Parse document merge results from GoT execution."""
    try:
        if not final_thoughts or not final_thoughts[0]:
            logger.warning("No final thoughts generated for document merge")
            return {
                'error': 'No results generated',
                'merged_document': '',
                'themes': [],
                'theme_frequencies': {},
                'thought_count': 0
            }
        
        thoughts = final_thoughts[0]
        if thoughts:
            latest_thought = thoughts[-1]
            return {
                'merged_document': latest_thought.state.get('current', ''),
                'themes': latest_thought.state.get('themes', []),
                'theme_frequencies': latest_thought.state.get('theme_frequencies', {}),
                'execution_time': latest_thought.state.get('execution_time', 0),
                'thought_count': len(thoughts)
            }
        
        return {
            'error': 'Failed to parse results',
            'merged_document': '',
            'themes': [],
            'theme_frequencies': {},
            'thought_count': 0
        }
        
    except Exception as e:
        logger.error(f"Error parsing document merge results: {e}")
        return {
            'error': f'Parse error: {str(e)}',
            'merged_document': '',
            'themes': [],
            'theme_frequencies': {},
            'thought_count': 0
        }

def parse_compliance_results(final_thoughts):
    """Parse compliance analysis results from GoT execution."""
    try:
        if not final_thoughts or not final_thoughts[0]:
            logger.warning("No final thoughts generated for compliance analysis")
            return {
                'error': 'No results generated',
                'requirements': [],
                'conflicts': [],
                'compliance_matrix': {},
                'thought_count': 0
            }
        
        thoughts = final_thoughts[0]
        if thoughts:
            latest_thought = thoughts[-1]
            return {
                'requirements': latest_thought.state.get('requirements', []),
                'conflicts': latest_thought.state.get('conflicts', []),
                'compliance_matrix': latest_thought.state.get('compliance_matrix', {}),
                'execution_time': latest_thought.state.get('execution_time', 0),
                'thought_count': len(thoughts)
            }
        
        return {
            'error': 'Failed to parse results',
            'requirements': [],
            'conflicts': [],
            'compliance_matrix': {},
            'thought_count': 0
        }
        
    except Exception as e:
        logger.error(f"Error parsing compliance results: {e}")
        return {
            'error': f'Parse error: {str(e)}',
            'requirements': [],
            'conflicts': [],
            'compliance_matrix': {},
            'thought_count': 0
        }

def parse_financial_metrics_results(final_thoughts):
    """Parse financial metrics results from GoT execution."""
    try:
        if not final_thoughts or not final_thoughts[0]:
            logger.warning("No final thoughts generated for financial metrics")
            return {
                'error': 'No results generated',
                'metrics': [],
                'rankings': [],
                'comparative_analysis': {},
                'thought_count': 0
            }
        
        thoughts = final_thoughts[0]
        if thoughts:
            latest_thought = thoughts[-1]
            return {
                'metrics': latest_thought.state.get('metrics', []),
                'rankings': latest_thought.state.get('rankings', []),
                'comparative_analysis': latest_thought.state.get('comparative_analysis', {}),
                'execution_time': latest_thought.state.get('execution_time', 0),
                'thought_count': len(thoughts)
            }
        
        return {
            'error': 'Failed to parse results',
            'metrics': [],
            'rankings': [],
            'comparative_analysis': {},
            'thought_count': 0
        }
        
    except Exception as e:
        logger.error(f"Error parsing financial metrics results: {e}")
        return {
            'error': f'Parse error: {str(e)}',
            'metrics': [],
            'rankings': [],
            'comparative_analysis': {},
            'thought_count': 0
        }

def save_session_results(session_id, workflow_type, results, cost):
    """Save session results to file."""
    try:
        os.makedirs('data/results', exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"data/results/{workflow_type}_{session_id}_{timestamp}.json"
        
        session_data = {
            'session_id': session_id,
            'workflow_type': workflow_type,
            'timestamp': timestamp,
            'results': results,
            'cost': cost,
            'execution_metadata': {
                'thought_count': results.get('thought_count', 0),
                'execution_time': results.get('execution_time', 0)
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(session_data, f, indent=2)
            
        logger.info(f"Results saved to {filename}")
    except Exception as e:
        logger.error(f"Failed to save results: {str(e)}")

@app.route('/api/sessions/<session_id>')
def get_session_results(session_id):
    """Get results for a specific session."""
    try:
        # Find session file
        results_dir = 'data/results'
        if not os.path.exists(results_dir):
            return jsonify({'error': 'No results found'}), 404
            
        for filename in os.listdir(results_dir):
            if session_id in filename:
                with open(os.path.join(results_dir, filename), 'r') as f:
                    data = json.load(f)
                    return jsonify(data)
                    
        return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'got_version': '0.0.3'  # From the GoT repository
    })

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'error': 'Internal server error',
        'message': 'An unexpected error occurred. Please try again.'
    }), 500

@app.errorhandler(404)
def not_found(error):
    """Handle not found errors."""
    return jsonify({
        'error': 'Not found',
        'message': 'The requested resource was not found.'
    }), 404

if __name__ == '__main__':
    # Ensure data directories exist
    os.makedirs('data/sample_documents', exist_ok=True)
    os.makedirs('data/results', exist_ok=True)
    
    # Run the app
    app.run(debug=True, host='127.0.0.1', port=8080)
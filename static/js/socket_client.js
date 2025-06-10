/**
 * Socket.IO Client for Graph of Thoughts Finance Web App
 * Handles real-time communication between frontend and backend
 * Events: node_created, edge_created, node_updated, execution_complete
 * Manages connection state and reconnection
 */

class SocketClient {
    constructor() {
        this.socket = null;
        this.currentSession = null;
        this.connectionState = 'disconnected';
        this.executionState = 'idle';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.heartbeatInterval = null;
        this.eventQueue = [];
        
        this.init();
        this.setupEventHandlers();
    }

    /**
     * Initialize Socket.IO connection
     */
    init() {
        try {
            // Initialize socket connection
            this.socket = io({
                transports: ['websocket', 'polling'], // Fallback for PythonAnywhere
                timeout: 20000,
                forceNew: true,
                reconnection: true,
                reconnectionAttempts: this.maxReconnectAttempts,
                reconnectionDelay: this.reconnectDelay
            });

            console.log('Socket.IO client initialized');
        } catch (error) {
            console.error('Failed to initialize Socket.IO:', error);
            this.handleConnectionError(error);
        }
    }

    /**
     * Set up all socket event handlers
     */
    setupEventHandlers() {
        if (!this.socket) return;

        // Connection events
        this.socket.on('connect', () => {
            console.log('Connected to server with ID:', this.socket.id);
            this.connectionState = 'connected';
            this.currentSession = this.socket.id;
            this.reconnectAttempts = 0;
            
            this.updateConnectionStatus();
            this.processEventQueue();
            this.startHeartbeat();
            
            this.emitClientEvent('socket_connected', { sessionId: this.currentSession });
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Disconnected from server:', reason);
            this.connectionState = 'disconnected';
            this.currentSession = null;
            
            this.updateConnectionStatus();
            this.stopHeartbeat();
            
            this.emitClientEvent('socket_disconnected', { reason });
        });

        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.handleConnectionError(error);
        });

        this.socket.on('reconnect', (attemptNumber) => {
            console.log('Reconnected after', attemptNumber, 'attempts');
            this.connectionState = 'connected';
            this.updateConnectionStatus();
            
            this.emitClientEvent('socket_reconnected', { attempts: attemptNumber });
        });

        this.socket.on('reconnect_failed', () => {
            console.error('Failed to reconnect after maximum attempts');
            this.connectionState = 'failed';
            this.updateConnectionStatus();
            
            this.emitClientEvent('socket_reconnect_failed', {});
        });

        // Server acknowledgment
        this.socket.on('connected', (data) => {
            console.log('Server confirmed connection:', data);
            this.currentSession = data.session_id;
        });

        // Execution lifecycle events
        this.socket.on('execution_started', (data) => {
            console.log('Execution started:', data);
            this.executionState = 'running';
            this.updateExecutionStatus();
            
            if (window.graphViz) {
                window.graphViz.clearGraph();
                window.graphViz.setExecutionState('running');
            }
            
            this.emitClientEvent('execution_started', data);
        });

        this.socket.on('execution_completed', (data) => {
            console.log('Execution completed:', data);
            this.executionState = 'completed';
            this.updateExecutionStatus();
            
            if (window.graphViz) {
                window.graphViz.setExecutionState('completed');
            }
            
            this.showExecutionSummary(data);
            this.emitClientEvent('execution_completed', data);
        });

        this.socket.on('execution_error', (data) => {
            console.error('Execution error:', data);
            this.executionState = 'error';
            this.updateExecutionStatus();
            
            if (window.graphViz) {
                window.graphViz.setExecutionState('error');
            }
            
            this.showError('Execution Error', data.error || 'An unknown error occurred');
            this.emitClientEvent('execution_error', data);
        });

        // Graph operation events
        this.socket.on('operation_start', (data) => {
            console.log('Operation started:', data);
            
            if (window.graphViz) {
                window.graphViz.addOperationNode(data);
            }
            
            this.updateOperationStatus(data.id, 'executing');
            this.emitClientEvent('operation_started', data);
        });

        this.socket.on('operation_complete', (data) => {
            console.log('Operation completed:', data);
            
            if (window.graphViz) {
                window.graphViz.updateOperationNode(data.id, data);
            }
            
            this.updateOperationStatus(data.id, 'completed');
            this.emitClientEvent('operation_completed', data);
        });

        this.socket.on('operation_error', (data) => {
            console.error('Operation error:', data);
            
            if (window.graphViz) {
                window.graphViz.updateOperationNode(data.id, { 
                    ...data, 
                    error: true 
                });
            }
            
            this.updateOperationStatus(data.id, 'error');
            this.emitClientEvent('operation_error', data);
        });

        // Thought generation events
        this.socket.on('thoughts_generated', (data) => {
            console.log('Thoughts generated:', data);
            this.emitClientEvent('thoughts_generated', data);
        });

        this.socket.on('thoughts_scored', (data) => {
            console.log('Thoughts scored:', data);
            this.emitClientEvent('thoughts_scored', data);
        });

        // Cost and performance events
        this.socket.on('cost_update', (data) => {
            console.log('Cost update:', data);
            this.updateCostDisplay(data);
            this.emitClientEvent('cost_updated', data);
        });

        this.socket.on('performance_metrics', (data) => {
            console.log('Performance metrics:', data);
            this.updatePerformanceDisplay(data);
            this.emitClientEvent('performance_updated', data);
        });

        // Control events
        this.socket.on('execution_paused', (data) => {
            console.log('Execution paused:', data);
            this.executionState = 'paused';
            this.updateExecutionStatus();
            this.emitClientEvent('execution_paused', data);
        });

        this.socket.on('execution_resumed', (data) => {
            console.log('Execution resumed:', data);
            this.executionState = 'running';
            this.updateExecutionStatus();
            this.emitClientEvent('execution_resumed', data);
        });

        // Debug and logging events
        this.socket.on('debug_info', (data) => {
            console.log('Debug info:', data);
            this.emitClientEvent('debug_info', data);
        });

        this.socket.on('log_message', (data) => {
            console.log('Server log:', data.message);
            this.addLogEntry(data);
        });
    }

    /**
     * Execute a workflow with given parameters
     */
    executeWorkflow(workflowId, inputs, options = {}) {
        if (!this.isConnected()) {
            this.queueEvent('execute_workflow', { workflowId, inputs, options });
            this.showError('Connection Error', 'Not connected to server. Please wait for reconnection.');
            return false;
        }

        const executionData = {
            workflow_id: workflowId,
            inputs: inputs,
            session_id: this.currentSession,
            timestamp: Date.now(),
            options: {
                max_cost: options.maxCost || 1.0,
                timeout: options.timeout || 300000, // 5 minutes
                enable_debug: options.enableDebug || false,
                ...options
            }
        };

        console.log('Executing workflow:', executionData);
        
        this.socket.emit('execute_workflow', executionData, (response) => {
            if (response && response.error) {
                this.showError('Execution Error', response.error);
                this.emitClientEvent('execution_error', response);
            } else {
                console.log('Workflow execution acknowledged:', response);
            }
        });

        this.executionState = 'starting';
        this.updateExecutionStatus();
        
        return true;
    }

    /**
     * Pause current execution
     */
    pauseExecution() {
        if (!this.isConnected()) {
            this.showError('Connection Error', 'Not connected to server');
            return false;
        }

        this.socket.emit('pause_execution', { 
            session_id: this.currentSession 
        }, (response) => {
            if (response && response.success) {
                console.log('Execution paused successfully');
            } else {
                this.showError('Pause Error', response?.error || 'Failed to pause execution');
            }
        });

        return true;
    }

    /**
     * Resume paused execution
     */
    resumeExecution() {
        if (!this.isConnected()) {
            this.showError('Connection Error', 'Not connected to server');
            return false;
        }

        this.socket.emit('resume_execution', { 
            session_id: this.currentSession 
        }, (response) => {
            if (response && response.success) {
                console.log('Execution resumed successfully');
            } else {
                this.showError('Resume Error', response?.error || 'Failed to resume execution');
            }
        });

        return true;
    }

    /**
     * Stop current execution
     */
    stopExecution() {
        if (!this.isConnected()) {
            return false;
        }

        this.socket.emit('stop_execution', { 
            session_id: this.currentSession 
        }, (response) => {
            if (response && response.success) {
                console.log('Execution stopped successfully');
                this.executionState = 'stopped';
                this.updateExecutionStatus();
            } else {
                this.showError('Stop Error', response?.error || 'Failed to stop execution');
            }
        });

        return true;
    }

    /**
     * Request node details
     */
    getNodeDetails(nodeId) {
        if (!this.isConnected()) {
            return Promise.reject(new Error('Not connected to server'));
        }

        return new Promise((resolve, reject) => {
            this.socket.emit('get_node_details', { 
                node_id: nodeId,
                session_id: this.currentSession 
            }, (response) => {
                if (response && !response.error) {
                    resolve(response);
                } else {
                    reject(new Error(response?.error || 'Failed to get node details'));
                }
            });
        });
    }

    /**
     * Check if socket is connected
     */
    isConnected() {
        return this.socket && this.socket.connected && this.connectionState === 'connected';
    }

    /**
     * Handle connection errors
     */
    handleConnectionError(error) {
        console.error('Socket connection error:', error);
        this.connectionState = 'error';
        this.updateConnectionStatus();
        
        // Try fallback to polling if WebSocket fails
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            setTimeout(() => {
                console.log(`Reconnection attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                this.socket.connect();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    /**
     * Queue events when disconnected
     */
    queueEvent(eventName, data) {
        this.eventQueue.push({ eventName, data, timestamp: Date.now() });
        console.log('Event queued:', eventName);
    }

    /**
     * Process queued events when reconnected
     */
    processEventQueue() {
        if (this.eventQueue.length === 0) return;

        console.log(`Processing ${this.eventQueue.length} queued events`);
        
        const now = Date.now();
        const validEvents = this.eventQueue.filter(event => 
            now - event.timestamp < 300000 // 5 minutes
        );

        validEvents.forEach(event => {
            this.socket.emit(event.eventName, event.data);
        });

        this.eventQueue = [];
    }

    /**
     * Start heartbeat to maintain connection
     */
    startHeartbeat() {
        this.heartbeatInterval = setInterval(() => {
            if (this.isConnected()) {
                this.socket.emit('heartbeat', { timestamp: Date.now() });
            }
        }, 30000); // Every 30 seconds
    }

    /**
     * Stop heartbeat
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Update connection status display
     */
    updateConnectionStatus() {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            const statusText = this.connectionState.charAt(0).toUpperCase() + 
                             this.connectionState.slice(1);
            statusElement.textContent = statusText;
            statusElement.className = `badge bg-${this.getConnectionStatusColor()}`;
        }

        // Update connection indicator
        const indicator = document.getElementById('connection-indicator');
        if (indicator) {
            indicator.className = `connection-indicator ${this.connectionState}`;
        }
    }

    /**
     * Update execution status display
     */
    updateExecutionStatus() {
        const statusElement = document.getElementById('execution-status');
        if (statusElement) {
            const statusText = this.executionState.charAt(0).toUpperCase() + 
                             this.executionState.slice(1);
            statusElement.textContent = statusText;
            statusElement.className = `badge bg-${this.getExecutionStatusColor()}`;
        }
    }

    /**
     * Update operation status
     */
    updateOperationStatus(operationId, status) {
        const element = document.getElementById(`operation-${operationId}`);
        if (element) {
            element.className = `operation-status ${status}`;
        }
    }

    /**
     * Update cost display
     */
    updateCostDisplay(costData) {
        const totalElement = document.getElementById('total-cost');
        if (totalElement) {
            totalElement.textContent = `$${costData.total.toFixed(4)}`;
        }

        const currentElement = document.getElementById('current-cost');
        if (currentElement) {
            currentElement.textContent = `$${costData.current.toFixed(4)}`;
        }

        // Update cost progress bar if available
        const progressElement = document.getElementById('cost-progress');
        const maxCost = parseFloat(document.getElementById('max-cost')?.value || 1.0);
        if (progressElement && maxCost > 0) {
            const percentage = Math.min((costData.total / maxCost) * 100, 100);
            progressElement.style.width = `${percentage}%`;
            progressElement.className = `progress-bar ${this.getCostProgressColor(percentage)}`;
        }
    }

    /**
     * Update performance display
     */
    updatePerformanceDisplay(perfData) {
        const elements = {
            'execution-time': perfData.executionTime ? `${perfData.executionTime}ms` : '0ms',
            'operations-count': perfData.operationsCount || 0,
            'thoughts-count': perfData.thoughtsCount || 0,
            'avg-score': perfData.avgScore ? `${(perfData.avgScore * 100).toFixed(1)}%` : '0%'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                element.textContent = value;
            }
        });
    }

    /**
     * Show execution summary
     */
    showExecutionSummary(data) {
        const summary = `
            Execution completed successfully!
            Total operations: ${data.operationsCount || 0}
            Total thoughts: ${data.thoughtsCount || 0}
            Total cost: $${(data.totalCost || 0).toFixed(4)}
            Execution time: ${data.executionTime || 0}ms
        `;
        
        this.showAlert('Execution Complete', summary, 'success');
    }

    /**
     * Show error message
     */
    showError(title, message) {
        console.error(`${title}: ${message}`);
        this.showAlert(title, message, 'danger');
    }

    /**
     * Show alert message
     */
    showAlert(title, message, type = 'info') {
        // Try to use existing alert system
        if (window.showAlert) {
            window.showAlert(message, type);
            return;
        }

        // Fallback to simple alert
        alert(`${title}: ${message}`);
    }

    /**
     * Add log entry
     */
    addLogEntry(logData) {
        const logContainer = document.getElementById('execution-logs');
        if (logContainer) {
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${logData.level || 'info'}`;
            logEntry.innerHTML = `
                <span class="log-timestamp">${new Date(logData.timestamp).toLocaleTimeString()}</span>
                <span class="log-message">${logData.message}</span>
            `;
            logContainer.appendChild(logEntry);
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }

    /**
     * Get connection status color
     */
    getConnectionStatusColor() {
        const colors = {
            connected: 'success',
            connecting: 'warning',
            disconnected: 'secondary',
            error: 'danger',
            failed: 'danger'
        };
        return colors[this.connectionState] || 'secondary';
    }

    /**
     * Get execution status color
     */
    getExecutionStatusColor() {
        const colors = {
            idle: 'secondary',
            starting: 'info',
            running: 'primary',
            paused: 'warning',
            completed: 'success',
            stopped: 'secondary',
            error: 'danger'
        };
        return colors[this.executionState] || 'secondary';
    }

    /**
     * Get cost progress color
     */
    getCostProgressColor(percentage) {
        if (percentage >= 90) return 'bg-danger';
        if (percentage >= 75) return 'bg-warning';
        if (percentage >= 50) return 'bg-info';
        return 'bg-success';
    }

    /**
     * Emit custom client events
     */
    emitClientEvent(eventName, data) {
        const event = new CustomEvent(`socket:${eventName}`, { detail: data });
        document.dispatchEvent(event);
    }

    /**
     * Clean up resources
     */
    destroy() {
        this.stopHeartbeat();
        
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
        }
        
        this.eventQueue = [];
        this.currentSession = null;
        this.connectionState = 'disconnected';
    }
}

// Initialize global socket client instance
let socketClient = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    try {
        socketClient = new SocketClient();
        console.log('Socket client initialized');
        
        // Add to window for debugging and external access
        window.socketClient = socketClient;
        
        // Set up global convenience functions
        window.executeWorkflow = (workflowId, inputs, options) => 
            socketClient.executeWorkflow(workflowId, inputs, options);
        
        window.pauseExecution = () => socketClient.pauseExecution();
        window.resumeExecution = () => socketClient.resumeExecution();
        window.stopExecution = () => socketClient.stopExecution();
        
    } catch (error) {
        console.error('Failed to initialize socket client:', error);
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (socketClient) {
        socketClient.destroy();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SocketClient;
}
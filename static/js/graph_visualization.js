/**
 * Graph of Thoughts Visualization Module
 * Real-time graph visualization for GoT finance workflows
 * Uses Cytoscape.js for interactive node/edge rendering
 */

class GraphVisualizer {
    constructor(containerId = 'cy') {
        this.cy = null;
        this.containerId = containerId;
        this.currentSession = null;
        this.executionState = 'idle'; // idle, running, paused, completed
        this.totalCost = 0;
        this.executionStartTime = null;
        
        this.init();
        this.setupEventHandlers();
    }

    /**
     * Initialize Cytoscape instance with financial theme
     */
    init() {
        this.cy = cytoscape({
            container: document.getElementById(this.containerId),
            
            style: [
                // Node styles by operation type
                {
                    selector: 'node',
                    style: {
                        'label': 'data(label)',
                        'text-wrap': 'wrap',
                        'text-max-width': '80px',
                        'text-halign': 'center',
                        'text-valign': 'center',
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'color': '#ffffff',
                        'background-color': 'data(color)',
                        'border-width': 2,
                        'border-color': '#ffffff',
                        'width': 'data(size)',
                        'height': 'data(size)',
                        'shape': 'round-rectangle',
                        'overlay-opacity': 0,
                        'text-outline-width': 1,
                        'text-outline-color': '#000000'
                    }
                },
                
                // Generate operation nodes
                {
                    selector: 'node[type="Generate"]',
                    style: {
                        'background-color': '#4a90e2', // Blue for generation
                        'shape': 'ellipse'
                    }
                },
                
                // Score operation nodes
                {
                    selector: 'node[type="Score"]',
                    style: {
                        'background-color': '#f39c12', // Orange for scoring
                        'shape': 'diamond'
                    }
                },
                
                // Aggregate operation nodes
                {
                    selector: 'node[type="Aggregate"]',
                    style: {
                        'background-color': '#27ae60', // Green for aggregation
                        'shape': 'hexagon'
                    }
                },
                
                // KeepBest operation nodes
                {
                    selector: 'node[type="KeepBestN"]',
                    style: {
                        'background-color': '#e74c3c', // Red for filtering
                        'shape': 'triangle'
                    }
                },
                
                // Improve operation nodes
                {
                    selector: 'node[type="Improve"]',
                    style: {
                        'background-color': '#9b59b6', // Purple for improvement
                        'shape': 'octagon'
                    }
                },
                
                // Validate operation nodes
                {
                    selector: 'node[type="Validate"]',
                    style: {
                        'background-color': '#34495e', // Dark gray for validation
                        'shape': 'round-tag'
                    }
                },
                
                // Active/executing nodes
                {
                    selector: 'node.executing',
                    style: {
                        'border-width': 4,
                        'border-color': '#ffd700',
                        'border-style': 'dashed'
                    }
                },
                
                // Completed nodes with high scores
                {
                    selector: 'node.high-score',
                    style: {
                        'border-width': 3,
                        'border-color': '#00ff00'
                    }
                },
                
                // Error nodes
                {
                    selector: 'node.error',
                    style: {
                        'background-color': '#c0392b',
                        'border-color': '#ff0000'
                    }
                },
                
                // Edge styles
                {
                    selector: 'edge',
                    style: {
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'arrow-scale': 1.2,
                        'line-color': '#2a3f5f',
                        'target-arrow-color': '#2a3f5f',
                        'width': 2,
                        'opacity': 0.8
                    }
                },
                
                // Active execution path
                {
                    selector: 'edge.active',
                    style: {
                        'line-color': '#ffd700',
                        'target-arrow-color': '#ffd700',
                        'width': 3,
                        'opacity': 1
                    }
                },
                
                // Selected elements
                {
                    selector: ':selected',
                    style: {
                        'overlay-color': '#ffd700',
                        'overlay-opacity': 0.3
                    }
                }
            ],
            
            layout: {
                name: 'breadthfirst',
                directed: true,
                roots: '[type="Generate"]',
                spacingFactor: 1.5,
                nodeDimensionsIncludeLabels: true,
                animate: true,
                animationDuration: 500
            },
            
            // Enable panning and zooming
            userPanningEnabled: true,
            userZoomingEnabled: true,
            boxSelectionEnabled: true,
            
            // Set viewport
            wheelSensitivity: 0.5,
            minZoom: 0.3,
            maxZoom: 3
        });
    }

    /**
     * Set up event handlers for node interactions
     */
    setupEventHandlers() {
        // Node click handler - show details modal
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            this.showNodeDetails(node);
        });

        // Node hover handler - show tooltip
        this.cy.on('mouseover', 'node', (evt) => {
            const node = evt.target;
            this.showTooltip(node, evt.renderedPosition);
        });

        this.cy.on('mouseout', 'node', () => {
            this.hideTooltip();
        });

        // Layout change handler
        this.cy.on('layoutstop', () => {
            this.fitToView();
        });

        // Selection handler
        this.cy.on('select unselect', 'node', () => {
            this.updateSelectionInfo();
        });
    }

    /**
     * Add a new operation node to the graph
     */
    addOperationNode(operation) {
        const nodeData = {
            id: operation.id,
            label: this.formatNodeLabel(operation),
            type: operation.type,
            color: this.getNodeColor(operation.type),
            size: this.calculateNodeSize(operation),
            operation: operation,
            timestamp: Date.now()
        };

        // Add the node
        this.cy.add({
            group: 'nodes',
            data: nodeData,
            classes: 'executing'
        });

        // Add edges from predecessors
        if (operation.predecessors && operation.predecessors.length > 0) {
            operation.predecessors.forEach(predId => {
                this.cy.add({
                    group: 'edges',
                    data: {
                        id: `${predId}-${operation.id}`,
                        source: predId,
                        target: operation.id
                    },
                    classes: 'active'
                });
            });
        }

        // Update layout
        this.updateLayout();
        
        // Highlight the new node
        this.highlightNode(operation.id);
        
        this.emitEvent('node_added', { nodeId: operation.id, operation });
    }

    /**
     * Update operation node with results
     */
    updateOperationNode(operationId, results) {
        const node = this.cy.getElementById(operationId);
        if (!node.length) return;

        // Update node data
        node.data('thoughts', results.thoughts);
        node.data('cost', results.cost);
        node.data('executionTime', results.executionTime);
        node.data('score', results.maxScore || 0);

        // Remove executing class and add completion styling
        node.removeClass('executing');
        
        if (results.error) {
            node.addClass('error');
        } else if (results.maxScore && results.maxScore > 0.8) {
            node.addClass('high-score');
        }

        // Update label with score if available
        if (results.maxScore !== undefined) {
            const operation = node.data('operation');
            node.data('label', this.formatNodeLabel(operation, results.maxScore));
        }

        // Update total cost
        this.totalCost += results.cost || 0;
        this.updateCostDisplay();

        // Remove active class from incoming edges
        this.cy.edges(`[target="${operationId}"]`).removeClass('active');

        this.emitEvent('node_updated', { nodeId: operationId, results });
    }

    /**
     * Format node label with operation type and score
     */
    formatNodeLabel(operation, score = null) {
        let label = operation.type;
        
        if (operation.parameters) {
            // Add key parameters to label
            if (operation.parameters.k) {
                label += `(k=${operation.parameters.k})`;
            }
            if (operation.parameters.num_thoughts) {
                label += `(n=${operation.parameters.num_thoughts})`;
            }
        }
        
        if (score !== null) {
            label += `\n${(score * 100).toFixed(0)}%`;
        }
        
        return label;
    }

    /**
     * Get color for operation type
     */
    getNodeColor(operationType) {
        const colors = {
            'Generate': '#4a90e2',
            'Score': '#f39c12',
            'Aggregate': '#27ae60',
            'KeepBestN': '#e74c3c',
            'Improve': '#9b59b6',
            'Validate': '#34495e'
        };
        return colors[operationType] || '#7f8c8d';
    }

    /**
     * Calculate node size based on operation complexity
     */
    calculateNodeSize(operation) {
        let baseSize = 60;
        
        // Increase size for operations with more parameters
        if (operation.parameters) {
            baseSize += Object.keys(operation.parameters).length * 5;
        }
        
        // Increase size for operations with more predecessors
        if (operation.predecessors) {
            baseSize += operation.predecessors.length * 3;
        }
        
        return Math.min(baseSize, 100);
    }

    /**
     * Show detailed information about a node
     */
    showNodeDetails(node) {
        const operation = node.data('operation');
        const thoughts = node.data('thoughts') || [];
        const cost = node.data('cost') || 0;
        const executionTime = node.data('executionTime') || 0;

        const modal = this.createNodeModal(operation, thoughts, cost, executionTime);
        document.body.appendChild(modal);
        
        // Show the modal
        $(modal).modal('show');
        
        // Remove modal after hiding
        $(modal).on('hidden.bs.modal', () => {
            modal.remove();
        });
    }

    /**
     * Create modal content for node details
     */
    createNodeModal(operation, thoughts, cost, executionTime) {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content bg-dark text-light">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title">
                            <i class="fas fa-node"></i> ${operation.type} Operation
                        </h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6">
                                <h6>Operation Details</h6>
                                <table class="table table-dark table-sm">
                                    <tr><td>Type</td><td>${operation.type}</td></tr>
                                    <tr><td>ID</td><td>${operation.id}</td></tr>
                                    <tr><td>Cost</td><td>$${cost.toFixed(4)}</td></tr>
                                    <tr><td>Execution Time</td><td>${executionTime}ms</td></tr>
                                    <tr><td>Predecessors</td><td>${operation.predecessors?.length || 0}</td></tr>
                                </table>
                                
                                ${operation.parameters ? `
                                <h6>Parameters</h6>
                                <pre class="bg-secondary p-2 rounded">${JSON.stringify(operation.parameters, null, 2)}</pre>
                                ` : ''}
                            </div>
                            <div class="col-md-6">
                                <h6>Generated Thoughts (${thoughts.length})</h6>
                                <div class="thoughts-container" style="max-height: 300px; overflow-y: auto;">
                                    ${this.renderThoughts(thoughts)}
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer border-secondary">
                        <button type="button" class="btn btn-outline-light" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" onclick="graphViz.exportNodeData('${operation.id}')">
                            Export Data
                        </button>
                    </div>
                </div>
            </div>
        `;
        return modal;
    }

    /**
     * Render thoughts list for modal
     */
    renderThoughts(thoughts) {
        if (!thoughts || thoughts.length === 0) {
            return '<p class="text-muted">No thoughts generated yet.</p>';
        }

        return thoughts.map((thought, index) => `
            <div class="card bg-secondary mb-2">
                <div class="card-body p-2">
                    <div class="d-flex justify-content-between align-items-start">
                        <small class="text-muted">#${index + 1}</small>
                        ${thought.score !== undefined ? 
                            `<span class="badge bg-primary">${(thought.score * 100).toFixed(0)}%</span>` : 
                            ''
                        }
                    </div>
                    <p class="mb-1 small">${this.truncateText(thought.text || thought.content || 'No content', 150)}</p>
                    ${thought.financial_data ? `
                        <div class="mt-1">
                            <small class="text-info">Financial Context Available</small>
                        </div>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    /**
     * Show tooltip on node hover
     */
    showTooltip(node, position) {
        const operation = node.data('operation');
        const cost = node.data('cost') || 0;
        const score = node.data('score') || 0;

        let tooltip = document.getElementById('node-tooltip');
        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.id = 'node-tooltip';
            tooltip.className = 'position-absolute bg-dark text-light p-2 rounded shadow';
            tooltip.style.zIndex = '9999';
            tooltip.style.pointerEvents = 'none';
            document.body.appendChild(tooltip);
        }

        tooltip.innerHTML = `
            <strong>${operation.type}</strong><br>
            Cost: $${cost.toFixed(4)}<br>
            ${score > 0 ? `Score: ${(score * 100).toFixed(0)}%<br>` : ''}
            Thoughts: ${node.data('thoughts')?.length || 0}
        `;

        tooltip.style.left = (position.x + 10) + 'px';
        tooltip.style.top = (position.y - 40) + 'px';
        tooltip.style.display = 'block';
    }

    /**
     * Hide tooltip
     */
    hideTooltip() {
        const tooltip = document.getElementById('node-tooltip');
        if (tooltip) {
            tooltip.style.display = 'none';
        }
    }

    /**
     * Highlight a specific node
     */
    highlightNode(nodeId) {
        // Remove previous highlights
        this.cy.nodes().removeClass('highlighted');
        
        // Add highlight to target node
        const node = this.cy.getElementById(nodeId);
        if (node.length) {
            node.addClass('highlighted');
            
            // Pan to node
            this.cy.animate({
                center: { eles: node },
                zoom: Math.max(this.cy.zoom(), 1)
            }, {
                duration: 500
            });
        }
    }

    /**
     * Update graph layout
     */
    updateLayout() {
        const layout = this.cy.layout({
            name: 'breadthfirst',
            directed: true,
            roots: this.cy.nodes('[type="Generate"]'),
            spacingFactor: 1.5,
            animate: true,
            animationDuration: 300
        });
        
        layout.run();
    }

    /**
     * Fit graph to container
     */
    fitToView() {
        this.cy.fit(null, 50);
    }

    /**
     * Clear the graph
     */
    clearGraph() {
        this.cy.elements().remove();
        this.totalCost = 0;
        this.executionStartTime = null;
        this.executionState = 'idle';
        this.updateCostDisplay();
        this.updateExecutionStatus();
    }

    /**
     * Update cost display
     */
    updateCostDisplay() {
        const costElement = document.getElementById('total-cost');
        if (costElement) {
            costElement.textContent = `$${this.totalCost.toFixed(4)}`;
        }
    }

    /**
     * Update execution status display
     */
    updateExecutionStatus() {
        const statusElement = document.getElementById('execution-status');
        if (statusElement) {
            statusElement.textContent = this.executionState;
            statusElement.className = `badge bg-${this.getStatusColor()}`;
        }
    }

    /**
     * Get status indicator color
     */
    getStatusColor() {
        const colors = {
            'idle': 'secondary',
            'running': 'primary',
            'paused': 'warning',
            'completed': 'success',
            'error': 'danger'
        };
        return colors[this.executionState] || 'secondary';
    }

    /**
     * Update selection information
     */
    updateSelectionInfo() {
        const selected = this.cy.$(':selected');
        const info = document.getElementById('selection-info');
        if (info) {
            if (selected.length > 0) {
                info.innerHTML = `Selected: ${selected.length} element(s)`;
            } else {
                info.innerHTML = 'No selection';
            }
        }
    }

    /**
     * Export node data
     */
    exportNodeData(nodeId) {
        const node = this.cy.getElementById(nodeId);
        if (!node.length) return;

        const data = {
            operation: node.data('operation'),
            thoughts: node.data('thoughts'),
            cost: node.data('cost'),
            executionTime: node.data('executionTime'),
            timestamp: node.data('timestamp')
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `got_node_${nodeId}_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * Export entire graph data
     */
    exportGraph() {
        const graphData = {
            nodes: this.cy.nodes().map(node => ({
                data: node.data(),
                position: node.position()
            })),
            edges: this.cy.edges().map(edge => ({
                data: edge.data()
            })),
            totalCost: this.totalCost,
            executionTime: this.executionStartTime ? Date.now() - this.executionStartTime : 0
        };

        const blob = new Blob([JSON.stringify(graphData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `got_graph_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * Utility function to truncate text
     */
    truncateText(text, maxLength) {
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    /**
     * Emit custom events
     */
    emitEvent(eventName, data) {
        const event = new CustomEvent(`graphviz:${eventName}`, { detail: data });
        document.dispatchEvent(event);
    }

    /**
     * Set execution state
     */
    setExecutionState(state) {
        this.executionState = state;
        this.updateExecutionStatus();
        
        if (state === 'running' && !this.executionStartTime) {
            this.executionStartTime = Date.now();
        }
    }

    /**
     * Get graph statistics
     */
    getStatistics() {
        return {
            nodeCount: this.cy.nodes().length,
            edgeCount: this.cy.edges().length,
            totalCost: this.totalCost,
            executionTime: this.executionStartTime ? Date.now() - this.executionStartTime : 0,
            completedNodes: this.cy.nodes('.high-score, .error').length,
            activeNodes: this.cy.nodes('.executing').length
        };
    }
}

// Initialize global graph visualizer instance
let graphViz = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (document.getElementById('cy')) {
        graphViz = new GraphVisualizer('cy');
        console.log('Graph visualizer initialized');
        
        // Add to window for debugging
        window.graphViz = graphViz;
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = GraphVisualizer;
}
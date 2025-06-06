/**
 * Graph of Thoughts Visualization Library
 * Advanced visualization for GoT execution flows, thought networks, and performance metrics
 * Designed for finance-specific use cases with sophisticated reasoning patterns
 */

class GoTVisualizer {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: options.width || 800,
            height: options.height || 600,
            theme: options.theme || 'light',
            animated: options.animated !== false,
            interactive: options.interactive !== false,
            showMetrics: options.showMetrics !== false,
            ...options
        };
        
        this.svg = null;
        this.nodes = [];
        this.links = [];
        this.executionData = null;
        this.currentStep = 0;
        this.animationTimer = null;
        
        // Color schemes for different operation types
        this.operationColors = {
            'Generate': '#3498db',
            'Score': '#f39c12',
            'KeepBestN': '#27ae60',
            'Aggregate': '#9b59b6',
            'ValidateAndImprove': '#e74c3c',
            'Improve': '#16a085',
            'KeepValid': '#2ecc71',
            'Selector': '#34495e',
            'GroundTruth': '#e67e22',
            'default': '#95a5a6'
        };
        
        // Finance-specific styling
        this.financeTheme = {
            risk: '#dc3545',
            profit: '#28a745',
            neutral: '#6c757d',
            warning: '#ffc107',
            info: '#17a2b8'
        };
        
        this.init();
    }
    
    init() {
        this.container.innerHTML = '';
        this.createSVG();
        this.setupControls();
        this.setupTooltips();
    }
    
    createSVG() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', this.options.width);
        svg.setAttribute('height', this.options.height);
        svg.setAttribute('class', 'got-visualization');
        
        // Add gradients and patterns
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        this.createGradients(defs);
        this.createPatterns(defs);
        svg.appendChild(defs);
        
        // Create main groups
        const linksGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        linksGroup.setAttribute('class', 'links');
        svg.appendChild(linksGroup);
        
        const nodesGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        nodesGroup.setAttribute('class', 'nodes');
        svg.appendChild(nodesGroup);
        
        const labelsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
        labelsGroup.setAttribute('class', 'labels');
        svg.appendChild(labelsGroup);
        
        this.svg = svg;
        this.container.appendChild(svg);
    }
    
    createGradients(defs) {
        // Create gradients for different states
        const gradients = [
            { id: 'nodeGradient', colors: ['#f8f9fa', '#e9ecef'] },
            { id: 'activeGradient', colors: ['#007bff', '#0056b3'] },
            { id: 'successGradient', colors: ['#28a745', '#1e7e34'] },
            { id: 'errorGradient', colors: ['#dc3545', '#bd2130'] },
            { id: 'processGradient', colors: ['#ffc107', '#e0a800'] }
        ];
        
        gradients.forEach(grad => {
            const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
            gradient.setAttribute('id', grad.id);
            gradient.setAttribute('x1', '0%');
            gradient.setAttribute('y1', '0%');
            gradient.setAttribute('x2', '0%');
            gradient.setAttribute('y2', '100%');
            
            grad.colors.forEach((color, i) => {
                const stop = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
                stop.setAttribute('offset', `${i * 100}%`);
                stop.setAttribute('stop-color', color);
                gradient.appendChild(stop);
            });
            
            defs.appendChild(gradient);
        });
    }
    
    createPatterns(defs) {
        // Create patterns for different thought states
        const pattern = document.createElementNS('http://www.w3.org/2000/svg', 'pattern');
        pattern.setAttribute('id', 'thoughtPattern');
        pattern.setAttribute('patternUnits', 'userSpaceOnUse');
        pattern.setAttribute('width', '20');
        pattern.setAttribute('height', '20');
        
        const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        circle.setAttribute('cx', '10');
        circle.setAttribute('cy', '10');
        circle.setAttribute('r', '2');
        circle.setAttribute('fill', '#007bff');
        circle.setAttribute('opacity', '0.3');
        
        pattern.appendChild(circle);
        defs.appendChild(pattern);
    }
    
    setupControls() {
        const controlsDiv = document.createElement('div');
        controlsDiv.className = 'got-viz-controls d-flex justify-content-between align-items-center mb-3';
        controlsDiv.innerHTML = `
            <div class="viz-actions">
                <button class="btn btn-sm btn-outline-primary" id="playAnimation">
                    <i class="fas fa-play"></i> Play
                </button>
                <button class="btn btn-sm btn-outline-secondary" id="pauseAnimation">
                    <i class="fas fa-pause"></i> Pause
                </button>
                <button class="btn btn-sm btn-outline-info" id="resetAnimation">
                    <i class="fas fa-undo"></i> Reset
                </button>
                <button class="btn btn-sm btn-outline-success" id="exportViz">
                    <i class="fas fa-download"></i> Export
                </button>
            </div>
            <div class="viz-progress">
                <label class="form-label small mb-1">Execution Progress</label>
                <div class="progress" style="width: 200px; height: 20px;">
                    <div class="progress-bar" id="vizProgressBar" style="width: 0%"></div>
                </div>
            </div>
            <div class="viz-metrics">
                <small class="text-muted">
                    Step: <span id="currentStepDisplay">0</span> / <span id="totalStepsDisplay">0</span>
                </small>
            </div>
        `;
        
        this.container.insertBefore(controlsDiv, this.svg);
        this.setupControlListeners();
    }
    
    setupControlListeners() {
        document.getElementById('playAnimation')?.addEventListener('click', () => this.playAnimation());
        document.getElementById('pauseAnimation')?.addEventListener('click', () => this.pauseAnimation());
        document.getElementById('resetAnimation')?.addEventListener('click', () => this.resetAnimation());
        document.getElementById('exportViz')?.addEventListener('click', () => this.exportVisualization());
    }
    
    setupTooltips() {
        // Create tooltip element
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'got-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 12px;
            pointer-events: none;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s;
            max-width: 300px;
        `;
        document.body.appendChild(this.tooltip);
    }
    
    /**
     * Main method to visualize GoT execution data
     * @param {Object} data - Execution results from the GoT framework
     */
    visualizeExecution(data) {
        this.executionData = data;
        this.processExecutionData(data);
        this.renderGraph();
        this.updateMetrics();
        
        if (this.options.animated) {
            this.resetAnimation();
        }
    }
    
    processExecutionData(data) {
        const operations = data.graph_definition || [];
        const results = data.results || {};
        const executionTrace = data.execution_trace || [];
        
        this.nodes = [];
        this.links = [];
        
        // Process operations into nodes
        operations.forEach((operation, index) => {
            const node = {
                id: operation.id,
                type: operation.type,
                label: operation.type,
                x: 100 + (index % 4) * 150,
                y: 100 + Math.floor(index / 4) * 120,
                parameters: operation.parameters,
                state: 'pending',
                thoughts: [],
                scores: [],
                cost: this.calculateOperationCost(operation),
                executionTime: 0,
                index: index
            };
            
            // Add execution data if available
            const traceData = executionTrace.find(trace => trace.operation_id === operation.id);
            if (traceData) {
                node.state = traceData.success ? 'completed' : 'error';
                node.thoughts = traceData.thoughts || [];
                node.scores = traceData.scores || [];
                node.executionTime = traceData.execution_time || 0;
            }
            
            this.nodes.push(node);
        });
        
        // Process relationships into links
        operations.forEach(operation => {
            if (operation.predecessors && operation.predecessors.length > 0) {
                operation.predecessors.forEach(predId => {
                    const sourceNode = this.nodes.find(n => n.id === predId);
                    const targetNode = this.nodes.find(n => n.id === operation.id);
                    
                    if (sourceNode && targetNode) {
                        this.links.push({
                            source: sourceNode,
                            target: targetNode,
                            type: 'execution',
                            thoughtFlow: this.calculateThoughtFlow(sourceNode, targetNode)
                        });
                    }
                });
            }
        });
        
        // Add thought connections for complex reasoning patterns
        this.addThoughtConnections();
    }
    
    calculateOperationCost(operation) {
        const baseCosts = {
            'Generate': 2,
            'Score': 1,
            'KeepBestN': 0,
            'Aggregate': 3,
            'ValidateAndImprove': 4,
            'Improve': 2,
            'KeepValid': 0,
            'Selector': 0,
            'GroundTruth': 1
        };
        
        const baseCost = baseCosts[operation.type] || 1;
        const multiplier = operation.parameters?.num_branches_prompt || operation.parameters?.num_samples || 1;
        
        return baseCost * multiplier * 0.01; // Convert to dollars
    }
    
    calculateThoughtFlow(sourceNode, targetNode) {
        const sourceThoughts = sourceNode.thoughts?.length || 1;
        const targetThoughts = targetNode.thoughts?.length || 1;
        
        return {
            input: sourceThoughts,
            output: targetThoughts,
            efficiency: targetThoughts / sourceThoughts
        };
    }
    
    addThoughtConnections() {
        // Add connections between thoughts that show reasoning flow
        this.nodes.forEach(node => {
            if (node.thoughts && node.thoughts.length > 1) {
                // Add internal thought connections for complex operations
                for (let i = 0; i < node.thoughts.length - 1; i++) {
                    this.links.push({
                        source: { 
                            ...node, 
                            id: `${node.id}_thought_${i}`,
                            x: node.x - 20 + (i * 10),
                            y: node.y - 20
                        },
                        target: { 
                            ...node, 
                            id: `${node.id}_thought_${i + 1}`,
                            x: node.x - 20 + ((i + 1) * 10),
                            y: node.y - 20
                        },
                        type: 'thought',
                        internal: true
                    });
                }
            }
        });
    }
    
    renderGraph() {
        this.renderLinks();
        this.renderNodes();
        this.renderLabels();
        this.renderThoughts();
        
        if (this.options.interactive) {
            this.enableInteractions();
        }
    }
    
    renderLinks() {
        const linksGroup = this.svg.querySelector('.links');
        linksGroup.innerHTML = '';
        
        this.links.forEach(link => {
            if (link.internal) return; // Skip internal thought connections for main graph
            
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', link.source.x + 40);
            line.setAttribute('y1', link.source.y + 20);
            line.setAttribute('x2', link.target.x);
            line.setAttribute('y2', link.target.y + 20);
            line.setAttribute('stroke', link.type === 'thought' ? '#17a2b8' : '#6c757d');
            line.setAttribute('stroke-width', link.type === 'thought' ? 1 : 2);
            line.setAttribute('stroke-dasharray', link.type === 'thought' ? '5,5' : 'none');
            line.setAttribute('marker-end', 'url(#arrowhead)');
            line.setAttribute('class', `link link-${link.type}`);
            
            // Add thought flow indicators
            if (link.thoughtFlow) {
                line.setAttribute('stroke-width', Math.max(1, link.thoughtFlow.input / 2));
                
                // Add animated flow indicator
                const flowCircle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                flowCircle.setAttribute('r', '3');
                flowCircle.setAttribute('fill', '#007bff');
                flowCircle.setAttribute('class', 'flow-indicator');
                
                const animateMotion = document.createElementNS('http://www.w3.org/2000/svg', 'animateMotion');
                animateMotion.setAttribute('dur', '3s');
                animateMotion.setAttribute('repeatCount', 'indefinite');
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', `M ${link.source.x + 40} ${link.source.y + 20} L ${link.target.x} ${link.target.y + 20}`);
                animateMotion.appendChild(path);
                
                flowCircle.appendChild(animateMotion);
                linksGroup.appendChild(flowCircle);
            }
            
            linksGroup.appendChild(line);
        });
        
        // Add arrowhead marker
        this.addArrowMarker();
    }
    
    addArrowMarker() {
        const defs = this.svg.querySelector('defs');
        
        // Remove existing marker
        const existingMarker = defs.querySelector('#arrowhead');
        if (existingMarker) {
            existingMarker.remove();
        }
        
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'arrowhead');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '7');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '3.5');
        marker.setAttribute('orient', 'auto');
        
        const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
        polygon.setAttribute('points', '0 0, 10 3.5, 0 7');
        polygon.setAttribute('fill', '#6c757d');
        
        marker.appendChild(polygon);
        defs.appendChild(marker);
    }
    
    renderNodes() {
        const nodesGroup = this.svg.querySelector('.nodes');
        nodesGroup.innerHTML = '';
        
        this.nodes.forEach((node, index) => {
            const nodeGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
            nodeGroup.setAttribute('class', `node node-${node.type.toLowerCase()}`);
            nodeGroup.setAttribute('data-node-id', node.id);
            
            // Main node rectangle
            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', node.x);
            rect.setAttribute('y', node.y);
            rect.setAttribute('width', '80');
            rect.setAttribute('height', '40');
            rect.setAttribute('rx', '8');
            rect.setAttribute('fill', this.getNodeFill(node));
            rect.setAttribute('stroke', this.operationColors[node.type] || this.operationColors.default);
            rect.setAttribute('stroke-width', '2');
            rect.setAttribute('class', 'node-rect');
            
            // Add node state indicator
            const stateIndicator = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            stateIndicator.setAttribute('cx', node.x + 75);
            stateIndicator.setAttribute('cy', node.y + 5);
            stateIndicator.setAttribute('r', '4');
            stateIndicator.setAttribute('fill', this.getStateColor(node.state));
            stateIndicator.setAttribute('class', 'state-indicator');
            
            // Add cost indicator
            if (node.cost > 0) {
                const costBadge = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
                costBadge.setAttribute('x', node.x + 60);
                costBadge.setAttribute('y', node.y - 10);
                costBadge.setAttribute('width', '20');
                costBadge.setAttribute('height', '12');
                costBadge.setAttribute('rx', '6');
                costBadge.setAttribute('fill', '#ffc107');
                costBadge.setAttribute('class', 'cost-badge');
                
                const costText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                costText.setAttribute('x', node.x + 70);
                costText.setAttribute('y', node.y - 2);
                costText.setAttribute('text-anchor', 'middle');
                costText.setAttribute('font-size', '8');
                costText.setAttribute('fill', '#000');
                costText.textContent = `$${node.cost.toFixed(2)}`;
                
                nodeGroup.appendChild(costBadge);
                nodeGroup.appendChild(costText);
            }
            
            // Add thought count indicator
            if (node.thoughts && node.thoughts.length > 0) {
                const thoughtBadge = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                thoughtBadge.setAttribute('cx', node.x + 5);
                thoughtBadge.setAttribute('cy', node.y + 5);
                thoughtBadge.setAttribute('r', '8');
                thoughtBadge.setAttribute('fill', '#17a2b8');
                thoughtBadge.setAttribute('class', 'thought-badge');
                
                const thoughtText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                thoughtText.setAttribute('x', node.x + 5);
                thoughtText.setAttribute('y', node.y + 9);
                thoughtText.setAttribute('text-anchor', 'middle');
                thoughtText.setAttribute('font-size', '10');
                thoughtText.setAttribute('fill', 'white');
                thoughtText.setAttribute('font-weight', 'bold');
                thoughtText.textContent = node.thoughts.length;
                
                nodeGroup.appendChild(thoughtBadge);
                nodeGroup.appendChild(thoughtText);
            }
            
            nodeGroup.appendChild(rect);
            nodeGroup.appendChild(stateIndicator);
            
            // Add hover effects and tooltips
            this.addNodeInteractions(nodeGroup, node);
            
            nodesGroup.appendChild(nodeGroup);
        });
    }
    
    getNodeFill(node) {
        const gradients = {
            'pending': 'url(#nodeGradient)',
            'processing': 'url(#processGradient)',
            'completed': 'url(#successGradient)',
            'error': 'url(#errorGradient)',
            'active': 'url(#activeGradient)'
        };
        
        return gradients[node.state] || gradients.pending;
    }
    
    getStateColor(state) {
        const colors = {
            'pending': '#6c757d',
            'processing': '#ffc107',
            'completed': '#28a745',
            'error': '#dc3545',
            'active': '#007bff'
        };
        
        return colors[state] || colors.pending;
    }
    
    renderLabels() {
        const labelsGroup = this.svg.querySelector('.labels');
        labelsGroup.innerHTML = '';
        
        this.nodes.forEach(node => {
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', node.x + 40);
            text.setAttribute('y', node.y + 25);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('font-size', '10');
            text.setAttribute('font-weight', 'bold');
            text.setAttribute('fill', '#000');
            text.setAttribute('class', 'node-label');
            text.textContent = this.truncateLabel(node.label, 8);
            
            labelsGroup.appendChild(text);
        });
    }
    
    renderThoughts() {
        // Render individual thoughts as small nodes around main operations
        this.nodes.forEach(node => {
            if (node.thoughts && node.thoughts.length > 1) {
                const thoughtsGroup = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                thoughtsGroup.setAttribute('class', 'thoughts-group');
                
                node.thoughts.forEach((thought, index) => {
                    const angle = (index / node.thoughts.length) * 2 * Math.PI;
                    const radius = 60;
                    const thoughtX = node.x + 40 + Math.cos(angle) * radius;
                    const thoughtY = node.y + 20 + Math.sin(angle) * radius;
                    
                    const thoughtNode = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                    thoughtNode.setAttribute('cx', thoughtX);
                    thoughtNode.setAttribute('cy', thoughtY);
                    thoughtNode.setAttribute('r', '6');
                    thoughtNode.setAttribute('fill', this.getThoughtColor(thought));
                    thoughtNode.setAttribute('stroke', '#fff');
                    thoughtNode.setAttribute('stroke-width', '1');
                    thoughtNode.setAttribute('class', 'thought-node');
                    thoughtNode.setAttribute('data-thought-index', index);
                    
                    // Add thought score indicator
                    if (thought.score !== undefined) {
                        const scoreText = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                        scoreText.setAttribute('x', thoughtX);
                        scoreText.setAttribute('y', thoughtY + 15);
                        scoreText.setAttribute('text-anchor', 'middle');
                        scoreText.setAttribute('font-size', '8');
                        scoreText.setAttribute('fill', '#666');
                        scoreText.textContent = thought.score.toFixed(1);
                        
                        thoughtsGroup.appendChild(scoreText);
                    }
                    
                    // Add connection line from main node to thought
                    const connectionLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                    connectionLine.setAttribute('x1', node.x + 40);
                    connectionLine.setAttribute('y1', node.y + 20);
                    connectionLine.setAttribute('x2', thoughtX);
                    connectionLine.setAttribute('y2', thoughtY);
                    connectionLine.setAttribute('stroke', '#e9ecef');
                    connectionLine.setAttribute('stroke-width', '1');
                    connectionLine.setAttribute('stroke-dasharray', '2,2');
                    
                    thoughtsGroup.appendChild(connectionLine);
                    thoughtsGroup.appendChild(thoughtNode);
                    
                    // Add thought interactions
                    this.addThoughtInteractions(thoughtNode, thought, node, index);
                });
                
                this.svg.querySelector('.nodes').appendChild(thoughtsGroup);
            }
        });
    }
    
    getThoughtColor(thought) {
        if (thought.score !== undefined) {
            // Color based on score
            if (thought.score >= 8) return '#28a745'; // High score - green
            if (thought.score >= 6) return '#ffc107'; // Medium score - yellow
            if (thought.score >= 4) return '#fd7e14'; // Low score - orange
            return '#dc3545'; // Very low score - red
        }
        
        if (thought.valid !== undefined) {
            return thought.valid ? '#28a745' : '#dc3545';
        }
        
        return '#17a2b8'; // Default thought color
    }
    
    addNodeInteractions(nodeGroup, node) {
        nodeGroup.addEventListener('mouseenter', (e) => {
            this.showTooltip(e, this.createNodeTooltip(node));
            nodeGroup.style.cursor = 'pointer';
            
            // Highlight connected nodes
            this.highlightConnections(node);
        });
        
        nodeGroup.addEventListener('mouseleave', (e) => {
            this.hideTooltip();
            this.clearHighlights();
        });
        
        nodeGroup.addEventListener('click', (e) => {
            this.selectNode(node);
            this.showNodeDetails(node);
        });
    }
    
    addThoughtInteractions(thoughtNode, thought, parentNode, index) {
        thoughtNode.addEventListener('mouseenter', (e) => {
            this.showTooltip(e, this.createThoughtTooltip(thought, parentNode, index));
            thoughtNode.style.cursor = 'pointer';
        });
        
        thoughtNode.addEventListener('mouseleave', (e) => {
            this.hideTooltip();
        });
        
        thoughtNode.addEventListener('click', (e) => {
            e.stopPropagation();
            this.showThoughtDetails(thought, parentNode, index);
        });
    }
    
    createNodeTooltip(node) {
        const parametersText = Object.entries(node.parameters || {})
            .map(([key, value]) => `${key}: ${value}`)
            .join('<br>');
        
        return `
            <div class="tooltip-header">
                <strong>${node.type}</strong>
                <span class="badge bg-${this.getStateBadgeClass(node.state)} ms-2">${node.state}</span>
            </div>
            <div class="tooltip-body">
                ${node.thoughts ? `<div>Thoughts: ${node.thoughts.length}</div>` : ''}
                ${node.cost > 0 ? `<div>Cost: $${node.cost.toFixed(4)}</div>` : ''}
                ${node.executionTime > 0 ? `<div>Time: ${node.executionTime.toFixed(2)}s</div>` : ''}
                ${parametersText ? `<div class="mt-2"><small>Parameters:<br>${parametersText}</small></div>` : ''}
            </div>
        `;
    }
    
    createThoughtTooltip(thought, parentNode, index) {
        return `
            <div class="tooltip-header">
                <strong>Thought ${index + 1}</strong>
                <small class="text-muted">from ${parentNode.type}</small>
            </div>
            <div class="tooltip-body">
                ${thought.score !== undefined ? `<div>Score: ${thought.score.toFixed(2)}</div>` : ''}
                ${thought.valid !== undefined ? `<div>Valid: ${thought.valid ? 'Yes' : 'No'}</div>` : ''}
                ${thought.content ? `<div class="mt-2"><small>${thought.content.substring(0, 100)}...</small></div>` : ''}
            </div>
        `;
    }
    
    getStateBadgeClass(state) {
        const classes = {
            'pending': 'secondary',
            'processing': 'warning',
            'completed': 'success',
            'error': 'danger',
            'active': 'primary'
        };
        
        return classes[state] || 'secondary';
    }
    
    showTooltip(event, content) {
        this.tooltip.innerHTML = content;
        this.tooltip.style.left = (event.pageX + 10) + 'px';
        this.tooltip.style.top = (event.pageY + 10) + 'px';
        this.tooltip.style.opacity = '1';
    }
    
    hideTooltip() {
        this.tooltip.style.opacity = '0';
    }
    
    highlightConnections(node) {
        // Highlight all connected links and nodes
        this.links.forEach(link => {
            if (link.source.id === node.id || link.target.id === node.id) {
                const linkElement = this.svg.querySelector(`.link`);
                if (linkElement) {
                    linkElement.style.strokeWidth = '4';
                    linkElement.style.stroke = '#007bff';
                }
            }
        });
    }
    
    clearHighlights() {
        // Reset all highlights
        this.svg.querySelectorAll('.link').forEach(link => {
            link.style.strokeWidth = '';
            link.style.stroke = '';
        });
    }
    
    selectNode(node) {
        // Clear previous selections
        this.svg.querySelectorAll('.node-selected').forEach(n => {
            n.classList.remove('node-selected');
        });
        
        // Select current node
        const nodeElement = this.svg.querySelector(`[data-node-id="${node.id}"]`);
        if (nodeElement) {
            nodeElement.classList.add('node-selected');
            nodeElement.querySelector('.node-rect').setAttribute('stroke-width', '4');
        }
        
        this.selectedNode = node;
    }
    
    showNodeDetails(node) {
        // Emit event for external handling
        const event = new CustomEvent('nodeSelected', {
            detail: { node, visualizer: this }
        });
        this.container.dispatchEvent(event);
    }
    
    showThoughtDetails(thought, parentNode, index) {
        // Emit event for external handling
        const event = new CustomEvent('thoughtSelected', {
            detail: { thought, parentNode, index, visualizer: this }
        });
        this.container.dispatchEvent(event);
    }
    
    truncateLabel(label, maxLength) {
        return label.length > maxLength ? label.substring(0, maxLength) + '...' : label;
    }
    
    enableInteractions() {
        let isDragging = false;
        let dragNode = null;
        let startX, startY;
        
        this.svg.addEventListener('mousedown', (e) => {
            const nodeGroup = e.target.closest('.node');
            if (nodeGroup) {
                isDragging = true;
                dragNode = nodeGroup;
                startX = e.clientX;
                startY = e.clientY;
                e.preventDefault();
            }
        });
        
        this.svg.addEventListener('mousemove', (e) => {
            if (isDragging && dragNode) {
                const deltaX = e.clientX - startX;
                const deltaY = e.clientY - startY;
                
                const nodeId = dragNode.dataset.nodeId;
                const node = this.nodes.find(n => n.id === nodeId);
                
                if (node) {
                    node.x += deltaX;
                    node.y += deltaY;
                    this.renderGraph();
                }
                
                startX = e.clientX;
                startY = e.clientY;
            }
        });
        
        this.svg.addEventListener('mouseup', () => {
            isDragging = false;
            dragNode = null;
        });
        
        // Zoom and pan functionality
        this.addZoomPan();
    }
    
    addZoomPan() {
        let scale = 1;
        let panX = 0;
        let panY = 0;
        let isPanning = false;
        let lastPanX, lastPanY;
        
        this.svg.addEventListener('wheel', (e) => {
            e.preventDefault();
            
            const delta = e.deltaY > 0 ? 0.9 : 1.1;
            scale *= delta;
            scale = Math.max(0.1, Math.min(5, scale));
            
            this.updateTransform(scale, panX, panY);
        });
        
        this.svg.addEventListener('mousedown', (e) => {
            if (e.button === 1 || e.ctrlKey) { // Middle button or Ctrl+click for panning
                isPanning = true;
                lastPanX = e.clientX;
                lastPanY = e.clientY;
                e.preventDefault();
            }
        });
        
        this.svg.addEventListener('mousemove', (e) => {
            if (isPanning) {
                panX += e.clientX - lastPanX;
                panY += e.clientY - lastPanY;
                lastPanX = e.clientX;
                lastPanY = e.clientY;
                
                this.updateTransform(scale, panX, panY);
            }
        });
        
        this.svg.addEventListener('mouseup', () => {
            isPanning = false;
        });
    }
    
    updateTransform(scale, panX, panY) {
        const transform = `translate(${panX}, ${panY}) scale(${scale})`;
        this.svg.querySelector('.nodes').setAttribute('transform', transform);
        this.svg.querySelector('.links').setAttribute('transform', transform);
        this.svg.querySelector('.labels').setAttribute('transform', transform);
    }
    
    /**
     * Animation control methods
     */
    playAnimation() {
        if (!this.executionData || !this.executionData.execution_trace) {
            console.warn('No execution trace data available for animation');
            return;
        }
        
        const trace = this.executionData.execution_trace;
        this.totalSteps = trace.length;
        
        if (this.animationTimer) {
            clearInterval(this.animationTimer);
        }
        
        this.animationTimer = setInterval(() => {
            if (this.currentStep < this.totalSteps) {
                this.animateStep(this.currentStep);
                this.currentStep++;
                this.updateProgress();
            } else {
                this.pauseAnimation();
            }
        }, 1500); // 1.5 second per step
        
        document.getElementById('totalStepsDisplay').textContent = this.totalSteps;
    }
    
    pauseAnimation() {
        if (this.animationTimer) {
            clearInterval(this.animationTimer);
            this.animationTimer = null;
        }
    }
    
    resetAnimation() {
        this.pauseAnimation();
        this.currentStep = 0;
        this.updateProgress();
        
        // Reset all nodes to pending state
        this.nodes.forEach(node => {
            node.state = 'pending';
        });
        
        this.renderGraph();
    }
    
    animateStep(stepIndex) {
        if (!this.executionData.execution_trace || stepIndex >= this.executionData.execution_trace.length) {
            return;
        }
        
        const step = this.executionData.execution_trace[stepIndex];
        const node = this.nodes.find(n => n.id === step.operation_id);
        
        if (node) {
            // Animate node state change
            node.state = 'processing';
            this.renderGraph();
            
            setTimeout(() => {
                node.state = step.success ? 'completed' : 'error';
                node.thoughts = step.thoughts || [];
                node.scores = step.scores || [];
                this.renderGraph();
                
                // Show thought generation animation
                this.animateThoughtGeneration(node);
            }, 750);
        }
    }
    
    animateThoughtGeneration(node) {
        if (!node.thoughts || node.thoughts.length === 0) return;
        
        // Animate thoughts appearing one by one
        const thoughtElements = this.svg.querySelectorAll(`[data-node-id="${node.id}"] + .thoughts-group .thought-node`);
        
        thoughtElements.forEach((thoughtElement, index) => {
            setTimeout(() => {
                thoughtElement.style.opacity = '0';
                thoughtElement.style.transform = 'scale(0)';
                
                setTimeout(() => {
                    thoughtElement.style.transition = 'all 0.5s ease';
                    thoughtElement.style.opacity = '1';
                    thoughtElement.style.transform = 'scale(1)';
                }, 100);
            }, index * 200);
        });
    }
    
    updateProgress() {
        const progressPercent = this.totalSteps > 0 ? (this.currentStep / this.totalSteps) * 100 : 0;
        
        const progressBar = document.getElementById('vizProgressBar');
        if (progressBar) {
            progressBar.style.width = progressPercent + '%';
        }
        
        const stepDisplay = document.getElementById('currentStepDisplay');
        if (stepDisplay) {
            stepDisplay.textContent = this.currentStep;
        }
    }
    
    updateMetrics() {
        if (!this.executionData) return;
        
        const metricsEvent = new CustomEvent('metricsUpdated', {
            detail: {
                totalNodes: this.nodes.length,
                totalLinks: this.links.length,
                totalThoughts: this.nodes.reduce((sum, node) => sum + (node.thoughts?.length || 0), 0),
                totalCost: this.nodes.reduce((sum, node) => sum + (node.cost || 0), 0),
                averageScore: this.calculateAverageScore(),
                executionTime: this.executionData.execution_time || 0,
                visualizer: this
            }
        });
        
        this.container.dispatchEvent(metricsEvent);
    }
    
    calculateAverageScore() {
        const allScores = [];
        this.nodes.forEach(node => {
            if (node.thoughts) {
                node.thoughts.forEach(thought => {
                    if (thought.score !== undefined) {
                        allScores.push(thought.score);
                    }
                });
            }
        });
        
        return allScores.length > 0 ? allScores.reduce((sum, score) => sum + score, 0) / allScores.length : 0;
    }
    
    /**
     * Export functionality
     */
    exportVisualization() {
        const exportOptions = [
            { label: 'Export as SVG', action: () => this.exportSVG() },
            { label: 'Export as PNG', action: () => this.exportPNG() },
            { label: 'Export Data as JSON', action: () => this.exportData() },
            { label: 'Export Animation as GIF', action: () => this.exportGIF() }
        ];
        
        this.showExportMenu(exportOptions);
    }
    
    showExportMenu(options) {
        // Create export menu
        const menu = document.createElement('div');
        menu.className = 'export-menu';
        menu.style.cssText = `
            position: absolute;
            background: white;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
            z-index: 1001;
            min-width: 200px;
        `;
        
        options.forEach(option => {
            const item = document.createElement('div');
            item.className = 'export-menu-item';
            item.style.cssText = `
                padding: 10px 15px;
                cursor: pointer;
                border-bottom: 1px solid #eee;
            `;
            item.textContent = option.label;
            item.addEventListener('click', () => {
                option.action();
                menu.remove();
            });
            item.addEventListener('mouseenter', () => {
                item.style.backgroundColor = '#f8f9fa';
            });
            item.addEventListener('mouseleave', () => {
                item.style.backgroundColor = '';
            });
            
            menu.appendChild(item);
        });
        
        // Position menu near export button
        const exportButton = document.getElementById('exportViz');
        const rect = exportButton.getBoundingClientRect();
        menu.style.left = rect.left + 'px';
        menu.style.top = (rect.bottom + 5) + 'px';
        
        document.body.appendChild(menu);
        
        // Remove menu when clicking elsewhere
        setTimeout(() => {
            document.addEventListener('click', function removeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', removeMenu);
                }
            });
        }, 10);
    }
    
    exportSVG() {
        const svgData = new XMLSerializer().serializeToString(this.svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        this.downloadBlob(blob, 'got-visualization.svg');
    }
    
    exportPNG() {
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        const img = new Image();
        
        const svgData = new XMLSerializer().serializeToString(this.svg);
        const blob = new Blob([svgData], { type: 'image/svg+xml' });
        const url = URL.createObjectURL(blob);
        
        img.onload = () => {
            canvas.width = this.options.width;
            canvas.height = this.options.height;
            ctx.drawImage(img, 0, 0);
            
            canvas.toBlob((blob) => {
                this.downloadBlob(blob, 'got-visualization.png');
                URL.revokeObjectURL(url);
            });
        };
        
        img.src = url;
    }
    
    exportData() {
        const exportData = {
            timestamp: new Date().toISOString(),
            nodes: this.nodes,
            links: this.links,
            executionData: this.executionData,
            options: this.options
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        this.downloadBlob(blob, 'got-visualization-data.json');
    }
    
    exportGIF() {
        // This would require a GIF creation library
        alert('GIF export requires additional libraries. Consider using screen recording for now.');
    }
    
    downloadBlob(blob, filename) {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.click();
        URL.revokeObjectURL(link.href);
    }
    
    /**
     * Layout algorithms for different visualization styles
     */
    applyHierarchicalLayout() {
        // Arrange nodes in hierarchical layers
        const layers = this.calculateLayers();
        const layerHeight = this.options.height / layers.length;
        
        layers.forEach((layer, layerIndex) => {
            const layerWidth = this.options.width / (layer.length + 1);
            
            layer.forEach((node, nodeIndex) => {
                node.x = layerWidth * (nodeIndex + 1) - 40;
                node.y = layerHeight * layerIndex + 50;
            });
        });
        
        this.renderGraph();
    }
    
    calculateLayers() {
        const layers = [];
        const visited = new Set();
        
        // Find root nodes (no predecessors)
        const rootNodes = this.nodes.filter(node => 
            !this.links.some(link => link.target.id === node.id)
        );
        
        let currentLayer = [...rootNodes];
        
        while (currentLayer.length > 0) {
            layers.push([...currentLayer]);
            currentLayer.forEach(node => visited.add(node.id));
            
            const nextLayer = [];
            currentLayer.forEach(node => {
                this.links.forEach(link => {
                    if (link.source.id === node.id && !visited.has(link.target.id)) {
                        if (!nextLayer.find(n => n.id === link.target.id)) {
                            nextLayer.push(link.target);
                        }
                    }
                });
            });
            
            currentLayer = nextLayer;
        }
        
        return layers;
    }
    
    applyCircularLayout() {
        // Arrange nodes in a circle
        const centerX = this.options.width / 2;
        const centerY = this.options.height / 2;
        const radius = Math.min(centerX, centerY) - 100;
        
        this.nodes.forEach((node, index) => {
            const angle = (index / this.nodes.length) * 2 * Math.PI;
            node.x = centerX + Math.cos(angle) * radius - 40;
            node.y = centerY + Math.sin(angle) * radius - 20;
        });
        
        this.renderGraph();
    }
    
    applyForceLayout() {
        // Simple force-directed layout
        const iterations = 100;
        const repulsion = 1000;
        const attraction = 0.1;
        
        for (let i = 0; i < iterations; i++) {
            // Apply repulsion between all nodes
            this.nodes.forEach(node1 => {
                this.nodes.forEach(node2 => {
                    if (node1.id !== node2.id) {
                        const dx = node1.x - node2.x;
                        const dy = node1.y - node2.y;
                        const distance = Math.sqrt(dx * dx + dy * dy) || 1;
                        
                        const force = repulsion / (distance * distance);
                        node1.x += (dx / distance) * force;
                        node1.y += (dy / distance) * force;
                    }
                });
            });
            
            // Apply attraction for connected nodes
            this.links.forEach(link => {
                const dx = link.target.x - link.source.x;
                const dy = link.target.y - link.source.y;
                
                link.source.x += dx * attraction;
                link.source.y += dy * attraction;
                link.target.x -= dx * attraction;
                link.target.y -= dy * attraction;
            });
            
            // Keep nodes within bounds
            this.nodes.forEach(node => {
                node.x = Math.max(50, Math.min(this.options.width - 50, node.x));
                node.y = Math.max(50, Math.min(this.options.height - 50, node.y));
            });
        }
        
        this.renderGraph();
    }
    
    /**
     * Performance monitoring and metrics
     */
    startPerformanceMonitoring() {
        this.performanceData = {
            renderTimes: [],
            animationFrames: 0,
            lastFrameTime: performance.now()
        };
        
        // Monitor rendering performance
        const originalRenderGraph = this.renderGraph.bind(this);
        this.renderGraph = () => {
            const start = performance.now();
            originalRenderGraph();
            const end = performance.now();
            
            this.performanceData.renderTimes.push(end - start);
            if (this.performanceData.renderTimes.length > 100) {
                this.performanceData.renderTimes.shift();
            }
        };
        
        // Monitor animation performance
        const monitorAnimation = () => {
            const now = performance.now();
            const delta = now - this.performanceData.lastFrameTime;
            
            if (delta > 16.67) { // 60 FPS threshold
                this.performanceData.animationFrames++;
            }
            
            this.performanceData.lastFrameTime = now;
            requestAnimationFrame(monitorAnimation);
        };
        
        requestAnimationFrame(monitorAnimation);
    }
    
    getPerformanceMetrics() {
        if (!this.performanceData) {
            return null;
        }
        
        const avgRenderTime = this.performanceData.renderTimes.reduce((sum, time) => sum + time, 0) / this.performanceData.renderTimes.length;
        
        return {
            averageRenderTime: avgRenderTime,
            slowFrames: this.performanceData.animationFrames,
            memoryUsage: performance.memory ? {
                used: performance.memory.usedJSHeapSize,
                total: performance.memory.totalJSHeapSize,
                limit: performance.memory.jsHeapSizeLimit
            } : null
        };
    }
    
    /**
     * Accessibility features
     */
    addAccessibilityFeatures() {
        // Add ARIA labels
        this.svg.setAttribute('role', 'img');
        this.svg.setAttribute('aria-label', 'Graph of Thoughts execution visualization');
        
        // Add keyboard navigation
        this.svg.setAttribute('tabindex', '0');
        
        this.svg.addEventListener('keydown', (e) => {
            switch (e.key) {
                case 'ArrowRight':
                    this.navigateToNextNode();
                    e.preventDefault();
                    break;
                case 'ArrowLeft':
                    this.navigateToPreviousNode();
                    e.preventDefault();
                    break;
                case 'Enter':
                case ' ':
                    if (this.selectedNode) {
                        this.showNodeDetails(this.selectedNode);
                    }
                    e.preventDefault();
                    break;
                case 'Escape':
                    this.clearSelection();
                    e.preventDefault();
                    break;
            }
        });
        
        // Add screen reader support
        this.nodes.forEach(node => {
            const nodeElement = this.svg.querySelector(`[data-node-id="${node.id}"]`);
            if (nodeElement) {
                nodeElement.setAttribute('aria-label', 
                    `${node.type} operation, ${node.state} state, ${node.thoughts?.length || 0} thoughts`
                );
                nodeElement.setAttribute('role', 'button');
                nodeElement.setAttribute('tabindex', '0');
            }
        });
    }
    
    navigateToNextNode() {
        const currentIndex = this.selectedNode ? this.nodes.findIndex(n => n.id === this.selectedNode.id) : -1;
        const nextIndex = (currentIndex + 1) % this.nodes.length;
        this.selectNode(this.nodes[nextIndex]);
    }
    
    navigateToPreviousNode() {
        const currentIndex = this.selectedNode ? this.nodes.findIndex(n => n.id === this.selectedNode.id) : 0;
        const prevIndex = currentIndex === 0 ? this.nodes.length - 1 : currentIndex - 1;
        this.selectNode(this.nodes[prevIndex]);
    }
    
    clearSelection() {
        this.svg.querySelectorAll('.node-selected').forEach(n => {
            n.classList.remove('node-selected');
            n.querySelector('.node-rect').setAttribute('stroke-width', '2');
        });
        this.selectedNode = null;
    }
    
    /**
     * Utility methods
     */
    destroy() {
        // Clean up event listeners and timers
        if (this.animationTimer) {
            clearInterval(this.animationTimer);
        }
        
        if (this.tooltip && this.tooltip.parentNode) {
            this.tooltip.parentNode.removeChild(this.tooltip);
        }
        
        // Remove all event listeners
        this.container.innerHTML = '';
    }
    
    resize(width, height) {
        this.options.width = width;
        this.options.height = height;
        
        if (this.svg) {
            this.svg.setAttribute('width', width);
            this.svg.setAttribute('height', height);
            this.renderGraph();
        }
    }
    
    setTheme(theme) {
        this.options.theme = theme;
        this.container.className = this.container.className.replace(/theme-\w+/, '') + ` theme-${theme}`;
        this.renderGraph();
    }
}

/**
 * Finance-specific visualization extensions
 */
class FinanceGoTVisualizer extends GoTVisualizer {
    constructor(containerId, options = {}) {
        super(containerId, {
            ...options,
            financeMode: true
        });
        
        // Finance-specific color schemes
        this.financeColors = {
            'risk_analysis': '#dc3545',
            'document_merge': '#007bff',
            'compliance_analysis': '#ffc107',
            'financial_metrics': '#28a745',
            'profit': '#28a745',
            'loss': '#dc3545',
            'neutral': '#6c757d'
        };
    }
    
    processFinanceData(data) {
        // Override to add finance-specific processing
        super.processExecutionData(data);
        
        // Add finance-specific node properties
        this.nodes.forEach(node => {
            if (data.workflow === 'risk_analysis') {
                node.riskLevel = this.calculateRiskLevel(node);
                node.financeColor = this.financeColors.risk_analysis;
            } else if (data.workflow === 'financial_metrics') {
                node.profitability = this.calculateProfitability(node);
                node.financeColor = this.financeColors.financial_metrics;
            }
        });
    }
    
    calculateRiskLevel(node) {
        if (node.thoughts && node.thoughts.length > 0) {
            const avgSeverity = node.thoughts.reduce((sum, thought) => {
                return sum + (thought.severity || 0);
            }, 0) / node.thoughts.length;
            
            if (avgSeverity >= 8) return 'high';
            if (avgSeverity >= 6) return 'medium';
            return 'low';
        }
        return 'unknown';
    }
    
    calculateProfitability(node) {
        // Finance-specific calculation logic
        return 'profitable'; // Placeholder
    }
    
    renderFinanceIndicators() {
        // Add finance-specific visual indicators
        this.nodes.forEach(node => {
            if (node.riskLevel) {
                this.addRiskIndicator(node);
            }
            if (node.profitability) {
                this.addProfitabilityIndicator(node);
            }
        });
    }
    
    addRiskIndicator(node) {
        const indicator = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
        indicator.setAttribute('x', node.x + 70);
        indicator.setAttribute('y', node.y + 30);
        indicator.setAttribute('width', '10');
        indicator.setAttribute('height', '10');
        indicator.setAttribute('fill', this.getRiskColor(node.riskLevel));
        indicator.setAttribute('class', 'risk-indicator');
        
        this.svg.querySelector('.nodes').appendChild(indicator);
    }
    
    getRiskColor(riskLevel) {
        const colors = {
            'high': '#dc3545',
            'medium': '#ffc107',
            'low': '#28a745',
            'unknown': '#6c757d'
        };
        return colors[riskLevel] || colors.unknown;
    }
    
    addProfitabilityIndicator(node) {
        // Add profitability-specific visual indicators
        const indicator = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
        indicator.setAttribute('cx', node.x + 75);
        indicator.setAttribute('cy', node.y + 35);
        indicator.setAttribute('r', '5');
        indicator.setAttribute('fill', this.financeColors.profit);
        indicator.setAttribute('class', 'profit-indicator');
        
        this.svg.querySelector('.nodes').appendChild(indicator);
    }
}

/**
 * Global utility functions for GoT visualization
 */
window.GoTVisualization = {
    create: (containerId, options = {}) => {
        if (options.financeMode) {
            return new FinanceGoTVisualizer(containerId, options);
        }
        return new GoTVisualizer(containerId, options);
    },
    
    // Predefined layout configurations
    layouts: {
        hierarchical: 'hierarchical',
        circular: 'circular',
        force: 'force'
    },
    
    // Predefined themes
    themes: {
        light: 'light',
        dark: 'dark',
        finance: 'finance'
    },
    
    // Utility functions
    utils: {
        formatCurrency: (amount) => {
            return new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD'
            }).format(amount);
        },
        
        formatDuration: (seconds) => {
            if (seconds < 60) return `${seconds.toFixed(1)}s`;
            const minutes = Math.floor(seconds / 60);
            const remainingSeconds = seconds % 60;
            return `${minutes}m ${remainingSeconds.toFixed(1)}s`;
        },
        
        generateId: () => {
            return 'viz_' + Math.random().toString(36).substr(2, 9);
        }
    }
};

// CSS styles for the visualization
const vizStyles = `
<style>
.got-visualization {
    border: 1px solid #dee2e6;
    border-radius: 8px;
    background: #fff;
}

.theme-dark .got-visualization {
    background: #2d3748;
    border-color: #4a5568;
}

.got-viz-controls {
    background: #f8f9fa;
    padding: 10px;
    border-radius: 6px;
    margin-bottom: 10px;
}

.theme-dark .got-viz-controls {
    background: #4a5568;
    color: white;
}

.node-selected .node-rect {
    filter: drop-shadow(0 0 10px rgba(0, 123, 255, 0.5));
}

.link {
    transition: all 0.3s ease;
}

.thought-node {
    transition: all 0.3s ease;
    cursor: pointer;
}

.thought-node:hover {
    transform: scale(1.2);
}

.flow-indicator {
    opacity: 0.7;
}

.got-tooltip {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.4;
}

.tooltip-header {
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding-bottom: 5px;
    margin-bottom: 5px;
}

.export-menu-item:last-child {
    border-bottom: none;
}

.theme-finance .got-visualization {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
}

.theme-finance .node-rect {
    stroke-width: 2;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

.risk-indicator {
    stroke: white;
    stroke-width: 1;
}

.profit-indicator {
    stroke: white;
    stroke-width: 1;
}

@media (max-width: 768px) {
    .got-viz-controls {
        flex-direction: column;
        gap: 10px;
    }
    
    .viz-actions {
        display: flex;
        justify-content: center;
        gap: 5px;
    }
    
    .viz-progress {
        order: 3;
    }
}

@keyframes pulse {
    0% { opacity: 1; }
    50% { opacity: 0.5; }
    100% { opacity: 1; }
}

.processing .state-indicator {
    animation: pulse 1s infinite;
}

.thought-node {
    animation: fadeIn 0.5s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: scale(0); }
    to { opacity: 1; transform: scale(1); }
}
</style>
`;

// Inject styles into document
if (!document.getElementById('got-viz-styles')) {
    const styleElement = document.createElement('div');
    styleElement.id = 'got-viz-styles';
    styleElement.innerHTML = vizStyles;
    document.head.appendChild(styleElement);
}

/**
 * Integration helpers for the Flask application
 */
window.GoTIntegration = {
    /**
     * Initialize visualization for demo page
     */
    initDemo: function(containerId = 'execution-graph') {
        const visualizer = window.GoTVisualization.create(containerId, {
            width: 800,
            height: 500,
            animated: true,
            interactive: true,
            financeMode: true,
            theme: 'finance'
        });

        // Listen for workflow execution results
        window.addEventListener('gotExecutionComplete', (event) => {
            visualizer.visualizeExecution(event.detail);
        });

        // Add event listeners for integration with demo UI
        visualizer.container.addEventListener('nodeSelected', (event) => {
            const node = event.detail.node;
            console.log('Node selected:', node);
            
            // Update demo UI with node details
            if (window.updateNodeDetails) {
                window.updateNodeDetails(node);
            }
        });

        visualizer.container.addEventListener('thoughtSelected', (event) => {
            const { thought, parentNode, index } = event.detail;
            console.log('Thought selected:', thought);
            
            // Update demo UI with thought details
            if (window.updateThoughtDetails) {
                window.updateThoughtDetails(thought, parentNode, index);
            }
        });

        visualizer.container.addEventListener('metricsUpdated', (event) => {
            const metrics = event.detail;
            console.log('Metrics updated:', metrics);
            
            // Update demo UI metrics display
            if (window.updateVisualizationMetrics) {
                window.updateVisualizationMetrics(metrics);
            }
        });

        return visualizer;
    },

    /**
     * Initialize visualization for advanced page
     */
    initAdvanced: function(containerId = 'graph-canvas') {
        const visualizer = window.GoTVisualization.create(containerId, {
            width: 1000,
            height: 600,
            animated: true,
            interactive: true,
            financeMode: true,
            theme: 'light',
            showMetrics: true
        });

        // Enable performance monitoring for advanced users
        visualizer.startPerformanceMonitoring();

        // Add advanced layout controls
        this.addLayoutControls(visualizer);

        return visualizer;
    },

    /**
     * Add layout control buttons
     */
    addLayoutControls: function(visualizer) {
        const controlsContainer = visualizer.container.querySelector('.got-viz-controls .viz-actions');
        
        if (controlsContainer) {
            const layoutControls = document.createElement('div');
            layoutControls.className = 'ms-3';
            layoutControls.innerHTML = `
                <div class="btn-group" role="group">
                    <button class="btn btn-sm btn-outline-info" onclick="GoTIntegration.setLayout('hierarchical', '${visualizer.container.id}')">
                        <i class="fas fa-sitemap"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="GoTIntegration.setLayout('circular', '${visualizer.container.id}')">
                        <i class="fas fa-circle"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-info" onclick="GoTIntegration.setLayout('force', '${visualizer.container.id}')">
                        <i class="fas fa-project-diagram"></i>
                    </button>
                </div>
            `;
            
            controlsContainer.appendChild(layoutControls);
        }
    },

    /**
     * Set visualization layout
     */
    setLayout: function(layoutType, containerId) {
        const container = document.getElementById(containerId);
        if (container && container._gotVisualizer) {
            const visualizer = container._gotVisualizer;
            
            switch (layoutType) {
                case 'hierarchical':
                    visualizer.applyHierarchicalLayout();
                    break;
                case 'circular':
                    visualizer.applyCircularLayout();
                    break;
                case 'force':
                    visualizer.applyForceLayout();
                    break;
            }
        }
    },

    /**
     * Create mini visualization for results summary
     */
    createMiniViz: function(containerId, data, options = {}) {
        const miniOptions = {
            width: 400,
            height: 200,
            animated: false,
            interactive: false,
            showMetrics: false,
            ...options
        };

        const visualizer = window.GoTVisualization.create(containerId, miniOptions);
        visualizer.visualizeExecution(data);
        
        return visualizer;
    },

    /**
     * Export current visualization state
     */
    exportCurrentVisualization: function(containerId, format = 'svg') {
        const container = document.getElementById(containerId);
        if (container && container._gotVisualizer) {
            const visualizer = container._gotVisualizer;
            
            switch (format) {
                case 'svg':
                    visualizer.exportSVG();
                    break;
                case 'png':
                    visualizer.exportPNG();
                    break;
                case 'json':
                    visualizer.exportData();
                    break;
            }
        }
    },

    /**
     * Real-time visualization updates for streaming execution
     */
    streamingVisualizer: function(containerId, options = {}) {
        const visualizer = window.GoTVisualization.create(containerId, {
            ...options,
            streaming: true
        });

        // WebSocket or polling setup for real-time updates
        let executionData = { nodes: [], links: [], execution_trace: [] };
        
        const updateVisualization = (newData) => {
            // Merge new data with existing
            executionData = this.mergeExecutionData(executionData, newData);
            visualizer.visualizeExecution(executionData);
        };

        // Expose update method
        visualizer.updateStream = updateVisualization;
        
        return visualizer;
    },

    /**
     * Merge streaming execution data
     */
    mergeExecutionData: function(existing, newData) {
        return {
            ...existing,
            ...newData,
            execution_trace: [...(existing.execution_trace || []), ...(newData.execution_trace || [])],
            nodes: this.mergeArrayById(existing.nodes || [], newData.nodes || []),
            links: this.mergeArrayById(existing.links || [], newData.links || [])
        };
    },

    /**
     * Merge arrays by ID, updating existing items
     */
    mergeArrayById: function(existing, newItems) {
        const merged = [...existing];
        
        newItems.forEach(newItem => {
            const existingIndex = merged.findIndex(item => item.id === newItem.id);
            if (existingIndex >= 0) {
                merged[existingIndex] = { ...merged[existingIndex], ...newItem };
            } else {
                merged.push(newItem);
            }
        });
        
        return merged;
    },

    /**
     * Comparison visualization for A/B testing different GoT configurations
     */
    createComparisonViz: function(containerId, dataA, dataB, options = {}) {
        const container = document.getElementById(containerId);
        container.innerHTML = '';
        
        // Create split view
        const splitContainer = document.createElement('div');
        splitContainer.className = 'row';
        splitContainer.innerHTML = `
            <div class="col-md-6">
                <h6 class="text-center mb-3">Configuration A</h6>
                <div id="${containerId}-a"></div>
            </div>
            <div class="col-md-6">
                <h6 class="text-center mb-3">Configuration B</h6>
                <div id="${containerId}-b"></div>
            </div>
        `;
        
        container.appendChild(splitContainer);
        
        // Create visualizations
        const vizA = window.GoTVisualization.create(`${containerId}-a`, {
            width: 380,
            height: 400,
            ...options
        });
        
        const vizB = window.GoTVisualization.create(`${containerId}-b`, {
            width: 380,
            height: 400,
            ...options
        });
        
        vizA.visualizeExecution(dataA);
        vizB.visualizeExecution(dataB);
        
        // Add comparison metrics
        this.addComparisonMetrics(container, dataA, dataB);
        
        return { vizA, vizB };
    },

    /**
     * Add comparison metrics display
     */
    addComparisonMetrics: function(container, dataA, dataB) {
        const metricsDiv = document.createElement('div');
        metricsDiv.className = 'mt-3 p-3 bg-light rounded';
        
        const costA = dataA.cost || 0;
        const costB = dataB.cost || 0;
        const timeA = dataA.execution_time || 0;
        const timeB = dataB.execution_time || 0;
        
        metricsDiv.innerHTML = `
            <h6>Comparison Metrics</h6>
            <div class="row text-center">
                <div class="col-md-3">
                    <div class="metric">
                        <strong>Cost Difference</strong><br>
                        <span class="${costA < costB ? 'text-success' : 'text-danger'}">
                            ${((costB - costA) / costA * 100).toFixed(1)}%
                        </span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric">
                        <strong>Time Difference</strong><br>
                        <span class="${timeA < timeB ? 'text-success' : 'text-danger'}">
                            ${((timeB - timeA) / timeA * 100).toFixed(1)}%
                        </span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric">
                        <strong>Better Config</strong><br>
                        <span class="text-primary">
                            ${(costA < costB && timeA < timeB) ? 'A' : 
                              (costB < costA && timeB < timeA) ? 'B' : 'Mixed'}
                        </span>
                    </div>
                </div>
                <div class="col-md-3">
                    <div class="metric">
                        <strong>Efficiency</strong><br>
                        <span class="text-info">
                            ${this.calculateEfficiencyRatio(dataA, dataB).toFixed(2)}
                        </span>
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(metricsDiv);
    },

    /**
     * Calculate efficiency ratio between two configurations
     */
    calculateEfficiencyRatio: function(dataA, dataB) {
        const efficiencyA = (dataA.results?.thought_count || 1) / ((dataA.cost || 0.01) * (dataA.execution_time || 1));
        const efficiencyB = (dataB.results?.thought_count || 1) / ((dataB.cost || 0.01) * (dataB.execution_time || 1));
        
        return efficiencyA / efficiencyB;
    },

    /**
     * Finance-specific visualization enhancements
     */
    addFinanceFeatures: function(visualizer, workflowType) {
        switch (workflowType) {
            case 'risk_analysis':
                this.addRiskAnalysisFeatures(visualizer);
                break;
            case 'financial_metrics':
                this.addFinancialMetricsFeatures(visualizer);
                break;
            case 'compliance_analysis':
                this.addComplianceFeatures(visualizer);
                break;
            case 'document_merge':
                this.addDocumentMergeFeatures(visualizer);
                break;
        }
    },

    /**
     * Add risk analysis specific features
     */
    addRiskAnalysisFeatures: function(visualizer) {
        // Add risk level indicators
        const originalRenderNodes = visualizer.renderNodes.bind(visualizer);
        visualizer.renderNodes = function() {
            originalRenderNodes();
            
            // Add risk severity color coding
            this.nodes.forEach(node => {
                if (node.thoughts && node.thoughts.length > 0) {
                    const avgSeverity = node.thoughts.reduce((sum, thought) => 
                        sum + (thought.severity || 0), 0) / node.thoughts.length;
                    
                    const nodeElement = this.svg.querySelector(`[data-node-id="${node.id}"] .node-rect`);
                    if (nodeElement && avgSeverity > 0) {
                        const riskColor = avgSeverity >= 8 ? '#dc3545' : 
                                        avgSeverity >= 6 ? '#ffc107' : '#28a745';
                        nodeElement.setAttribute('stroke', riskColor);
                        nodeElement.setAttribute('stroke-width', '3');
                    }
                }
            });
        };
    },

    /**
     * Add financial metrics specific features
     */
    addFinancialMetricsFeatures: function(visualizer) {
        // Add profitability indicators
        const originalCreateNodeTooltip = visualizer.createNodeTooltip.bind(visualizer);
        visualizer.createNodeTooltip = function(node) {
            let tooltip = originalCreateNodeTooltip(node);
            
            if (node.thoughts) {
                const financialData = node.thoughts.find(thought => thought.financial_metrics);
                if (financialData) {
                    tooltip += `
                        <div class="mt-2">
                            <strong>Financial Metrics:</strong><br>
                            <small>ROE: ${financialData.financial_metrics.roe || 'N/A'}</small><br>
                            <small>ROA: ${financialData.financial_metrics.roa || 'N/A'}</small>
                        </div>
                    `;
                }
            }
            
            return tooltip;
        };
    },

    /**
     * Add compliance analysis features
     */
    addComplianceFeatures: function(visualizer) {
        // Add compliance status indicators
        visualizer.nodes.forEach(node => {
            if (node.thoughts) {
                const conflictCount = node.thoughts.reduce((count, thought) => 
                    count + (thought.conflicts ? thought.conflicts.length : 0), 0);
                
                node.complianceStatus = conflictCount === 0 ? 'compliant' : 
                                      conflictCount < 3 ? 'minor_issues' : 'major_issues';
            }
        });
    },

    /**
     * Add document merge features
     */
    addDocumentMergeFeatures: function(visualizer) {
        // Add theme frequency visualization
        const originalRenderThoughts = visualizer.renderThoughts.bind(visualizer);
        visualizer.renderThoughts = function() {
            originalRenderThoughts();
            
            // Add theme frequency as node size variation
            this.nodes.forEach(node => {
                if (node.thoughts && node.thoughts.length > 0) {
                    const totalThemes = node.thoughts.reduce((sum, thought) => 
                        sum + (thought.themes ? thought.themes.length : 0), 0);
                    
                    const nodeElement = this.svg.querySelector(`[data-node-id="${node.id}"] .node-rect`);
                    if (nodeElement && totalThemes > 0) {
                        const size = Math.min(120, 80 + (totalThemes * 2));
                        nodeElement.setAttribute('width', size);
                    }
                }
            });
        };
    }
};

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page that needs visualization
    if (document.getElementById('execution-graph')) {
        window.gotVisualizer = window.GoTIntegration.initDemo();
    }
    
    if (document.getElementById('graph-canvas')) {
        window.advancedGotVisualizer = window.GoTIntegration.initAdvanced();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        GoTVisualizer,
        FinanceGoTVisualizer,
        GoTVisualization: window.GoTVisualization,
        GoTIntegration: window.GoTIntegration
    };
}

console.log('GoT Visualization Library loaded successfully');
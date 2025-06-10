"""
Finance workflow definitions using Graph of Thoughts operations.
Creates sophisticated reasoning graphs for financial analysis tasks.
"""

#from graph_of_thoughts import operations
from .local_got import operations
from functools import partial
from finance_workflows.enhanced_operations import create_enhanced_risk_analysis_graph


class FinanceWorkflows:
    """Factory class for creating finance-specific Graph of Operations."""

    @staticmethod
    def create_risk_analysis_graph():
        """
        Create a sophisticated Graph of Operations for risk analysis.
        
        Uses GoT pattern: Split documents -> Extract risks -> Score -> Aggregate -> Improve
        """
        return create_enhanced_risk_analysis_graph()
        operations_graph = operations.GraphOfOperations()
        
        # Step 1: Generate initial risk extractions from documents (multiple attempts)
        initial_generate = operations.Generate(1, 5)  # 5 different risk extractions
        operations_graph.append_operation(initial_generate)
        
        # Step 2: Score each risk extraction
        score_extractions = operations.Score(1, False, FinanceWorkflows._risk_analysis_scorer)
        operations_graph.append_operation(score_extractions)
        
        # Step 3: Keep best risk extractions
        keep_best_extractions = operations.KeepBestN(3, True)
        operations_graph.append_operation(keep_best_extractions)
        
        # Step 4: Aggregate the best risk analyses
        aggregate_risks = operations.Aggregate(3)  # Try 3 different aggregations
        operations_graph.append_operation(aggregate_risks)
        
        # Step 5: Score aggregated results
        score_aggregated = operations.Score(1, False, FinanceWorkflows._risk_aggregation_scorer)
        operations_graph.append_operation(score_aggregated)
        
        # Step 6: Keep best aggregated result
        keep_best_aggregated = operations.KeepBestN(1, True)
        operations_graph.append_operation(keep_best_aggregated)
        
        # Step 7: Improve the final result
        improve_final = operations.Generate(1, 3)  # 3 improvement attempts
        operations_graph.append_operation(improve_final)
        
        # Step 8: Score improvements
        score_improvements = operations.Score(1, False, FinanceWorkflows._risk_analysis_scorer)
        operations_graph.append_operation(score_improvements)
        
        # Step 9: Keep the best final result
        final_selection = operations.KeepBestN(1, True)
        operations_graph.append_operation(final_selection)
        
        return operations_graph

    @staticmethod
    def create_document_merge_graph():
        """
        Create a Graph of Operations for document merging and theme extraction.
        
        Uses GoT pattern: Split -> Extract themes -> Aggregate themes -> Merge documents
        """
        operations_graph = operations.GraphOfOperations()
        
        # Step 1: Split documents for parallel processing
        document_splitter = operations.Selector(
            lambda thoughts: [
                operations.Thought(state={**thoughts[0].state, "parts": {i}})
                for i in range(min(4, len(thoughts[0].state.get('documents', []))))
            ]
        )
        operations_graph.add_operation(document_splitter)
        
        # Step 2: Extract themes from each document part
        theme_extractors = []
        for i in range(4):  # Process up to 4 documents in parallel
            part_selector = operations.Selector(
                lambda thoughts, part_id=i: [
                    thought for thought in thoughts 
                    if part_id in thought.state.get("parts", set())
                ]
            )
            part_selector.add_predecessor(document_splitter)
            operations_graph.add_operation(part_selector)
            
            extract_themes = operations.Generate(1, 3)  # 3 theme extraction attempts
            extract_themes.add_predecessor(part_selector)
            operations_graph.add_operation(extract_themes)
            
            score_themes = operations.Score(1, False, FinanceWorkflows._theme_extraction_scorer)
            score_themes.add_predecessor(extract_themes)
            operations_graph.add_operation(score_themes)
            
            keep_best_themes = operations.KeepBestN(1, True)
            keep_best_themes.add_predecessor(score_themes)
            operations_graph.add_operation(keep_best_themes)
            
            theme_extractors.append(keep_best_themes)
        
        # Step 3: Aggregate themes from all documents
        while len(theme_extractors) > 1:
            new_extractors = []
            for i in range(0, len(theme_extractors), 2):
                if i + 1 < len(theme_extractors):
                    aggregate_themes = operations.Aggregate(2)
                    aggregate_themes.add_predecessor(theme_extractors[i])
                    aggregate_themes.add_predecessor(theme_extractors[i + 1])
                    operations_graph.add_operation(aggregate_themes)
                    
                    score_aggregated_themes = operations.Score(1, False, FinanceWorkflows._theme_aggregation_scorer)
                    score_aggregated_themes.add_predecessor(aggregate_themes)
                    operations_graph.add_operation(score_aggregated_themes)
                    
                    keep_best_aggregated = operations.KeepBestN(1, True)
                    keep_best_aggregated.add_predecessor(score_aggregated_themes)
                    operations_graph.add_operation(keep_best_aggregated)
                    
                    new_extractors.append(keep_best_aggregated)
                else:
                    new_extractors.append(theme_extractors[i])
            theme_extractors = new_extractors
        
        # Step 4: Final document merge based on themes
        final_merge = operations.Generate(1, 5)  # 5 merge attempts
        operations_graph.append_operation(final_merge)
        
        # Step 5: Score merged documents
        score_merged = operations.Score(1, False, FinanceWorkflows._document_merge_scorer)
        operations_graph.append_operation(score_merged)
        
        # Step 6: Keep best merged result
        keep_best_merge = operations.KeepBestN(1, True)
        operations_graph.append_operation(keep_best_merge)
        
        return operations_graph

    @staticmethod
    def create_compliance_analysis_graph():
        """
        Create a Graph of Operations for regulatory compliance analysis.
        
        Uses ToT + GoT pattern: Extract requirements -> Analyze conflicts -> Validate
        """
        operations_graph = operations.GraphOfOperations()
        
        # Step 1: Extract requirements from each regulatory text
        extract_requirements = operations.Generate(1, 4)  # 4 extraction attempts
        operations_graph.append_operation(extract_requirements)
        
        # Step 2: Score requirement extractions
        score_requirements = operations.Score(1, False, FinanceWorkflows._requirement_extraction_scorer)
        operations_graph.append_operation(score_requirements)
        
        # Step 3: Keep best extractions
        keep_best_requirements = operations.KeepBestN(2, True)  # Keep top 2
        operations_graph.append_operation(keep_best_requirements)
        
        # Step 4: Iterative improvement of requirements (ToT-style)
        for iteration in range(2):
            improve_requirements = operations.Generate(1, 3)
            improve_requirements.add_predecessor(keep_best_requirements)
            operations_graph.add_operation(improve_requirements)
            
            score_improved = operations.Score(1, False, FinanceWorkflows._requirement_extraction_scorer)
            score_improved.add_predecessor(improve_requirements)
            operations_graph.add_operation(score_improved)
            
            keep_improved = operations.KeepBestN(1, True)
            keep_improved.add_predecessor(score_improved)
            operations_graph.add_operation(keep_improved)
            
            keep_best_requirements = keep_improved
        
        # Step 5: Conflict analysis
        analyze_conflicts = operations.Generate(1, 5)  # 5 conflict analysis attempts
        operations_graph.append_operation(analyze_conflicts)
        
        # Step 6: Score conflict analyses
        score_conflicts = operations.Score(1, False, FinanceWorkflows._conflict_analysis_scorer)
        operations_graph.append_operation(score_conflicts)
        
        # Step 7: Validate and improve conflict analysis
        validate_and_improve = operations.ValidateAndImprove(
            num_samples=1,
            improve=True,
            num_tries=3,
            validate_function=FinanceWorkflows._validate_compliance_analysis
        )
        operations_graph.append_operation(validate_and_improve)
        
        # Step 8: Final scoring
        final_score = operations.Score(1, False, FinanceWorkflows._compliance_final_scorer)
        operations_graph.append_operation(final_score)
        
        # Step 9: Keep best result
        final_selection = operations.KeepBestN(1, True)
        operations_graph.append_operation(final_selection)
        
        return operations_graph

    @staticmethod
    def create_financial_metrics_graph():
        """
        Create a Graph of Operations for financial metrics comparison.
        
        Uses GoT pattern: Extract metrics -> Compare -> Rank -> Validate
        """
        operations_graph = operations.GraphOfOperations()
        
        # Step 1: Extract metrics from each company's data
        extract_metrics = operations.Generate(1, 3)  # 3 extraction attempts per company
        operations_graph.append_operation(extract_metrics)
        
        # Step 2: Score metric extractions
        score_metrics = operations.Score(1, False, FinanceWorkflows._metrics_extraction_scorer)
        operations_graph.append_operation(score_metrics)
        
        # Step 3: Keep best metric extractions
        keep_best_metrics = operations.KeepBestN(5, True)  # Keep top 5 for comparison
        operations_graph.append_operation(keep_best_metrics)
        
        # Step 4: Comparative analysis
        comparative_analysis = operations.Aggregate(5)  # 5 comparison attempts
        operations_graph.append_operation(comparative_analysis)
        
        # Step 5: Score comparative analyses
        score_comparisons = operations.Score(1, False, FinanceWorkflows._comparative_analysis_scorer)
        operations_graph.append_operation(score_comparisons)
        
        # Step 6: Keep best comparison
        keep_best_comparison = operations.KeepBestN(1, True)
        operations_graph.append_operation(keep_best_comparison)
        
        # Step 7: Iterative refinement
        for refinement in range(2):
            refine_analysis = operations.Generate(1, 3)
            refine_analysis.add_predecessor(keep_best_comparison)
            operations_graph.add_operation(refine_analysis)
            
            score_refinement = operations.Score(1, False, FinanceWorkflows._comparative_analysis_scorer)
            score_refinement.add_predecessor(refine_analysis)
            operations_graph.add_operation(score_refinement)
            
            keep_refined = operations.KeepBestN(1, True)
            keep_refined.add_predecessor(score_refinement)
            operations_graph.add_operation(keep_refined)
            
            keep_best_comparison = keep_refined
        
        return operations_graph

    # Scoring functions for different workflows
    @staticmethod
    def _risk_analysis_scorer(state):
        """Score risk analysis quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            # Check for risk factors
            risk_factors = data.get('risk_factors', [])
            if risk_factors:
                score += min(len(risk_factors) * 1.0, 5.0)  # Up to 5 points for number of risks
                
                # Check for proper structure
                for risk in risk_factors:
                    if isinstance(risk, dict):
                        if 'severity' in risk and isinstance(risk['severity'], (int, float)):
                            score += 0.5
                        if 'category' in risk:
                            score += 0.3
                        if 'description' in risk:
                            score += 0.2
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _risk_aggregation_scorer(state):
        """Score aggregated risk analysis."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            # Check for consolidated risks
            consolidated_risks = data.get('consolidated_risks', [])
            if consolidated_risks:
                score += min(len(consolidated_risks) * 0.5, 4.0)
                
                # Check for aggregation quality
                for risk in consolidated_risks:
                    if isinstance(risk, dict):
                        if 'frequency' in risk:  # Shows aggregation occurred
                            score += 1.0
                        if 'sources' in risk:
                            score += 0.5
            
            # Check for ranking
            if 'risk_ranking' in data:
                score += 2.0
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _theme_extraction_scorer(state):
        """Score theme extraction quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            themes = data.get('themes', [])
            if themes:
                score += min(len(themes) * 0.8, 5.0)
                
                for theme in themes:
                    if isinstance(theme, dict):
                        if 'frequency' in theme:
                            score += 0.5
                        if 'relevance_score' in theme:
                            score += 0.3
                        if 'category' in theme:
                            score += 0.2
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _theme_aggregation_scorer(state):
        """Score theme aggregation quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            # Check aggregated themes
            aggregated_themes = data.get('aggregated_themes', [])
            if aggregated_themes:
                score += min(len(aggregated_themes) * 0.6, 4.0)
                
                for theme in aggregated_themes:
                    if isinstance(theme, dict):
                        if 'total_frequency' in theme:
                            score += 0.5
                        if 'trend' in theme:
                            score += 0.3
            
            # Check insights
            insights = data.get('key_insights', [])
            if insights:
                score += min(len(insights) * 0.5, 3.0)
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _document_merge_scorer(state):
        """Score document merge quality."""
        current = state.get('current', '')
        
        # Simple heuristics for document quality
        score = 0.0
        
        if len(current) > 500:  # Substantial content
            score += 3.0
        if len(current) > 1000:
            score += 2.0
        
        # Check for structure words
        structure_words = ['summary', 'analysis', 'conclusion', 'key', 'important', 'trend']
        for word in structure_words:
            if word.lower() in current.lower():
                score += 0.5
        
        return min(score, 10.0)

    @staticmethod
    def _requirement_extraction_scorer(state):
        """Score requirement extraction quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            requirements = data.get('requirements', [])
            if requirements:
                score += min(len(requirements) * 1.0, 5.0)
                
                for req in requirements:
                    if isinstance(req, dict):
                        if 'deadline' in req:
                            score += 0.5
                        if 'penalty' in req:
                            score += 0.3
                        if 'jurisdiction' in req:
                            score += 0.2
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _conflict_analysis_scorer(state):
        """Score conflict analysis quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            conflicts = data.get('conflicts', [])
            if conflicts:
                score += min(len(conflicts) * 2.0, 6.0)
                
                for conflict in conflicts:
                    if isinstance(conflict, dict):
                        if 'severity' in conflict:
                            score += 0.5
                        if 'recommendation' in conflict:
                            score += 0.5
            
            # Check compliance matrix
            if 'compliance_matrix' in data:
                score += 2.0
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _validate_compliance_analysis(state):
        """Validate compliance analysis structure."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            # Check required fields
            if 'conflicts' in data or 'requirements' in data:
                return True
            return False
        except:
            return False

    @staticmethod
    def _compliance_final_scorer(state):
        """Final scoring for compliance analysis."""
        base_score = FinanceWorkflows._conflict_analysis_scorer(state)
        
        # Bonus for validation
        if state.get('valid', False):
            base_score += 2.0
        
        return min(base_score, 10.0)

    @staticmethod
    def _metrics_extraction_scorer(state):
        """Score metrics extraction quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            company_metrics = data.get('company_metrics', {})
            if company_metrics:
                # Check for essential metrics
                essential_metrics = ['revenue', 'net_income', 'total_assets', 'roe', 'roa']
                for metric in essential_metrics:
                    if metric in company_metrics:
                        score += 1.0
                
                # Check for calculated ratios
                ratio_metrics = ['debt_to_equity', 'profit_margin', 'current_ratio']
                for metric in ratio_metrics:
                    if metric in company_metrics:
                        score += 0.5
            
            return min(score, 10.0)
        except:
            return 1.0

    @staticmethod
    def _comparative_analysis_scorer(state):
        """Score comparative analysis quality."""
        try:
            import json
            
            current = state.get('current', '{}')
            if isinstance(current, str):
                data = json.loads(current)
            else:
                data = current
            
            score = 0.0
            
            comparative_analysis = data.get('comparative_analysis', {})
            if comparative_analysis:
                # Check for rankings
                rankings = comparative_analysis.get('rankings', {})
                if rankings:
                    score += min(len(rankings) * 1.0, 4.0)
                
                # Check for peer analysis
                peer_analysis = comparative_analysis.get('peer_analysis', [])
                if peer_analysis:
                    score += min(len(peer_analysis) * 0.5, 3.0)
                
                # Check for benchmarks
                if 'market_benchmarks' in comparative_analysis:
                    score += 2.0
            
            return min(score, 10.0)
        except:
            return 1.0
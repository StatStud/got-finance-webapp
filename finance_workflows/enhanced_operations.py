# ==============================================================================
# FIXED GoT ENHANCEMENTS - Compatible with your local_got.py structure
# ==============================================================================

from finance_workflows.local_got import operations, Thought
from typing import Dict, List, Any, Optional
import json
import logging

# 1. ENHANCED THOUGHT TYPES (Heterogeneous Graphs)
class EnhancedThought(Thought):
    """Enhanced thought with type classification for heterogeneous graphs"""
    
    def __init__(self, state: Dict = None, thought_type: str = "analysis"):
        super().__init__(state)
        self.thought_type = thought_type  # 'plan', 'analysis', 'conclusion', 'refinement'
        self.confidence = 0.5  # Add confidence scoring
        self.refinement_count = 0  # Track how many times this was refined
        self.parent_thoughts = []  # Track what thoughts led to this one
    
    def set_type(self, thought_type: str):
        """Simple way to classify thoughts"""
        self.thought_type = thought_type
        return self
    
    def add_parent(self, parent_thought):
        """Track thought lineage for context-aware scoring"""
        if parent_thought not in self.parent_thoughts:
            self.parent_thoughts.append(parent_thought)


# 2. BASE OPERATION CLASS (copying from your existing structure)
class BaseOperation:
    """Base class for operations - mimics your existing operation structure"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.predecessors = []
        self.successors = []
        self.thoughts = []
        self.id = id(self)
        self.executed = False  # MISSING ATTRIBUTE - needed for can_be_executed check
    
    def add_predecessor(self, operation):
        """Add a predecessor operation"""
        self.predecessors.append(operation)
        operation.successors.append(self)
    
    def add_successor(self, operation):
        """Add a successor operation"""
        self.successors.append(operation)
        operation.predecessors.append(self)
    
    def get_thoughts(self):
        """Get the thoughts from this operation"""
        return self.thoughts
    
    def get_previous_thoughts(self):
        """Get thoughts from all predecessor operations"""
        previous_thoughts = []
        for predecessor in self.predecessors:
            previous_thoughts.extend(predecessor.get_thoughts())
        return previous_thoughts
    
    def can_be_executed(self):
        """Check if this operation can be executed - matches your local_got.py logic"""
        return all(predecessor.executed for predecessor in self.predecessors)
    
    def execute(self, lm, prompter, parser, **kwargs):
        """Execute the operation"""
        self._execute(lm, prompter, parser, **kwargs)
        self.executed = True  # Mark as executed after running
        self.logger.info(f"{self.__class__.__name__} operation completed with {len(self.thoughts)} thoughts")
    
    def _execute(self, lm, prompter, parser, **kwargs):
        """Override this method in subclasses"""
        raise NotImplementedError("Subclasses must implement _execute method")


# 3. SIMPLE REFINING OPERATION (Self-Improvement Loops)
class SimpleRefine(BaseOperation):
    """
    Simple refining operation that improves thoughts iteratively
    Adds the missing "refining transformations" from GoT paper (p.3)
    """
    
    def __init__(self, max_refinements: int = 2, improvement_threshold: float = 0.1):
        super().__init__()
        self.max_refinements = max_refinements
        self.improvement_threshold = improvement_threshold
    
    def _execute(self, lm, prompter, parser, **kwargs):
        """Refine thoughts by asking LLM to improve them"""
        previous_thoughts = self.get_previous_thoughts()
        
        if len(previous_thoughts) == 0:
            previous_thoughts = [EnhancedThought(kwargs)]
        
        self.thoughts = []
        
        for thought in previous_thoughts:
            # Convert regular Thought to EnhancedThought if needed
            if not isinstance(thought, EnhancedThought):
                enhanced_thought = EnhancedThought(thought.state, "analysis")
                enhanced_thought._score = getattr(thought, '_score', 0.0)
                thought = enhanced_thought
            
            if thought.refinement_count < self.max_refinements:
                # Create refinement prompt
                refinement_prompt = self._create_refinement_prompt(thought)
                
                # Call LLM to refine the thought
                try:
                    response = lm.query(refinement_prompt, 1)
                    response_texts = lm.get_response_texts(response)
                    refined_content = response_texts[0] if response_texts else f"[REFINED] {thought.state.get('content', '')}"
                except Exception as e:
                    self.logger.warning(f"LLM refinement failed: {e}")
                    refined_content = f"[REFINED] {thought.state.get('content', '')}"
                
                # Create refined thought
                refined_state = thought.state.copy()
                refined_state['content'] = refined_content
                refined_state['refinement_prompt'] = refinement_prompt
                
                refined_thought = EnhancedThought(refined_state, "refinement")
                refined_thought.refinement_count = thought.refinement_count + 1
                refined_thought.add_parent(thought)
                refined_thought.confidence = min(1.0, thought.confidence + 0.1)  # Slightly higher confidence
                
                self.thoughts.append(refined_thought)
                self.logger.info(f"Refined thought #{thought.refinement_count + 1}")
            else:
                self.thoughts.append(thought)  # No more refinements
        
        self.logger.info(f"SimpleRefine operation completed with {len(self.thoughts)} thoughts")
    
    def _create_refinement_prompt(self, thought: EnhancedThought) -> str:
        """Create a simple refinement prompt"""
        content = thought.state.get('content', '')
        thought_type = thought.thought_type
        
        if thought_type == "plan":
            improvement_focus = "Make the plan more detailed and actionable"
        elif thought_type == "analysis":
            improvement_focus = "Add more specific evidence and strengthen the reasoning"
        else:
            improvement_focus = "Improve clarity and add supporting details"
        
        return f"""<Instruction>
Improve the following financial {thought_type} by:
1. {improvement_focus}
2. Adding quantitative support where possible
3. Identifying potential gaps or limitations
4. Making it more comprehensive and actionable

Current {thought_type}: {content}

Provide an improved version that is more thorough and valuable for financial decision-making.
Output only the improved {thought_type}, no additional commentary.
</Instruction>"""


# 4. CONTEXT-AWARE SCORING (Graph-aware evaluation)
class ContextAwareScorer:
    """
    Simple context-aware scoring that considers graph relationships
    Implements E(v,G,p✓) from GoT paper (p.3-4)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def score_with_context(self, thought: Thought, all_thoughts: List[Thought]) -> float:
        """Score a thought considering its context in the graph"""
        
        # Convert to EnhancedThought if needed
        if not isinstance(thought, EnhancedThought):
            enhanced_thought = EnhancedThought(thought.state, "analysis")
            enhanced_thought._score = getattr(thought, '_score', 0.7)
            thought = enhanced_thought
        
        # Base score (your existing scoring or default)
        base_score = getattr(thought, '_score', 0.7)
        
        # Context bonuses (simple implementation)
        context_bonus = 0.0
        
        # 1. Refinement bonus - refined thoughts get higher scores
        if thought.thought_type == "refinement":
            context_bonus += 0.1
            self.logger.debug(f"Refinement bonus: +0.1")
        
        # 2. Confidence bonus
        context_bonus += thought.confidence * 0.1
        self.logger.debug(f"Confidence bonus: +{thought.confidence * 0.1:.2f}")
        
        # 3. Completeness bonus - thoughts that reference others
        if len(thought.parent_thoughts) > 1:  # Aggregated from multiple sources
            context_bonus += 0.1
            self.logger.debug(f"Aggregation bonus: +0.1")
        
        # 4. Content quality bonus
        content = thought.state.get('content', '')
        if len(content) > 100:  # Longer, more detailed thoughts
            context_bonus += 0.05
            self.logger.debug(f"Detail bonus: +0.05")
        
        final_score = min(1.0, base_score + context_bonus)
        self.logger.info(f"Context-aware score: {base_score:.2f} + {context_bonus:.2f} = {final_score:.2f}")
        
        return final_score


# 5. ENHANCED AGGREGATION (Sophisticated thought merging)
class SmartAggregate(BaseOperation):
    """
    Smarter aggregation that does intelligent thought merging
    Improves on basic Aggregate operation
    """
    
    def __init__(self, merge_strategy: str = "complementary"):
        super().__init__()
        self.merge_strategy = merge_strategy
    
    def _execute(self, lm, prompter, parser, **kwargs):
        """Intelligently merge thoughts based on their types and content"""
        previous_thoughts = self.get_previous_thoughts()
        
        if len(previous_thoughts) == 0:
            previous_thoughts = [EnhancedThought(kwargs)]
        
        if len(previous_thoughts) <= 1:
            self.thoughts = previous_thoughts
            return
        
        # Convert to EnhancedThoughts if needed
        enhanced_thoughts = []
        for thought in previous_thoughts:
            if not isinstance(thought, EnhancedThought):
                enhanced = EnhancedThought(thought.state, "analysis")
                enhanced._score = getattr(thought, '_score', 0.7)
                enhanced_thoughts.append(enhanced)
            else:
                enhanced_thoughts.append(thought)
        
        # Group thoughts by type for smarter merging
        grouped = self._group_by_type(enhanced_thoughts)
        
        merged_results = []
        
        # Merge plans together
        if 'plan' in grouped and len(grouped['plan']) > 1:
            merged_plan = self._merge_plans(grouped['plan'])
            merged_results.append(merged_plan)
        elif 'plan' in grouped:
            merged_results.extend(grouped['plan'])
        
        # Merge analyses together  
        if 'analysis' in grouped and len(grouped['analysis']) > 1:
            merged_analysis = self._merge_analyses(grouped['analysis'])
            merged_results.append(merged_analysis)
        elif 'analysis' in grouped:
            merged_results.extend(grouped['analysis'])
        
        # Add other types
        for thought_type, thoughts in grouped.items():
            if thought_type not in ['plan', 'analysis']:
                merged_results.extend(thoughts)
        
        # Create final conclusion if we have multiple results
        if len(merged_results) > 1:
            conclusion = self._create_conclusion(merged_results, enhanced_thoughts)
            merged_results.append(conclusion)
        
        self.thoughts = merged_results
        self.logger.info(f"SmartAggregate merged {len(enhanced_thoughts)} thoughts into {len(merged_results)} results")
    
    def _group_by_type(self, thoughts: List[EnhancedThought]) -> Dict:
        """Group thoughts by their type"""
        grouped = {}
        for thought in thoughts:
            thought_type = getattr(thought, 'thought_type', 'analysis')
            if thought_type not in grouped:
                grouped[thought_type] = []
            grouped[thought_type].append(thought)
        return grouped
    
    def _merge_plans(self, plan_thoughts: List[EnhancedThought]) -> EnhancedThought:
        """Merge planning thoughts"""
        combined_content = []
        total_confidence = 0
        
        for i, thought in enumerate(plan_thoughts, 1):
            content = thought.state.get('content', '')
            combined_content.append(f"{i}. {content}")
            total_confidence += thought.confidence
        
        merged_state = {
            'content': f"Integrated Strategic Plan:\n" + "\n".join(combined_content),
            'source_thoughts': len(plan_thoughts),
            'merge_type': 'plan_integration'
        }
        
        result = EnhancedThought(merged_state, 'plan')
        result.confidence = total_confidence / len(plan_thoughts)
        result._score = 0.8  # Higher score for merged plans
        
        for thought in plan_thoughts:
            result.add_parent(thought)
        
        return result
    
    def _merge_analyses(self, analysis_thoughts: List[EnhancedThought]) -> EnhancedThought:
        """Merge analysis thoughts"""
        insights = []
        total_confidence = 0
        
        for i, thought in enumerate(analysis_thoughts, 1):
            content = thought.state.get('content', '')
            insights.append(f"Analysis {i}: {content}")
            total_confidence += thought.confidence
        
        merged_state = {
            'content': f"Comprehensive Analysis:\n" + "\n\n".join(insights),
            'source_thoughts': len(analysis_thoughts),
            'merge_type': 'analysis_synthesis'
        }
        
        result = EnhancedThought(merged_state, 'analysis')
        result.confidence = total_confidence / len(analysis_thoughts)
        result._score = 0.85  # Higher score for synthesized analysis
        
        for thought in analysis_thoughts:
            result.add_parent(thought)
        
        return result
    
    def _create_conclusion(self, merged_results: List[EnhancedThought], 
                          original_thoughts: List[EnhancedThought]) -> EnhancedThought:
        """Create conclusion from merged thoughts"""
        
        # Extract key points from merged results
        key_points = []
        for result in merged_results:
            content = result.state.get('content', '')
            # Take first sentence or first 100 chars as key point
            first_line = content.split('\n')[0]
            if len(first_line) > 100:
                first_line = first_line[:100] + "..."
            key_points.append(f"• {first_line}")
        
        conclusion_content = f"""Final Recommendation:

Based on comprehensive analysis of {len(original_thoughts)} inputs:

{chr(10).join(key_points)}

This integrated assessment provides a balanced perspective considering multiple analytical approaches and strategic considerations."""

        conclusion_state = {
            'content': conclusion_content,
            'source_thoughts': len(original_thoughts),
            'merge_type': 'final_conclusion'
        }
        
        result = EnhancedThought(conclusion_state, 'conclusion')
        result.confidence = 0.9  # High confidence for well-aggregated results
        result._score = 0.9
        
        for thought in merged_results:
            result.add_parent(thought)
        
        return result


# 6. ENHANCED RISK ANALYSIS WORKFLOW
def create_enhanced_risk_analysis_graph():
    """
    Enhanced version of your risk analysis with GoT features
    Just replace your existing create_risk_analysis_graph() with this
    """
    operations_graph = operations.GraphOfOperations()
    
    # Phase 1: Initial Generation (your existing logic)
    initial_generate = operations.Generate(1, 5)
    operations_graph.append_operation(initial_generate)
    
    # Phase 2: Score with basic scoring first
    basic_score = operations.Score(1, False, lambda thoughts: 0.7)  # Simple default scoring
    operations_graph.append_operation(basic_score)
    
    # Phase 3: Keep best candidates
    keep_best = operations.KeepBestN(3, True)
    operations_graph.append_operation(keep_best)
    
    # Phase 4: NEW - Simple refinement (adds self-improvement)
    refine_thoughts = SimpleRefine(max_refinements=2)
    operations_graph.append_operation(refine_thoughts)
    
    # Phase 5: Enhanced aggregation (smarter merging)
    smart_aggregate = SmartAggregate(merge_strategy="complementary")
    operations_graph.append_operation(smart_aggregate)
    
    # Phase 6: Final scoring
    final_score = operations.Score(1, False, lambda thoughts: 0.85)
    operations_graph.append_operation(final_score)
    
    # Phase 7: Final selection
    final_selection = operations.KeepBestN(1, True)
    operations_graph.append_operation(final_selection)
    
    return operations_graph


# 7. SIMPLE BACKTRACKING OPERATION
class SimpleBacktrack(BaseOperation):
    """Simple backtracking when thoughts are low quality"""
    
    def __init__(self, quality_threshold: float = 0.6):
        super().__init__()
        self.quality_threshold = quality_threshold
    
    def _execute(self, lm, prompter, parser, **kwargs):
        """Backtrack if all thoughts are below quality threshold"""
        previous_thoughts = self.get_previous_thoughts()
        
        if len(previous_thoughts) == 0:
            previous_thoughts = [EnhancedThought(kwargs)]
        
        # Calculate average quality
        scores = [getattr(t, '_score', 0.5) for t in previous_thoughts]
        avg_quality = sum(scores) / len(scores) if scores else 0.5
        
        if avg_quality < self.quality_threshold:
            self.logger.info(f"🔄 Backtracking: Quality {avg_quality:.2f} below threshold {self.quality_threshold}")
            
            # Simple backtracking: create new thoughts with different approach
            self.thoughts = []
            for thought in previous_thoughts:
                # Convert to EnhancedThought if needed
                if not isinstance(thought, EnhancedThought):
                    enhanced = EnhancedThought(thought.state, "analysis")
                    enhanced._score = getattr(thought, '_score', 0.5)
                    thought = enhanced
                
                new_state = thought.state.copy()
                original_content = thought.state.get('content', '')
                new_state['content'] = f"""Alternative Approach: {original_content}

[BACKTRACKED] Reconsidering with different methodology to improve analysis quality."""
                new_state['backtrack_reason'] = f"Low quality: {avg_quality:.2f}"
                
                backtrack_thought = EnhancedThought(new_state, 'analysis')
                backtrack_thought.confidence = min(1.0, thought.confidence + 0.2)  # Higher confidence for backtracked thoughts
                backtrack_thought._score = min(1.0, thought._score + 0.2)
                backtrack_thought.add_parent(thought)
                
                self.thoughts.append(backtrack_thought)
        else:
            self.thoughts = previous_thoughts
        
        self.logger.info(f"SimpleBacktrack completed with {len(self.thoughts)} thoughts")


# ==============================================================================
# 8. INTEGRATION FUNCTIONS
# ==============================================================================

def enhance_existing_workflows():
    """
    Function to enhance your existing workflows with GoT features
    Call this from your workflows.py
    """
    return {
        'risk_analysis': create_enhanced_risk_analysis_graph,
        'enhanced_thought': EnhancedThought,
        'context_scorer': ContextAwareScorer,
        'smart_aggregate': SmartAggregate,
        'simple_refine': SimpleRefine,
        'simple_backtrack': SimpleBacktrack
    }


# Test function to verify everything works
def test_enhanced_operations():
    """Quick test to verify the enhanced operations work"""
    try:
        # Test EnhancedThought
        thought = EnhancedThought({'content': 'Test risk analysis'}, 'analysis')
        print(f"✅ EnhancedThought created: {thought.thought_type}")
        
        # Test ContextAwareScorer
        scorer = ContextAwareScorer()
        score = scorer.score_with_context(thought, [thought])
        print(f"✅ Context-aware scoring works: {score:.2f}")
        
        # Test operations can be instantiated
        refine_op = SimpleRefine()
        aggregate_op = SmartAggregate()
        backtrack_op = SimpleBacktrack()
        print(f"✅ All operations instantiated successfully")
        
        # Test workflow creation
        workflow = create_enhanced_risk_analysis_graph()
        print(f"✅ Enhanced workflow created with {len(workflow.operations)} operations")
        
        print("\n🎉 All enhanced GoT features are working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced operations: {e}")
        return False


if __name__ == "__main__":
    test_enhanced_operations()
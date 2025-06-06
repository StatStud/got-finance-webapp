"""
Finance-specific parsers for Graph of Thoughts workflows.
These inherit from the GoT Parser base class and provide specialized parsing
for financial analysis responses.
"""

import json
import re
import logging
from typing import Dict, List, Union, Any
from graph_of_thoughts.parser.parser import Parser

logger = logging.getLogger(__name__)


class FinanceBaseParser(Parser):
    """Base parser with common finance parsing utilities."""
    
    def extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """Extract JSON content from text that may contain additional formatting."""
        try:
            # First try to parse the entire text as JSON
            return json.loads(text.strip())
        except json.JSONDecodeError:
            # Look for JSON content within the text
            json_patterns = [
                r'\{.*\}',  # Find content between outermost braces
                r'```json\s*(\{.*?\})\s*```',  # Extract from code blocks
                r'```\s*(\{.*?\})\s*```',  # Extract from generic code blocks
            ]
            
            for pattern in json_patterns:
                matches = re.findall(pattern, text, re.DOTALL)
                for match in matches:
                    try:
                        return json.loads(match)
                    except json.JSONDecodeError:
                        continue
            
            # If no valid JSON found, return error structure
            logger.warning(f"Could not extract JSON from text: {text[:200]}...")
            return {"error": "Invalid JSON format", "raw_text": text}

    def extract_score_from_text(self, text: str) -> float:
        """Extract numeric score from text."""
        try:
            # Look for standalone numbers
            numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
            if numbers:
                score = float(numbers[-1])  # Take the last number found
                return min(max(score, 0), 10)  # Clamp between 0 and 10
            return 0.0
        except (ValueError, IndexError):
            return 0.0


class RiskAnalysisParser(FinanceBaseParser):
    """Parser for risk analysis workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated risk analysis results."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            # Combine with existing state
            base_state = states[0].copy() if states else {}
            
            # Extract consolidated risks and rankings
            consolidated_risks = parsed_data.get('consolidated_risks', [])
            risk_ranking = parsed_data.get('risk_ranking', [])
            
            new_state = {
                **base_state,
                'current': json.dumps(parsed_data),
                'risk_factors': consolidated_risks,
                'ranked_risks': risk_ranking,
                'severity_scores': {
                    risk['factor']: risk['severity'] 
                    for risk in consolidated_risks 
                    if 'factor' in risk and 'severity' in risk
                }
            }
            
            new_states.append(new_state)
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated risk analysis responses."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            # Extract risk factors
            risk_factors = parsed_data.get('risk_factors', [])
            
            new_state = state.copy()
            new_state.update({
                'current': json.dumps(parsed_data),
                'risk_factors': risk_factors,
                'severity_scores': {
                    risk['factor']: risk['severity'] 
                    for risk in risk_factors 
                    if isinstance(risk, dict) and 'factor' in risk and 'severity' in risk
                }
            })
            
            new_states.append(new_state)
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved risk analysis."""
        if not texts:
            return state
            
        text = texts[0]
        parsed_data = self.extract_json_from_text(text)
        
        improved_state = state.copy()
        improved_state.update({
            'current': json.dumps(parsed_data),
            'risk_factors': parsed_data.get('risk_factors', []),
            'severity_scores': {
                risk['factor']: risk['severity'] 
                for risk in parsed_data.get('risk_factors', [])
                if isinstance(risk, dict) and 'factor' in risk and 'severity' in risk
            }
        })
        
        return improved_state

    def parse_validation_answer(self, state: Dict, texts: List[str]) -> bool:
        """Parse validation response."""
        if not texts:
            return False
        
        text = texts[0].lower()
        positive_indicators = ['valid', 'correct', 'good', 'yes', 'true', 'pass']
        return any(indicator in text for indicator in positive_indicators)

    def parse_score_answer(self, states: List[Dict], texts: List[str]) -> List[float]:
        """Parse scoring responses."""
        scores = []
        for text in texts:
            score = self.extract_score_from_text(text)
            scores.append(score)
        return scores if scores else [0.0]


class DocumentMergeParser(FinanceBaseParser):
    """Parser for document merge workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated document merge results."""
        new_states = []
        
        for text in texts:
            if states and 'parts' in states[0] and len(states[0]['parts']) > 0:
                # Aggregating themes
                parsed_data = self.extract_json_from_text(text)
                themes = parsed_data.get('aggregated_themes', [])
                insights = parsed_data.get('key_insights', [])
                
                base_state = states[0].copy()
                new_state = {
                    **base_state,
                    'current': json.dumps(parsed_data),
                    'themes': themes,
                    'key_insights': insights,
                    'theme_frequencies': {
                        theme['theme']: theme['total_frequency']
                        for theme in themes
                        if isinstance(theme, dict) and 'theme' in theme and 'total_frequency' in theme
                    }
                }
            else:
                # Merging full documents
                base_state = states[0].copy() if states else {}
                new_state = {
                    **base_state,
                    'current': text,
                    'merged_document': text
                }
            
            new_states.append(new_state)
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated theme extraction or document merge responses."""
        new_states = []
        
        for text in texts:
            new_state = state.copy()
            
            # Try to parse as JSON (theme extraction)
            parsed_data = self.extract_json_from_text(text)
            
            if 'themes' in parsed_data:
                # This is theme extraction
                themes = parsed_data.get('themes', [])
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'themes': themes,
                    'theme_frequencies': {
                        theme['theme']: theme['frequency']
                        for theme in themes
                        if isinstance(theme, dict) and 'theme' in theme and 'frequency' in theme
                    }
                })
            else:
                # This is document merge or plain text
                new_state.update({
                    'current': text,
                    'merged_document': text
                })
            
            new_states.append(new_state)
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved document merge."""
        if not texts:
            return state
            
        improved_state = state.copy()
        improved_state['current'] = texts[0]
        improved_state['merged_document'] = texts[0]
        
        return improved_state

    def parse_validation_answer(self, state: Dict, texts: List[str]) -> bool:
        """Parse validation response."""
        if not texts:
            return False
        
        text = texts[0].lower()
        positive_indicators = ['valid', 'coherent', 'good', 'yes', 'true', 'pass']
        return any(indicator in text for indicator in positive_indicators)

    def parse_score_answer(self, states: List[Dict], texts: List[str]) -> List[float]:
        """Parse scoring responses."""
        scores = []
        for text in texts:
            score = self.extract_score_from_text(text)
            scores.append(score)
        return scores if scores else [0.0]


class ComplianceAnalysisParser(FinanceBaseParser):
    """Parser for compliance analysis workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated compliance analysis results."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            base_state = states[0].copy() if states else {}
            
            conflicts = parsed_data.get('conflicts', [])
            compliance_matrix = parsed_data.get('compliance_matrix', {})
            
            new_state = {
                **base_state,
                'current': json.dumps(parsed_data),
                'conflicts': conflicts,
                'compliance_matrix': compliance_matrix,
                'requirements': base_state.get('requirements', [])
            }
            
            new_states.append(new_state)
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated compliance analysis responses."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            new_state = state.copy()
            
            if 'requirements' in parsed_data:
                # This is requirement extraction
                requirements = parsed_data.get('requirements', [])
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'requirements': requirements
                })
            elif 'conflicts' in parsed_data:
                # This is conflict analysis
                conflicts = parsed_data.get('conflicts', [])
                compliance_matrix = parsed_data.get('compliance_matrix', {})
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'conflicts': conflicts,
                    'compliance_matrix': compliance_matrix
                })
            else:
                new_state['current'] = json.dumps(parsed_data)
            
            new_states.append(new_state)
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved compliance analysis."""
        if not texts:
            return state
            
        text = texts[0]
        parsed_data = self.extract_json_from_text(text)
        
        improved_state = state.copy()
        improved_state.update({
            'current': json.dumps(parsed_data),
            'conflicts': parsed_data.get('conflicts', []),
            'compliance_matrix': parsed_data.get('compliance_matrix', {}),
            'requirements': parsed_data.get('requirements', state.get('requirements', []))
        })
        
        return improved_state

    def parse_validation_answer(self, state: Dict, texts: List[str]) -> bool:
        """Parse validation response."""
        if not texts:
            return False
        
        text = texts[0].lower()
        positive_indicators = ['valid', 'compliant', 'correct', 'good', 'yes', 'true', 'pass']
        return any(indicator in text for indicator in positive_indicators)

    def parse_score_answer(self, states: List[Dict], texts: List[str]) -> List[float]:
        """Parse scoring responses."""
        scores = []
        for text in texts:
            score = self.extract_score_from_text(text)
            scores.append(score)
        return scores if scores else [0.0]


class FinancialMetricsParser(FinanceBaseParser):
    """Parser for financial metrics workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated financial metrics comparison results."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            base_state = states[0].copy() if states else {}
            
            comparative_analysis = parsed_data.get('comparative_analysis', {})
            rankings = comparative_analysis.get('rankings', {})
            peer_analysis = comparative_analysis.get('peer_analysis', [])
            
            new_state = {
                **base_state,
                'current': json.dumps(parsed_data),
                'comparative_analysis': comparative_analysis,
                'rankings': rankings,
                'peer_analysis': peer_analysis
            }
            
            new_states.append(new_state)
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated financial metrics responses."""
        new_states = []
        
        for text in texts:
            parsed_data = self.extract_json_from_text(text)
            
            new_state = state.copy()
            
            if 'company_metrics' in parsed_data:
                # This is metrics extraction
                company_metrics = parsed_data.get('company_metrics', {})
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'company_metrics': company_metrics,
                    'metrics': [company_metrics]
                })
            elif 'comparative_analysis' in parsed_data:
                # This is comparative analysis
                comparative_analysis = parsed_data.get('comparative_analysis', {})
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'comparative_analysis': comparative_analysis,
                    'rankings': comparative_analysis.get('rankings', {})
                })
            else:
                new_state['current'] = json.dumps(parsed_data)
            
            new_states.append(new_state)
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved financial metrics analysis."""
        if not texts:
            return state
            
        text = texts[0]
        parsed_data = self.extract_json_from_text(text)
        
        improved_state = state.copy()
        improved_state.update({
            'current': json.dumps(parsed_data),
            'comparative_analysis': parsed_data.get('comparative_analysis', {}),
            'rankings': parsed_data.get('comparative_analysis', {}).get('rankings', {}),
            'metrics': parsed_data.get('metrics', state.get('metrics', []))
        })
        
        return improved_state

    def parse_validation_answer(self, state: Dict, texts: List[str]) -> bool:
        """Parse validation response."""
        if not texts:
            return False
        
        text = texts[0].lower()
        positive_indicators = ['valid', 'accurate', 'correct', 'good', 'yes', 'true', 'pass']
        return any(indicator in text for indicator in positive_indicators)

    def parse_score_answer(self, states: List[Dict], texts: List[str]) -> List[float]:
        """Parse scoring responses."""
        scores = []
        for text in texts:
            score = self.extract_score_from_text(text)
            scores.append(score)
        return scores if scores else [0.0]
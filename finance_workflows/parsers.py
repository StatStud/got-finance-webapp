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
        if not text or not text.strip():
            return {"error": "Empty text provided", "raw_text": text}
            
        text = text.strip()
        
        try:
            # First try to parse the entire text as JSON
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Look for JSON content within the text using improved patterns
        json_patterns = [
            r'```json\s*(\{.*?\})\s*```',  # Extract from json code blocks
            r'```\s*(\{.*?\})\s*```',      # Extract from generic code blocks
            r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\})',  # Better balanced braces pattern
        ]
        
        for pattern in json_patterns:
            try:
                matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
                for match in matches:
                    try:
                        parsed = json.loads(match.strip())
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.debug(f"Pattern {pattern} failed: {e}")
                continue
        
        # Try to find the largest JSON-like structure
        try:
            # Find opening brace and try to find matching closing brace
            start_idx = text.find('{')
            if start_idx != -1:
                brace_count = 0
                for i, char in enumerate(text[start_idx:], start_idx):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_candidate = text[start_idx:i+1]
                            try:
                                return json.loads(json_candidate)
                            except json.JSONDecodeError:
                                break
        except Exception as e:
            logger.debug(f"Brace matching failed: {e}")
        
        # If all else fails, try to construct a minimal valid response
        logger.warning(f"Could not extract valid JSON from text: {text[:200]}...")
        
        # Try to extract key-value pairs manually for common patterns
        if 'risk_factors' in text.lower():
            return self._extract_risk_factors_fallback(text)
        elif 'themes' in text.lower():
            return self._extract_themes_fallback(text)
        elif 'requirements' in text.lower():
            return self._extract_requirements_fallback(text)
        elif 'company_metrics' in text.lower():
            return self._extract_metrics_fallback(text)
        
        return {"error": "Could not parse JSON", "raw_text": text[:500]}

    def _extract_risk_factors_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback extraction for risk factors when JSON parsing fails."""
        try:
            # Simple extraction based on common patterns
            risk_factors = []
            
            # Look for lines that might contain risk information
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if any(keyword in line.lower() for keyword in ['risk', 'threat', 'challenge', 'exposure']):
                    # Extract a simple risk factor
                    risk_factors.append({
                        "factor": line[:50] + "..." if len(line) > 50 else line,
                        "description": line,
                        "severity": 5,  # Default severity
                        "category": "operational"
                    })
            
            return {
                "risk_factors": risk_factors[:5]  # Limit to 5 factors
            }
        except Exception as e:
            logger.error(f"Fallback risk extraction failed: {e}")
            return {"risk_factors": []}

    def _extract_themes_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback extraction for themes when JSON parsing fails."""
        try:
            themes = []
            
            # Simple theme extraction
            common_themes = ['earnings', 'growth', 'revenue', 'profit', 'strategy', 'market', 'risk']
            
            for theme in common_themes:
                if theme in text.lower():
                    themes.append({
                        "theme": theme.title(),
                        "frequency": text.lower().count(theme),
                        "relevance_score": 5,
                        "category": "financial"
                    })
            
            return {"themes": themes}
        except Exception as e:
            logger.error(f"Fallback theme extraction failed: {e}")
            return {"themes": []}

    def _extract_requirements_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback extraction for requirements when JSON parsing fails."""
        try:
            requirements = []
            
            # Simple requirement extraction
            lines = text.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['must', 'shall', 'required', 'minimum']):
                    requirements.append({
                        "requirement_id": f"REQ_{len(requirements)+1:03d}",
                        "description": line.strip(),
                        "jurisdiction": "Unknown",
                        "deadline": "TBD"
                    })
            
            return {"requirements": requirements[:5]}
        except Exception as e:
            logger.error(f"Fallback requirement extraction failed: {e}")
            return {"requirements": []}

    def _extract_metrics_fallback(self, text: str) -> Dict[str, Any]:
        """Fallback extraction for financial metrics when JSON parsing fails."""
        try:
            # Extract numbers that might be financial metrics
            numbers = re.findall(r'\d+\.?\d*', text)
            
            return {
                "company_metrics": {
                    "company_name": "Unknown Company",
                    "revenue": float(numbers[0]) if len(numbers) > 0 else 0,
                    "net_income": float(numbers[1]) if len(numbers) > 1 else 0,
                    "total_assets": float(numbers[2]) if len(numbers) > 2 else 0,
                    "roe": 0.1,
                    "roa": 0.05
                }
            }
        except Exception as e:
            logger.error(f"Fallback metrics extraction failed: {e}")
            return {"company_metrics": {}}

    def extract_score_from_text(self, text: str) -> float:
        """Extract numeric score from text."""
        try:
            # Look for standalone numbers
            numbers = re.findall(r'\b(\d+(?:\.\d+)?)\b', text)
            if numbers:
                score = float(numbers[-1])  # Take the last number found
                return min(max(score, 0), 10)  # Clamp between 0 and 10
            return 5.0  # Default middle score
        except (ValueError, IndexError):
            return 5.0


class RiskAnalysisParser(FinanceBaseParser):
    """Parser for risk analysis workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated risk analysis results."""
        new_states = []
        
        for text in texts:
            try:
                parsed_data = self.extract_json_from_text(text)
                
                # Combine with existing state
                base_state = states[0].copy() if states else {}
                
                # Extract consolidated risks and rankings
                consolidated_risks = parsed_data.get('consolidated_risks', [])
                if not consolidated_risks and 'risk_factors' in parsed_data:
                    consolidated_risks = parsed_data['risk_factors']
                
                risk_ranking = parsed_data.get('risk_ranking', [])
                if not risk_ranking and consolidated_risks:
                    # Create basic ranking from severity
                    risk_ranking = [risk.get('factor', f'Risk {i+1}') 
                                  for i, risk in enumerate(sorted(consolidated_risks, 
                                  key=lambda x: x.get('severity', 0), reverse=True))]
                
                new_state = {
                    **base_state,
                    'current': json.dumps(parsed_data),
                    'risk_factors': consolidated_risks,
                    'ranked_risks': risk_ranking,
                    'severity_scores': {
                        risk.get('factor', f'Risk {i+1}'): risk.get('severity', 0) 
                        for i, risk in enumerate(consolidated_risks)
                        if isinstance(risk, dict)
                    }
                }
                
                new_states.append(new_state)
            except Exception as e:
                logger.error(f"Error parsing aggregation answer: {e}")
                # Return a basic error state
                new_states.append({
                    'current': '{"error": "Failed to parse aggregation"}',
                    'risk_factors': [],
                    'ranked_risks': [],
                    'severity_scores': {}
                })
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated risk analysis responses."""
        new_states = []
        
        for text in texts:
            try:
                parsed_data = self.extract_json_from_text(text)
                
                # Extract risk factors
                risk_factors = parsed_data.get('risk_factors', [])
                
                new_state = state.copy()
                new_state.update({
                    'current': json.dumps(parsed_data),
                    'risk_factors': risk_factors,
                    'severity_scores': {
                        risk.get('factor', f'Risk {i+1}'): risk.get('severity', 0)
                        for i, risk in enumerate(risk_factors) 
                        if isinstance(risk, dict)
                    }
                })
                
                new_states.append(new_state)
            except Exception as e:
                logger.error(f"Error parsing generate answer: {e}")
                # Return a basic error state
                new_states.append({
                    **state,
                    'current': '{"error": "Failed to parse generation"}',
                    'risk_factors': [],
                    'severity_scores': {}
                })
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved risk analysis."""
        if not texts:
            return state
            
        try:
            text = texts[0]
            parsed_data = self.extract_json_from_text(text)
            
            improved_state = state.copy()
            improved_state.update({
                'current': json.dumps(parsed_data),
                'risk_factors': parsed_data.get('risk_factors', []),
                'severity_scores': {
                    risk.get('factor', f'Risk {i+1}'): risk.get('severity', 0)
                    for i, risk in enumerate(parsed_data.get('risk_factors', []))
                    if isinstance(risk, dict)
                }
            })
            
            return improved_state
        except Exception as e:
            logger.error(f"Error parsing improve answer: {e}")
            return state

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
        return scores if scores else [5.0]


class DocumentMergeParser(FinanceBaseParser):
    """Parser for document merge workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated document merge results."""
        new_states = []
        
        for text in texts:
            try:
                if states and 'parts' in states[0] and len(states[0]['parts']) > 0:
                    # Aggregating themes
                    parsed_data = self.extract_json_from_text(text)
                    themes = parsed_data.get('aggregated_themes', parsed_data.get('themes', []))
                    insights = parsed_data.get('key_insights', [])
                    
                    base_state = states[0].copy()
                    new_state = {
                        **base_state,
                        'current': json.dumps(parsed_data),
                        'themes': themes,
                        'key_insights': insights,
                        'theme_frequencies': {
                            theme.get('theme', f'Theme {i+1}'): theme.get('total_frequency', theme.get('frequency', 0))
                            for i, theme in enumerate(themes)
                            if isinstance(theme, dict)
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
            except Exception as e:
                logger.error(f"Error parsing document merge aggregation: {e}")
                new_states.append({
                    'current': text,
                    'merged_document': text,
                    'themes': [],
                    'theme_frequencies': {}
                })
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated theme extraction or document merge responses."""
        new_states = []
        
        for text in texts:
            try:
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
                            theme.get('theme', f'Theme {i+1}'): theme.get('frequency', 0)
                            for i, theme in enumerate(themes)
                            if isinstance(theme, dict)
                        }
                    })
                else:
                    # This is document merge or plain text
                    new_state.update({
                        'current': text,
                        'merged_document': text
                    })
                
                new_states.append(new_state)
            except Exception as e:
                logger.error(f"Error parsing document merge generation: {e}")
                new_states.append({
                    **state,
                    'current': text,
                    'merged_document': text
                })
        
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
        return scores if scores else [5.0]


class ComplianceAnalysisParser(FinanceBaseParser):
    """Parser for compliance analysis workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated compliance analysis results."""
        new_states = []
        
        for text in texts:
            try:
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
            except Exception as e:
                logger.error(f"Error parsing compliance aggregation: {e}")
                new_states.append({
                    'current': '{"error": "Failed to parse compliance"}',
                    'conflicts': [],
                    'compliance_matrix': {},
                    'requirements': []
                })
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated compliance analysis responses."""
        new_states = []
        
        for text in texts:
            try:
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
            except Exception as e:
                logger.error(f"Error parsing compliance generation: {e}")
                new_states.append({
                    **state,
                    'current': '{"error": "Failed to parse compliance"}',
                    'requirements': [],
                    'conflicts': []
                })
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved compliance analysis."""
        if not texts:
            return state
            
        try:
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
        except Exception as e:
            logger.error(f"Error parsing compliance improvement: {e}")
            return state

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
        return scores if scores else [5.0]


class FinancialMetricsParser(FinanceBaseParser):
    """Parser for financial metrics workflow responses."""

    def parse_aggregation_answer(self, states: List[Dict], texts: List[str]) -> Union[Dict, List[Dict]]:
        """Parse aggregated financial metrics comparison results."""
        new_states = []
        
        for text in texts:
            try:
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
            except Exception as e:
                logger.error(f"Error parsing financial metrics aggregation: {e}")
                new_states.append({
                    'current': '{"error": "Failed to parse metrics"}',
                    'comparative_analysis': {},
                    'rankings': {},
                    'peer_analysis': []
                })
        
        return new_states

    def parse_generate_answer(self, state: Dict, texts: List[str]) -> List[Dict]:
        """Parse generated financial metrics responses."""
        new_states = []
        
        for text in texts:
            try:
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
            except Exception as e:
                logger.error(f"Error parsing financial metrics generation: {e}")
                new_states.append({
                    **state,
                    'current': '{"error": "Failed to parse metrics"}',
                    'company_metrics': {},
                    'metrics': []
                })
        
        return new_states

    def parse_improve_answer(self, state: Dict, texts: List[str]) -> Dict:
        """Parse improved financial metrics analysis."""
        if not texts:
            return state
            
        try:
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
        except Exception as e:
            logger.error(f"Error parsing financial metrics improvement: {e}")
            return state

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
        return scores if scores else [5.0]
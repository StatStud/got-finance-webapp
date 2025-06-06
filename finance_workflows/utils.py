"""
Utility functions for finance workflows.
"""

import json
import datetime
from typing import Dict, List, Any, Union


def format_currency(amount: float) -> str:
    """Format currency amount with proper formatting."""
    if amount == 0.0:
        return "$0.00"
    elif amount < 0.01:
        return f"${amount:.6f}"
    else:
        return f"${amount:.2f}"


def calculate_cost(prompt_tokens: int, completion_tokens: int, 
                  prompt_rate: float = 0.0, completion_rate: float = 0.0) -> float:
    """Calculate API cost based on token usage."""
    prompt_cost = (prompt_tokens / 1000.0) * prompt_rate
    completion_cost = (completion_tokens / 1000.0) * completion_rate
    return prompt_cost + completion_cost


def parse_financial_data(text: str) -> Dict[str, Any]:
    """Parse financial data from text input."""
    try:
        # Try to parse as JSON first
        return json.loads(text)
    except json.JSONDecodeError:
        # If not JSON, try to extract key-value pairs
        data = {}
        lines = text.strip().split('\n')
        
        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()
                
                # Try to convert to number
                try:
                    if '.' in value:
                        data[key] = float(value.replace(',', '').replace('$', '').replace('%', ''))
                    else:
                        data[key] = int(value.replace(',', '').replace('$', '').replace('%', ''))
                except ValueError:
                    data[key] = value
        
        return data


def extract_risk_factors(text: str) -> List[Dict[str, Any]]:
    """Extract risk factors from text using simple heuristics."""
    risk_keywords = [
        'risk', 'threat', 'challenge', 'uncertainty', 'volatile', 'exposure',
        'liable', 'vulnerable', 'dependent', 'competitive', 'regulatory',
        'compliance', 'cybersecurity', 'operational', 'financial', 'market'
    ]
    
    sentences = text.split('.')
    risk_factors = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if any(keyword in sentence.lower() for keyword in risk_keywords):
            # Simple severity estimation based on intensity words
            severity = 5  # Default medium severity
            
            high_intensity = ['severe', 'significant', 'major', 'critical', 'substantial']
            low_intensity = ['minor', 'limited', 'minimal', 'slight']
            
            if any(word in sentence.lower() for word in high_intensity):
                severity = 8
            elif any(word in sentence.lower() for word in low_intensity):
                severity = 3
            
            risk_factors.append({
                'factor': sentence[:50] + '...' if len(sentence) > 50 else sentence,
                'description': sentence,
                'severity': severity,
                'category': 'operational'  # Default category
            })
    
    return risk_factors


def calculate_financial_ratios(metrics: Dict[str, float]) -> Dict[str, float]:
    """Calculate financial ratios from basic metrics."""
    ratios = {}
    
    try:
        # Return on Equity (ROE)
        if 'net_income' in metrics and 'total_equity' in metrics and metrics['total_equity'] > 0:
            ratios['roe'] = metrics['net_income'] / metrics['total_equity']
        
        # Return on Assets (ROA)
        if 'net_income' in metrics and 'total_assets' in metrics and metrics['total_assets'] > 0:
            ratios['roa'] = metrics['net_income'] / metrics['total_assets']
        
        # Profit Margin
        if 'net_income' in metrics and 'revenue' in metrics and metrics['revenue'] > 0:
            ratios['profit_margin'] = metrics['net_income'] / metrics['revenue']
        
        # Debt to Equity
        if 'total_debt' in metrics and 'total_equity' in metrics and metrics['total_equity'] > 0:
            ratios['debt_to_equity'] = metrics['total_debt'] / metrics['total_equity']
        elif 'total_assets' in metrics and 'total_equity' in metrics and metrics['total_equity'] > 0:
            # Approximate debt as assets - equity
            debt = metrics['total_assets'] - metrics['total_equity']
            ratios['debt_to_equity'] = debt / metrics['total_equity']
        
        # Current Ratio
        if 'current_assets' in metrics and 'current_liabilities' in metrics and metrics['current_liabilities'] > 0:
            ratios['current_ratio'] = metrics['current_assets'] / metrics['current_liabilities']
        
        # Quick Ratio (assume current assets for simplicity)
        if 'current_assets' in metrics and 'current_liabilities' in metrics and metrics['current_liabilities'] > 0:
            ratios['quick_ratio'] = metrics['current_assets'] / metrics['current_liabilities']
    
    except (KeyError, ZeroDivisionError, TypeError):
        pass
    
    return ratios


def validate_json_structure(data: Union[str, Dict], required_fields: List[str]) -> bool:
    """Validate that JSON data contains required fields."""
    try:
        if isinstance(data, str):
            data = json.loads(data)
        
        if not isinstance(data, dict):
            return False
        
        return all(field in data for field in required_fields)
    except (json.JSONDecodeError, TypeError):
        return False


def merge_risk_analyses(analyses: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Merge multiple risk analyses into a consolidated view."""
    consolidated_risks = {}
    
    for analysis in analyses:
        risk_factors = analysis.get('risk_factors', [])
        
        for risk in risk_factors:
            if not isinstance(risk, dict) or 'factor' not in risk:
                continue
                
            factor_name = risk['factor']
            
            if factor_name in consolidated_risks:
                # Update existing risk
                existing = consolidated_risks[factor_name]
                existing['frequency'] = existing.get('frequency', 1) + 1
                existing['severity'] = (existing['severity'] + risk.get('severity', 5)) / 2
                existing['sources'].append(analysis.get('source', 'unknown'))
            else:
                # Add new risk
                consolidated_risks[factor_name] = {
                    'factor': factor_name,
                    'description': risk.get('description', ''),
                    'severity': risk.get('severity', 5),
                    'category': risk.get('category', 'other'),
                    'frequency': 1,
                    'sources': [analysis.get('source', 'unknown')]
                }
    
    # Convert to list and sort by severity
    consolidated_list = list(consolidated_risks.values())
    consolidated_list.sort(key=lambda x: x['severity'], reverse=True)
    
    # Create ranking
    risk_ranking = [risk['factor'] for risk in consolidated_list]
    
    return {
        'consolidated_risks': consolidated_list,
        'risk_ranking': risk_ranking,
        'total_risks': len(consolidated_list),
        'avg_severity': sum(r['severity'] for r in consolidated_list) / len(consolidated_list) if consolidated_list else 0
    }


def extract_themes_from_text(text: str) -> List[Dict[str, Any]]:
    """Extract themes from text using keyword analysis."""
    # Common financial themes
    theme_keywords = {
        'earnings': ['earnings', 'revenue', 'profit', 'income', 'sales'],
        'growth': ['growth', 'expansion', 'increase', 'rising', 'improving'],
        'risks': ['risk', 'challenge', 'concern', 'threat', 'volatility'],
        'strategy': ['strategy', 'plan', 'initiative', 'transformation', 'direction'],
        'market': ['market', 'industry', 'competition', 'demand', 'customer'],
        'financial_health': ['margin', 'cash', 'debt', 'liquidity', 'capital'],
        'operations': ['operations', 'efficiency', 'productivity', 'supply', 'manufacturing'],
        'regulation': ['regulatory', 'compliance', 'legal', 'policy', 'government']
    }
    
    themes = []
    text_lower = text.lower()
    
    for theme_name, keywords in theme_keywords.items():
        frequency = sum(text_lower.count(keyword) for keyword in keywords)
        
        if frequency > 0:
            # Extract sample quotes
            quotes = []
            sentences = text.split('.')
            for sentence in sentences[:10]:  # Limit to first 10 sentences
                if any(keyword in sentence.lower() for keyword in keywords):
                    quotes.append(sentence.strip())
                    if len(quotes) >= 2:  # Limit quotes
                        break
            
            relevance_score = min(frequency * 2, 10)  # Simple relevance calculation
            
            themes.append({
                'theme': theme_name.replace('_', ' ').title(),
                'frequency': frequency,
                'relevance_score': relevance_score,
                'key_quotes': quotes,
                'category': theme_name
            })
    
    # Sort by relevance
    themes.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    return themes


def create_execution_summary(session_id: str, workflow_type: str, 
                           execution_time: float, cost: float, 
                           thought_count: int, success: bool) -> Dict[str, Any]:
    """Create execution summary for logging."""
    return {
        'session_id': session_id,
        'workflow_type': workflow_type,
        'timestamp': datetime.datetime.now().isoformat(),
        'execution_time_seconds': execution_time,
        'cost_usd': cost,
        'thought_count': thought_count,
        'success': success,
        'cost_per_thought': cost / thought_count if thought_count > 0 else 0,
        'thoughts_per_second': thought_count / execution_time if execution_time > 0 else 0
    }


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage."""
    import re
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
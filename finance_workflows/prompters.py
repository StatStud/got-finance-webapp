"""
Finance-specific prompters for Graph of Thoughts workflows.
These inherit from the GoT Prompter base class and provide specialized prompts
for financial analysis tasks.
"""

from typing import Dict, List
from graph_of_thoughts.prompter.prompter import Prompter


class RiskAnalysisPrompter(Prompter):
    """
    Prompter for risk analysis workflows.
    Generates prompts for extracting, scoring, and ranking risk factors.
    """

    risk_extraction_prompt = """<Instruction> Analyze the following financial document and extract all risk factors mentioned. 
For each risk factor, provide a brief description and assign a severity score from 1-10 (10 being most severe).
Output the results in JSON format with the structure:
{
    "risk_factors": [
        {
            "factor": "Risk factor name",
            "description": "Brief description", 
            "severity": 8,
            "category": "operational/financial/market/regulatory/other"
        }
    ]
}
</Instruction>

<Examples>
Example 1:
Document: "Our company faces significant cybersecurity threats that could impact operations. Additionally, we are subject to changing regulations in multiple jurisdictions."
Output:
{
    "risk_factors": [
        {
            "factor": "Cybersecurity threats",
            "description": "Risk of cyber attacks impacting operations",
            "severity": 8,
            "category": "operational"
        },
        {
            "factor": "Regulatory changes",
            "description": "Exposure to changing regulations across jurisdictions",
            "severity": 6,
            "category": "regulatory"
        }
    ]
}
</Examples>

Document: {document}
Output:"""

    risk_aggregation_prompt = """<Instruction> Combine the following risk factor analyses from multiple documents into a consolidated risk assessment.
Merge similar risk factors, calculate average severity scores, and rank all risks by their overall severity.
Output in JSON format:
{
    "consolidated_risks": [
        {
            "factor": "Combined risk factor name",
            "description": "Consolidated description",
            "severity": 7.5,
            "category": "category",
            "frequency": 3,
            "sources": ["doc1", "doc2", "doc3"]
        }
    ],
    "risk_ranking": ["risk1", "risk2", "risk3"]
}
</Instruction>

Risk Analyses to Combine:
{risk_analyses}

Consolidated Output:"""

    risk_scoring_prompt = """<Instruction> Score the quality of this risk analysis on a scale of 1-10 based on:
1. Completeness of risk identification
2. Accuracy of severity scoring
3. Proper categorization
4. Overall coherence

Provide only a numeric score.
</Instruction>

Risk Analysis: {risk_analysis}
Score:"""

    def aggregation_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate aggregation prompt for combining risk analyses."""
        risk_analyses = []
        for i, state in enumerate(state_dicts):
            risk_data = state.get('current', '{}')
            risk_analyses.append(f"Analysis {i+1}: {risk_data}")
        
        return self.risk_aggregation_prompt.format(
            risk_analyses="\n\n".join(risk_analyses)
        )

    def generate_prompt(self, num_branches: int, **kwargs) -> str:
        """Generate prompt for risk factor extraction."""
        document = kwargs.get('document', kwargs.get('current', ''))
        documents = kwargs.get('documents', [])
        method = kwargs.get('method', 'got_risk')
        
        if method.startswith('got') and 'current' in kwargs and kwargs['current']:
            # This is an aggregation step
            return self.risk_aggregation_prompt.format(
                risk_analyses=kwargs['current']
            )
        elif documents and len(documents) > 0:
            # Use first document for single extraction
            return self.risk_extraction_prompt.format(document=documents[0])
        else:
            return self.risk_extraction_prompt.format(document=document)

    def improve_prompt(self, **kwargs) -> str:
        """Generate improvement prompt for risk analysis."""
        current_analysis = kwargs.get('current', '')
        return f"""<Instruction> Improve the following risk analysis by:
1. Adding any missing risk factors
2. Refining severity scores
3. Improving risk descriptions
4. Ensuring proper categorization

Current Analysis: {current_analysis}

Improved Analysis:"""

    def validation_prompt(self, **kwargs) -> str:
        """Generate validation prompt for risk analysis."""
        return "Validate that this risk analysis follows the required JSON format and includes severity scores."

    def score_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate scoring prompt for risk analysis quality."""
        if len(state_dicts) == 1:
            return self.risk_scoring_prompt.format(
                risk_analysis=state_dicts[0].get('current', '')
            )
        return "Score the overall quality of these combined risk analyses on a scale of 1-10."


class DocumentMergePrompter(Prompter):
    """
    Prompter for document merging workflows.
    Generates prompts for extracting themes, merging documents, and identifying patterns.
    """

    theme_extraction_prompt = """<Instruction> Analyze the following financial document and extract key themes and topics.
For each theme, identify the frequency of mentions and provide relevant quotes.
Output in JSON format:
{
    "themes": [
        {
            "theme": "Theme name",
            "frequency": 5,
            "relevance_score": 8,
            "key_quotes": ["quote1", "quote2"],
            "category": "earnings/guidance/risks/strategy/other"
        }
    ]
}
</Instruction>

<Examples>
Example:
Document: "Our Q3 earnings exceeded expectations due to strong digital transformation initiatives. However, supply chain challenges continue to impact margins. We remain optimistic about our AI strategy."
Output:
{
    "themes": [
        {
            "theme": "Digital transformation",
            "frequency": 1,
            "relevance_score": 9,
            "key_quotes": ["strong digital transformation initiatives"],
            "category": "strategy"
        },
        {
            "theme": "Supply chain challenges", 
            "frequency": 1,
            "relevance_score": 7,
            "key_quotes": ["supply chain challenges continue to impact margins"],
            "category": "risks"
        }
    ]
}
</Examples>

Document: {document}
Output:"""

    document_merge_prompt = """<Instruction> Merge the following financial documents into a coherent summary that:
1. Combines similar themes and topics
2. Maintains chronological context where relevant
3. Highlights recurring patterns and trends
4. Eliminates redundancy while preserving key information

Output a well-structured summary document.
</Instruction>

Documents to merge:
{documents}

Merged summary:"""

    theme_aggregation_prompt = """<Instruction> Combine theme analyses from multiple documents to identify:
1. Most frequently mentioned themes across all documents
2. Trending topics over time
3. Consistent vs. changing narratives
4. Overall thematic patterns

Output in JSON format:
{
    "aggregated_themes": [
        {
            "theme": "Combined theme name",
            "total_frequency": 15,
            "avg_relevance": 8.2,
            "trend": "increasing/stable/decreasing",
            "documents_mentioned": 4
        }
    ],
    "key_insights": ["insight1", "insight2"]
}
</Instruction>

Theme Analyses:
{theme_analyses}

Aggregated Output:"""

    def aggregation_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate aggregation prompt for combining document themes."""
        if len(state_dicts[0].get('parts', [])) > 0:
            # Aggregating themes
            theme_analyses = []
            for i, state in enumerate(state_dicts):
                themes = state.get('current', '{}')
                theme_analyses.append(f"Document {i+1} themes: {themes}")
            
            return self.theme_aggregation_prompt.format(
                theme_analyses="\n\n".join(theme_analyses)
            )
        else:
            # Merging full documents
            documents = []
            for i, state in enumerate(state_dicts):
                doc_content = state.get('current', '')
                documents.append(f"Document {i+1}:\n{doc_content}")
            
            return self.document_merge_prompt.format(
                documents="\n\n".join(documents)
            )

    def generate_prompt(self, num_branches: int, **kwargs) -> str:
        """Generate prompt for theme extraction or document processing."""
        documents = kwargs.get('documents', [])
        parts = kwargs.get('parts', set())
        current = kwargs.get('current', '')
        method = kwargs.get('method', 'got_merge')
        
        if current and method.startswith('got'):
            # Processing existing content
            return self.theme_extraction_prompt.format(document=current)
        elif parts and len(parts) > 0:
            # Processing specific document parts
            doc_parts = [documents[i] for i in sorted(parts)]
            return self.theme_extraction_prompt.format(document=doc_parts[0])
        elif documents:
            # Processing first document
            return self.theme_extraction_prompt.format(document=documents[0])
        else:
            return self.theme_extraction_prompt.format(document="No document provided")

    def improve_prompt(self, **kwargs) -> str:
        """Generate improvement prompt for document merge."""
        current = kwargs.get('current', '')
        return f"""<Instruction> Improve this merged document by:
1. Enhancing coherence and flow
2. Adding more detailed thematic analysis
3. Strengthening the narrative structure
4. Ensuring all key themes are properly integrated

Current merged document: {current}

Improved version:"""

    def validation_prompt(self, **kwargs) -> str:
        """Generate validation prompt."""
        return "Validate that this document merge properly combines themes and maintains coherent structure."

    def score_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate scoring prompt for document merge quality."""
        return "Score this document merge on coherence, theme integration, and information retention (1-10)."


class ComplianceAnalysisPrompter(Prompter):
    """
    Prompter for regulatory compliance analysis workflows.
    """

    requirement_extraction_prompt = """<Instruction> Extract regulatory requirements from the following text.
For each requirement, identify:
1. The specific obligation or rule
2. Applicable entities/institutions
3. Implementation timeline
4. Penalties for non-compliance

Output in JSON format:
{
    "requirements": [
        {
            "requirement_id": "REQ_001",
            "description": "Detailed requirement description",
            "applicable_to": ["banks", "investment_firms"],
            "deadline": "2024-12-31",
            "penalty": "Fine up to 10% of annual revenue",
            "jurisdiction": "EU/US/UK/etc"
        }
    ]
}
</Instruction>

Regulatory Text: {regulatory_text}
Output:"""

    conflict_analysis_prompt = """<Instruction> Analyze the following regulatory requirements from different jurisdictions to identify:
1. Conflicting requirements
2. Overlapping obligations  
3. Implementation challenges
4. Compliance gaps

Output conflicts and recommendations in JSON format:
{
    "conflicts": [
        {
            "conflict_id": "CONF_001",
            "jurisdictions": ["EU", "US"],
            "description": "Conflicting capital requirements",
            "severity": "high/medium/low",
            "recommendation": "Suggested resolution approach"
        }
    ],
    "compliance_matrix": {
        "requirement_coverage": "90%",
        "jurisdictions_analyzed": 3,
        "total_conflicts": 2
    }
}
</Instruction>

Requirements to analyze:
{requirements}

Analysis:"""

    def aggregation_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate aggregation prompt for compliance analysis."""
        requirements = []
        for i, state in enumerate(state_dicts):
            req_data = state.get('current', '{}')
            requirements.append(f"Jurisdiction {i+1}: {req_data}")
        
        return self.conflict_analysis_prompt.format(
            requirements="\n\n".join(requirements)
        )

    def generate_prompt(self, num_branches: int, **kwargs) -> str:
        """Generate prompt for requirement extraction."""
        regulatory_texts = kwargs.get('regulatory_texts', [])
        current = kwargs.get('current', '')
        
        if current:
            return self.conflict_analysis_prompt.format(requirements=current)
        elif regulatory_texts:
            return self.requirement_extraction_prompt.format(
                regulatory_text=regulatory_texts[0]
            )
        else:
            return self.requirement_extraction_prompt.format(
                regulatory_text="No regulatory text provided"
            )

    def improve_prompt(self, **kwargs) -> str:
        """Generate improvement prompt."""
        current = kwargs.get('current', '')
        return f"""<Instruction> Improve this compliance analysis by:
1. Adding more detailed conflict descriptions
2. Providing clearer implementation guidance
3. Enhancing severity assessments
4. Adding practical compliance recommendations

Current analysis: {current}

Improved analysis:"""

    def validation_prompt(self, **kwargs) -> str:
        """Generate validation prompt."""
        return "Validate that this compliance analysis includes all required fields and proper JSON format."

    def score_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate scoring prompt."""
        return "Score this compliance analysis on completeness, accuracy, and practical value (1-10)."


class FinancialMetricsPrompter(Prompter):
    """
    Prompter for financial metrics comparison workflows.
    """

    metrics_extraction_prompt = """<Instruction> Extract key financial metrics from the following company data.
Calculate ratios and provide comparative analysis context.
Output in JSON format:
{
    "company_metrics": {
        "company_name": "Company Name",
        "revenue": 1000000000,
        "net_income": 100000000,
        "total_assets": 5000000000,
        "total_equity": 2000000000,
        "debt_to_equity": 1.5,
        "roe": 0.05,
        "roa": 0.02,
        "profit_margin": 0.10,
        "current_ratio": 1.2,
        "quick_ratio": 0.8,
        "custom_metrics": {}
    }
}
</Instruction>

<Examples>
Example:
Financial Data: "ABC Corp - Revenue: $500M, Net Income: $50M, Total Assets: $2B, Equity: $800M, Current Assets: $600M, Current Liabilities: $500M"
Output:
{
    "company_metrics": {
        "company_name": "ABC Corp",
        "revenue": 500000000,
        "net_income": 50000000,
        "total_assets": 2000000000,
        "total_equity": 800000000,
        "debt_to_equity": 1.5,
        "roe": 0.0625,
        "roa": 0.025,
        "profit_margin": 0.10,
        "current_ratio": 1.2,
        "quick_ratio": 1.2
    }
}
</Examples>

Financial Data: {financial_data}
Output:"""

    comparative_analysis_prompt = """<Instruction> Compare the financial metrics across multiple companies and provide:
1. Ranking by key performance indicators
2. Peer analysis and benchmarking
3. Investment attractiveness scores
4. Risk assessment based on financial ratios

Output comprehensive comparison in JSON format:
{
    "comparative_analysis": {
        "rankings": {
            "by_roe": ["Company1", "Company2", "Company3"],
            "by_revenue_growth": ["Company1", "Company2", "Company3"],
            "by_debt_ratio": ["Company1", "Company2", "Company3"]
        },
        "peer_analysis": [
            {
                "company": "Company1",
                "investment_score": 8.5,
                "risk_score": 3.2,
                "strengths": ["High ROE", "Low debt"],
                "weaknesses": ["Low liquidity"]
            }
        ],
        "market_benchmarks": {
            "industry_avg_roe": 0.12,
            "industry_avg_debt_ratio": 0.6
        }
    }
}
</Instruction>

Company Metrics to Compare:
{company_metrics}

Comparative Analysis:"""

    def aggregation_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate aggregation prompt for metrics comparison."""
        company_metrics = []
        for state in state_dicts:
            metrics = state.get('current', '{}')
            company_metrics.append(metrics)
        
        return self.comparative_analysis_prompt.format(
            company_metrics="\n\n".join(company_metrics)
        )

    def generate_prompt(self, num_branches: int, **kwargs) -> str:
        """Generate prompt for metrics extraction."""
        financial_data = kwargs.get('financial_data', [])
        current = kwargs.get('current', '')
        
        if current:
            return self.comparative_analysis_prompt.format(company_metrics=current)
        elif financial_data:
            return self.metrics_extraction_prompt.format(
                financial_data=financial_data[0]
            )
        else:
            return self.metrics_extraction_prompt.format(
                financial_data="No financial data provided"
            )

    def improve_prompt(self, **kwargs) -> str:
        """Generate improvement prompt."""
        current = kwargs.get('current', '')
        return f"""<Instruction> Improve this financial metrics analysis by:
1. Adding more comprehensive ratio calculations
2. Enhancing peer comparison insights
3. Providing clearer investment recommendations
4. Including industry benchmark comparisons

Current analysis: {current}

Improved analysis:"""

    def validation_prompt(self, **kwargs) -> str:
        """Generate validation prompt."""
        return "Validate that financial metrics are properly calculated and formatted in JSON."

    def score_prompt(self, state_dicts: List[Dict], **kwargs) -> str:
        """Generate scoring prompt."""
        return "Score this financial metrics analysis on accuracy, completeness, and analytical value (1-10)."
"""
Cerebras Language Model implementation for Graph of Thoughts.
Adapts the Cerebras API to work with the GoT framework.
"""

import os
import logging
from typing import List, Dict, Union, Any
from cerebras.cloud.sdk import Cerebras

# Import GoT base class
#from graph_of_thoughts.language_models.abstract_language_model import AbstractLanguageModel
from .local_got import AbstractLanguageModel

class CerebrasLLM(AbstractLanguageModel):
    """
    Cerebras language model implementation for Graph of Thoughts framework.
    
    Inherits from AbstractLanguageModel and implements the required methods
    to integrate Cerebras API with GoT operations.
    """

    def __init__(
        self, 
        config_path: str = "config.json", 
        model_name: str = "cerebras", 
        cache: bool = False
    ) -> None:
        """
        Initialize the Cerebras language model.

        :param config_path: Path to the configuration file. Defaults to "config.json".
        :type config_path: str
        :param model_name: Name of the model configuration. Defaults to "cerebras".
        :type model_name: str
        :param cache: Flag to determine whether to cache responses. Defaults to False.
        :type cache: bool
        """
        super().__init__(config_path, model_name, cache)
        
        # Get configuration for the specified model
        self.config: Dict = self.config[model_name] if self.config else {}
        
        # Model configuration
        self.model_id: str = self.config.get("model_id", "llama-3.3-70b")
        self.temperature: float = self.config.get("temperature", 1.0)
        self.max_tokens: int = self.config.get("max_tokens", 4096)
        self.stop: Union[str, List[str]] = self.config.get("stop", None)
        
        # Cost tracking (Cerebras is currently free, so set to 0)
        self.prompt_token_cost: float = self.config.get("prompt_token_cost", 0.0)
        self.response_token_cost: float = self.config.get("response_token_cost", 0.0)
        
        # Get API key from environment or config
        self.api_key: str = os.getenv("CEREBRAS_API_KEY", self.config.get("api_key", ""))
        if not self.api_key:
            raise ValueError("CEREBRAS_API_KEY not found in environment variables or config")
        
        # Initialize Cerebras client
        self.client = Cerebras(api_key=self.api_key)
        
        self.logger.info(f"Initialized Cerebras LLM with model: {self.model_id}")

    def query(self, query: str, num_responses: int = 1) -> List[Dict[str, Any]]:
        """
        Query the Cerebras model for responses.

        :param query: The query to be posed to the language model.
        :type query: str
        :param num_responses: Number of desired responses, default is 1.
        :type num_responses: int
        :return: Response(s) from the Cerebras model.
        :rtype: List[Dict[str, Any]]
        """
        if self.cache and query in self.response_cache:
            self.logger.debug("Returning cached response")
            return self.response_cache[query]

        responses = []
        
        try:
            # Generate multiple responses if requested
            for _ in range(num_responses):
                chat_completion = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": query}],
                    model=self.model_id,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stop=self.stop
                )
                
                # Extract response
                response_text = chat_completion.choices[0].message.content.strip()
                
                # Create response dictionary compatible with GoT
                response_dict = {
                    "content": response_text,
                    "role": "assistant",
                    "model": self.model_id,
                    "finish_reason": chat_completion.choices[0].finish_reason
                }
                
                responses.append(response_dict)
                
                # Update token counts (if available from Cerebras)
                if hasattr(chat_completion, 'usage') and chat_completion.usage:
                    self.prompt_tokens += getattr(chat_completion.usage, 'prompt_tokens', 0)
                    self.completion_tokens += getattr(chat_completion.usage, 'completion_tokens', 0)
                else:
                    # Estimate tokens if usage not available
                    estimated_prompt_tokens = len(query.split()) * 1.3  # Rough estimation
                    estimated_completion_tokens = len(response_text.split()) * 1.3
                    self.prompt_tokens += int(estimated_prompt_tokens)
                    self.completion_tokens += int(estimated_completion_tokens)
            
            # Calculate cost (currently 0 for Cerebras)
            prompt_tokens_k = float(self.prompt_tokens) / 1000.0
            completion_tokens_k = float(self.completion_tokens) / 1000.0
            self.cost = (
                self.prompt_token_cost * prompt_tokens_k + 
                self.response_token_cost * completion_tokens_k
            )
            
            self.logger.info(
                f"Generated {num_responses} responses. "
                f"Prompt tokens: {self.prompt_tokens}, "
                f"Completion tokens: {self.completion_tokens}, "
                f"Cost: ${self.cost:.4f}"
            )
            
            # Cache if enabled
            if self.cache:
                self.response_cache[query] = responses
                
            return responses
            
        except Exception as e:
            self.logger.error(f"Error querying Cerebras API: {str(e)}")
            # Return empty response to prevent GoT execution failure
            return [{"content": "", "role": "assistant", "model": self.model_id, "error": str(e)}]

    def get_response_texts(self, query_response: Union[List[Dict], Dict]) -> List[str]:
        """
        Extract the response texts from the query response.

        :param query_response: The response dictionary (or list of dictionaries) from the Cerebras model.
        :type query_response: Union[List[Dict], Dict]
        :return: List of response strings.
        :rtype: List[str]
        """
        if not isinstance(query_response, list):
            query_response = [query_response]
        
        response_texts = []
        for response in query_response:
            if isinstance(response, dict):
                # Extract content from response
                content = response.get("content", "")
                if content:
                    response_texts.append(content)
                elif "error" in response:
                    self.logger.warning(f"Response contained error: {response['error']}")
                    response_texts.append("")  # Add empty string to maintain list length
                else:
                    self.logger.warning("Response missing content field")
                    response_texts.append("")
            else:
                self.logger.warning(f"Unexpected response format: {type(response)}")
                response_texts.append(str(response))
        
        return response_texts

    def create_config_file(self, config_path: str = "config.json") -> None:
        """
        Create a default configuration file for Cerebras LLM.
        
        :param config_path: Path where to save the config file.
        :type config_path: str
        """
        default_config = {
            "cerebras": {
                "model_id": "llama-3.3-70b",
                "prompt_token_cost": 0.0,  # Cerebras is currently free
                "response_token_cost": 0.0,
                "temperature": 1.0,
                "max_tokens": 4096,
                "stop": None,
                "organization": "",
                "api_key": ""  # Should be set via environment variable
            }
        }
        
        import json
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        self.logger.info(f"Created default config file at {config_path}")

    def estimate_cost(self, query: str, num_responses: int = 1) -> float:
        """
        Estimate the cost of a query before execution.
        
        :param query: The query string
        :type query: str
        :param num_responses: Number of responses
        :type num_responses: int
        :return: Estimated cost in dollars
        :rtype: float
        """
        # Rough token estimation
        estimated_prompt_tokens = len(query.split()) * 1.3
        estimated_completion_tokens = estimated_prompt_tokens * 0.5  # Assume response is half the prompt length
        
        estimated_cost = (
            (estimated_prompt_tokens / 1000.0) * self.prompt_token_cost +
            (estimated_completion_tokens / 1000.0) * self.response_token_cost
        ) * num_responses
        
        return estimated_cost

    def reset_counters(self) -> None:
        """Reset token and cost counters."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = 0.0
        self.logger.info("Reset token and cost counters")

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get current usage statistics.
        
        :return: Dictionary with usage stats
        :rtype: Dict[str, Any]
        """
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
            "cost": self.cost,
            "model": self.model_id,
            "cached_queries": len(self.response_cache) if self.cache else 0
        }
# Mistral LLM Client using official mistralai library
import json
import os
from typing import Any, Optional

from pyrate_limiter import Limiter, Rate, Duration
from mistralai.client import Mistral
from mistralai.client.models.usermessage import UserMessage

from language_learner.core.llm_interface import LLMClient
from language_learner.exceptions import LLMError


class MistralLLMClient(LLMClient):
    """Mistral LLM client implementing generic LLM interface"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        rate_limit: Optional[float] = None,
    ) -> None:
        """Initialize Mistral LLM client.

        Args:
            api_key: Mistral API key, defaults to MISTRAL_API_KEY environment variable
            model: Model name to use
            rate_limit: Maximum API calls per second

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.model = model
        self.rate_limit = rate_limit
        
        # Initialize rate limiter using pyrate_limiter
        if self.rate_limit > 0:
            # Convert rate_limit (calls/second) to duration per call
            # For fractional rates like 0.8, we use Rate with fractional duration
            # e.g., 0.8 calls/sec = 1 call per 1.25 seconds
            seconds_per_call = 1.0 / self.rate_limit
            self.limiter = Limiter(Rate(1, Duration.SECOND * seconds_per_call))
        else:
            self.limiter = None

        if not self.api_key:
            raise ValueError("Mistral API key not provided")

        self.client = Mistral(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Generate text using Mistral LLM.

        Args:
            prompt: Input prompt for text generation
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate
            response_schema: Optional JSON schema for structured output.
                           If provided, the Mistral API will return a JSON response.

        Returns:
            Generated text (JSON string if response_schema was provided)

        Raises:
            LLMError: If there's an error generating text
        """
        try:
            # Apply rate limiting using pyrate_limiter
            if self.limiter:
                self.limiter.try_acquire()
            
            # Build request parameters
            request_params = {
                "model": self.model,
                "messages": [UserMessage(content=prompt)],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            
            # If response_schema is provided, use response_format
            if response_schema is not None:
                # Mistral structured output expects the schema nested under a
                # "json_schema" object with a name, not a bare "schema" field.
                # See https://docs.mistral.ai/capabilities/structured-output/
                request_params["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": response_schema.get("title", "response"),
                        "schema": response_schema,
                        "strict": True,
                    },
                }
            
            chat_response = self.client.chat.complete(**request_params)

            if chat_response.choices and len(chat_response.choices) > 0:
                return chat_response.choices[0].message.content.strip()

            raise LLMError("No response from API")
        except Exception as e:
            raise LLMError(f"Failed to generate text: {e}") from e

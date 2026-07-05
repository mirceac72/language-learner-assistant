# Generic LLM Client Interface
from typing import Any, Protocol


class LLMClient(Protocol):
    """Generic interface for LLM clients"""

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        """Generate text from a prompt.
        
        Args:
            prompt: Input prompt for text generation
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum number of tokens to generate
            response_schema: Optional JSON schema for structured output.
                           If provided and the API supports it, the response will be formatted as JSON.
        
        Returns:
            Generated text
        """
        ...

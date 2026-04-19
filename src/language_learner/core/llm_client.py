# Mistral LLM Client using official mistralai library
import os

from mistralai.client import Mistral
from mistralai.client.models.usermessage import UserMessage

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.exceptions import LLMError


class MistralLLMClient(LLMClient):
    """Mistral LLM client implementing generic LLM interface"""

    def __init__(
        self, api_key: str | None = None, model: str = "mistral-small"
    ) -> None:
        """Initialize Mistral LLM client.

        Args:
            api_key: Mistral API key, defaults to MISTRAL_API_KEY environment variable
            model: Model name to use

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.model = model

        if not self.api_key:
            raise ValueError("Mistral API key not provided")

        self.client = Mistral(api_key=self.api_key)

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 150
    ) -> str:
        """Generate text using Mistral LLM.

        Args:
            prompt: Input prompt for text generation
            temperature: Sampling temperature
            max_tokens: Maximum number of tokens to generate

        Returns:
            Generated text

        Raises:
            LLMError: If there's an error generating text
        """
        try:
            chat_response = self.client.chat.complete(
                model=self.model,
                messages=[UserMessage(content=prompt)],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if chat_response.choices and len(chat_response.choices) > 0:
                return chat_response.choices[0].message.content.strip()

            raise LLMError("No response from API")
        except Exception as e:
            raise LLMError(f"Failed to generate text: {e}") from e

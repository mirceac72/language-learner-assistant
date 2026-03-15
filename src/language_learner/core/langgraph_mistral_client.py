# LangGraph Mistral LLM Client
import os

from langchain_core.messages import HumanMessage
from langchain_mistralai import ChatMistralAI

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.exceptions import LLMError


class LangGraphMistralClient(LLMClient):
    """LangGraph Mistral LLM client implementing generic LLM interface"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "mistral-small-latest",
        temperature: float = 0.7,
    ) -> None:
        """Initialize LangGraph Mistral LLM client.

        Args:
            api_key: Mistral API key, defaults to MISTRAL_API_KEY environment variable
            model: Model name to use
            temperature: Default temperature for generation

        Raises:
            ValueError: If API key is not provided
        """
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        self.model = model
        self.temperature = temperature

        if not self.api_key:
            raise ValueError("Mistral API key not provided")

        # Initialize LangChain Mistral client
        self.client = ChatMistralAI(
            model=self.model,
            api_key=self.api_key,
            temperature=self.temperature,
        )

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 150
    ) -> str:
        """Generate text using LangGraph Mistral LLM.

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
            # Create human message from prompt
            message = HumanMessage(content=prompt)

            # Generate response using LangChain client
            response = self.client.invoke([message])

            if response and response.content:
                return response.content.strip()

            raise LLMError("No response from API")
        except Exception as e:
            raise LLMError(f"Failed to generate text: {e}") from e

# Generic LLM Client Interface
from typing import Protocol


class LLMClient(Protocol):
    """Generic interface for LLM clients"""

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 150
    ) -> str:
        """Generate text from a prompt"""
        ...

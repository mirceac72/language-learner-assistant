# Mock LLM Client for testing

from src.language_learner.core.llm_interface import LLMClient


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API calls"""

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.call_count = 0

    def generate(
        self, prompt: str, temperature: float = 0.7, max_tokens: int = 150
    ) -> str:
        """Generate mock response"""
        self.call_count += 1

        # Check for quality assessment first (more specific check)
        if "quality" in prompt and "Assess" in prompt and "Exercise Type:" in prompt:
            # Mock quality assessment response
            return "85|Good exercise with clear question and appropriate challenge|Could add more context about word usage"

        # Simple mock responses based on prompt content
        elif "fill-in-the-blank" in prompt:
            return "Le chat est sur le ___.|canapé|The cat is on the sofa."
        elif "multiple choice" in prompt:
            return "What does 'pomme' mean?|apple|fruit|red|tree"
        elif "translation" in prompt:
            return "J'aime les pommes.|I like apples."

        return "Mock response for testing"

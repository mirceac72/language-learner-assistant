# Mock LLM Client for testing

from language_learner.core.llm_interface import LLMClient
from language_learner.dialogs.dialog_prompts import (
    TOPIC_CREATOR_MARKER,
    TOPIC_REVIEWER_MARKER,
    TURN_CREATOR_MARKER,
    TURN_REVIEWER_MARKER,
)

# Valid JSON answers for the four dialog practice prompts. The markers are
# the constants from dialogs/dialog_prompts.py, so the mock cannot drift
# from the real prompt wording.
MOCK_TOPIC_JSON = (
    '{"topic": "Tu passes l\'été chez ta grand-mère à la campagne. '
    "Il fait très chaud et il n'a pas plu depuis des semaines.\"}"
)
MOCK_TURN_CREATOR_JSON = (
    '{"reply": "Il fait chaud aujourd\'hui. Est-ce qu\'il y a une canicule chez toi ?", '
    '"corrections": [], "target_words_used": []}'
)
MOCK_REVIEW_VERDICT_JSON = '{"approved": true, "score": 85, "feedback": "Fine."}'


class MockLLMClient(LLMClient):
    """Mock LLM client for testing without API calls.

    ``responses`` maps a prompt substring to the exact response to return;
    it is checked first, so tests can override any built-in response, e.g.
    force a reviewer rejection.
    """

    def __init__(self, responses: dict | None = None):
        self.responses = responses or {}
        self.call_count = 0

    def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 150,
        response_schema: dict | None = None,
    ) -> str:
        """Generate mock response"""
        self.call_count += 1

        # Scripted overrides first: a key that is a substring of the prompt
        # forces the exact response.
        for key, response in self.responses.items():
            if key in prompt:
                return response

        # Dialog practice prompts
        if TURN_CREATOR_MARKER in prompt:
            return MOCK_TURN_CREATOR_JSON
        if TURN_REVIEWER_MARKER in prompt:
            return MOCK_REVIEW_VERDICT_JSON
        if TOPIC_CREATOR_MARKER in prompt:
            return MOCK_TOPIC_JSON
        if TOPIC_REVIEWER_MARKER in prompt:
            return MOCK_REVIEW_VERDICT_JSON

        # Check for quality assessment first (more specific check)
        if "quality" in prompt and "Assess" in prompt and "Exercise Type:" in prompt:
            # Mock quality assessment response
            return "85|Good exercise with clear question and appropriate challenge|Could add more context about word usage"

        # Check for translation accuracy review
        if "Verify if the following English text is an accurate translation" in prompt:
            return '{"score": 100, "feedback": "Perfect translation"}'

        # Check for translation exercise evaluation
        if "Evaluate this translation exercise" in prompt:
            return '{"score": 85, "feedback": "Good translation, minor differences are acceptable."}'

        # Simple mock responses based on prompt content
        elif "fill-in-the-blank" in prompt:
            return "Le chat est sur le ___.|canapé|The cat is on the sofa."
        elif "multiple choice" in prompt:
            return "What does 'pomme' mean?|apple|fruit|red|tree"
        elif (
            "Create a natural French sentence" in prompt
            or "Create a French sentence" in prompt
        ):
            # First LLM call for translation exercise - return French sentence
            return "J'aime les pommes."
        elif "Translate the following French sentence" in prompt:
            # Second LLM call for translation exercise - return English translation
            return "I like apples."
        elif "translation" in prompt:
            return "J'aime les pommes.|I like apples."

        return "Mock response for testing"

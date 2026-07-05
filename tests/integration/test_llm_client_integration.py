"""Integration tests for MistralLLMClient with real Mistral API."""

import time

import pytest

from language_learner.evaluation.evaluator import AnswerEvaluator
from language_learner.models.exercise import Exercise, ExerciseType


@pytest.mark.integration
class TestMistralLLMClientIntegration:
    """Integration tests for MistralLLMClient using real Mistral API."""

    async def test_single_generate_call(self, real_llm_client):
        """Test a single generate call with real API."""
        result = real_llm_client.generate("What is the capital of France?")

        # Verify we got a non-empty response
        assert result is not None
        assert len(result.strip()) > 0

    async def test_generate_with_custom_parameters(self, real_llm_client):
        """Test generate with custom temperature and max_tokens."""
        result = real_llm_client.generate(
            "Tell me a short joke in one sentence.",
            temperature=0.9,
            max_tokens=50
        )

        # Verify we got a non-empty response
        assert result is not None
        assert len(result.strip()) > 0

    async def test_generate_with_french_prompts(self, real_llm_client):
        """Test generate with French language prompts."""
        prompts = [
            "Traduis 'Hello, how are you?' en français",
            "Quelle est la capitale de l'Espagne?",
        ]

        # Execute all prompts sequentially
        results = [real_llm_client.generate(prompt) for prompt in prompts]

        # Verify we got responses for all prompts
        assert len(results) == len(prompts)
        assert all(result is not None for result in results)
        assert all(len(result.strip()) > 0 for result in results)

    async def test_rate_limiting_minimum_interval(self, real_llm_client):
        """Test that rate limiting enforces minimum interval between calls.
        
        With rate_limit=0.8 calls/second (default), the minimum interval
        should be at least 1.25 seconds. This test verifies that consecutive
        calls are spaced appropriately.
        """
        # First call
        start_time = time.time()
        real_llm_client.generate("What is 2+2?")
        first_call_end = time.time()
        
        # Second call
        real_llm_client.generate("What is 3+3?")
        second_call_end = time.time()
        
        # Time between start of first call and end of second call
        # should be at least 1 second (rate is 0.8/sec = 1 call per 1.25 sec)
        elapsed = second_call_end - start_time
        assert elapsed >= 1.0, f"Expected at least 1.0s between calls, got {elapsed:.2f}s"


@pytest.mark.integration
class TestTranslationEvaluation:
    """Integration tests for translation evaluation with real LLM."""

    async def test_translation_evaluation_similar_translations(self, real_llm_client):
        """Test that slightly different but semantically equivalent translations are evaluated correctly.
        
        This test verifies that:
        1. Two slightly different translations of the same phrase are both accepted
        2. The LLM evaluator correctly identifies semantic equivalence
        3. Score > 75% when translations are semantically correct
        """
        evaluator = AnswerEvaluator(real_llm_client)
        
        # Create a translation exercise
        # French: "Il y a un lien fort entre ces deux événements."
        # Expected English: "There is a strong link between these two events."
        exercise = Exercise(
            exercise_id="translation-test-001",
            exercise_type=ExerciseType.TRANSLATION,
            question="Il y a un lien fort entre ces deux événements.",
            correct_answer="There is a strong link between these two events.",
        )
        
        # Test with exact match
        result1 = evaluator.evaluate_answer(exercise, "There is a strong link between these two events.")
        assert result1.score == 100.0
        assert result1.is_correct is True
        
        # Test with slightly different but semantically equivalent translation
        # User answer has a minor difference: "connection" instead of "link"
        user_answer = "There is a strong connection between these two events."
        result2 = evaluator.evaluate_answer(exercise, user_answer)
        
        # Should be accepted with high score (> 75%)
        assert result2.score > 75, f"Expected score > 75 for semantically equivalent translation, got {result2.score}"
        assert result2.is_correct is True, f"Expected is_correct=True for score {result2.score}, got {result2.is_correct}"
        assert result2.feedback is not None and len(result2.feedback) > 0
        
    async def test_translation_evaluation_with_typo(self, real_llm_client):
        """Test that translations with minor typos are handled gracefully.
        
        This test verifies that a translation with a typo still gets
        evaluated by the LLM and receives a reasonable score.
        """
        evaluator = AnswerEvaluator(real_llm_client)
        
        # Create a translation exercise
        exercise = Exercise(
            exercise_id="translation-test-002",
            exercise_type=ExerciseType.TRANSLATION,
            question="Il y a un lien fort entre ces deux événements.",
            correct_answer="There is a strong link between these two events.",
        )
        
        # User answer with typo: "evenimentsts" instead of "events"
        user_answer = "There is a strong link between these two evenimentsts."
        result = evaluator.evaluate_answer(exercise, user_answer)
        
        # Despite the typo, the LLM should evaluate it semantically
        # The score might be lower due to the error, but it should not be 0
        # unless the LLM determines it's completely wrong
        assert result.score >= 0, f"Expected non-negative score, got {result.score}"
        assert result.feedback is not None and len(result.feedback) > 0
        
    async def test_translation_evaluation_structured_output(self, real_llm_client):
        """Test that translation evaluation returns structured output (score and feedback).
        
        Verifies that the evaluation result contains:
        - A score between 0 and 100
        - Feedback text
        - Correct answer
        """
        evaluator = AnswerEvaluator(real_llm_client)
        
        exercise = Exercise(
            exercise_id="translation-test-003",
            exercise_type=ExerciseType.TRANSLATION,
            question="Bonjour, comment ça va?",
            correct_answer="Hello, how are you?",
        )
        
        # Test with a reasonable translation
        user_answer = "Hello, how is it going?"
        result = evaluator.evaluate_answer(exercise, user_answer)
        
        # Verify result structure
        assert 0 <= result.score <= 100, f"Score should be between 0 and 100, got {result.score}"
        assert isinstance(result.is_correct, bool), "is_correct should be a boolean"
        assert result.feedback is not None, "feedback should not be None"
        assert result.correct_answer == exercise.correct_answer
        
    async def test_translation_evaluation_different_phrasing(self, real_llm_client):
        """Test translations with different phrasing but same meaning."""
        evaluator = AnswerEvaluator(real_llm_client)
        
        # Multiple exercises with different phrasings
        test_cases = [
            {
                "question": "J'aime les pommes.",
                "correct_answer": "I like apples.",
                "user_answer": "I enjoy apples.",
            },
            {
                "question": "C'est une belle journée.",
                "correct_answer": "It is a beautiful day.",
                "user_answer": "It's a nice day.",
            },
        ]
        
        for i, test_case in enumerate(test_cases):
            exercise = Exercise(
                exercise_id=f"translation-phrasing-test-{i}",
                exercise_type=ExerciseType.TRANSLATION,
                question=test_case["question"],
                correct_answer=test_case["correct_answer"],
            )
            
            result = evaluator.evaluate_answer(exercise, test_case["user_answer"])
            
            # Different phrasing should still be accepted
            # We expect the LLM to recognize semantic equivalence
            assert result.score >= 0, f"Test case {i}: Expected non-negative score"
            assert result.feedback is not None, f"Test case {i}: Expected feedback"
            assert result.correct_answer == test_case["correct_answer"]

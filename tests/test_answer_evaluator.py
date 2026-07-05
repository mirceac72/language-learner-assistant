"""Tests for AnswerEvaluator"""
import pytest

from language_learner.core.mock_llm import MockLLMClient
from language_learner.evaluation.evaluator import AnswerEvaluator
from language_learner.models.exercise import Exercise, ExerciseType, DifficultyLevel


def make_exercise(exercise_type: ExerciseType, correct_answer: str) -> Exercise:
    return Exercise(
        exercise_id="test-1",
        exercise_type=exercise_type,
        question="Test question",
        correct_answer=correct_answer,
    )


@pytest.fixture
def evaluator():
    return AnswerEvaluator(MockLLMClient())


class TestExactMatch:
    def test_exact_match_returns_100(self, evaluator):
        ex = make_exercise(ExerciseType.FILL_BLANK, "apple")
        result = evaluator.evaluate_answer(ex, "apple")
        assert result.score == 100.0
        assert result.is_correct is True

    def test_case_insensitive_match(self, evaluator):
        ex = make_exercise(ExerciseType.FILL_BLANK, "Apple")
        result = evaluator.evaluate_answer(ex, "apple")
        assert result.is_correct is True

    def test_whitespace_normalized_match(self, evaluator):
        ex = make_exercise(ExerciseType.FILL_BLANK, "apple")
        result = evaluator.evaluate_answer(ex, "  apple  ")
        assert result.is_correct is True

    def test_no_match_fill_blank_returns_0(self, evaluator):
        ex = make_exercise(ExerciseType.FILL_BLANK, "apple")
        result = evaluator.evaluate_answer(ex, "orange")
        assert result.score == 0.0
        assert result.is_correct is False


class TestTranslationLLMEvaluation:
    def test_exact_match_skips_llm(self):
        mock = MockLLMClient()
        evaluator = AnswerEvaluator(mock)
        ex = make_exercise(ExerciseType.TRANSLATION, "I like apples.")
        result = evaluator.evaluate_answer(ex, "I like apples.")
        assert result.is_correct is True
        assert mock.call_count == 0

    def test_non_exact_translation_uses_llm(self):
        mock = MockLLMClient()
        evaluator = AnswerEvaluator(mock)
        ex = make_exercise(ExerciseType.TRANSLATION, "I like apples.")
        result = evaluator.evaluate_answer(ex, "I enjoy apples.")
        assert mock.call_count == 1
        assert result.score == 85.0
        assert result.is_correct is True
        assert result.feedback == "Good translation, minor differences are acceptable."

    def test_llm_failure_falls_back_to_incorrect(self):
        class FailingLLM:
            def generate(self, prompt, temperature=0.7, max_tokens=150):
                raise RuntimeError("LLM unavailable")

        evaluator = AnswerEvaluator(FailingLLM())
        ex = make_exercise(ExerciseType.TRANSLATION, "I like apples.")
        result = evaluator.evaluate_answer(ex, "I enjoy apples.")
        assert result.is_correct is False
        assert result.score == 0.0

    def test_correct_answer_always_set(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        ex = make_exercise(ExerciseType.TRANSLATION, "I like apples.")
        result = evaluator.evaluate_answer(ex, "I enjoy apples.")
        assert result.correct_answer == "I like apples."


class TestParseLLMEvaluation:
    def test_parse_valid_json_response(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        result = evaluator._parse_llm_json_response(
            '{"score": 75, "feedback": "Close answer."}',
        )
        assert result.score == 75.0
        assert result.feedback == "Close answer."

    def test_parse_json_with_whitespace(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        result = evaluator._parse_llm_json_response(
            '  {"score": 85, "feedback": "Good translation"}  ',
        )
        assert result.score == 85.0
        assert result.feedback == "Good translation"

    def test_parse_json_extract_from_text(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        # Test extraction of JSON from a text response
        result = evaluator._parse_llm_json_response(
            'Here is my evaluation: {"score": 90, "feedback": "Excellent"} and some more text',
        )
        assert result.score == 90.0
        assert result.feedback == "Excellent"

    def test_parse_score_colon_format(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        # Test fallback parsing for "score: 80" format
        result = evaluator._parse_llm_json_response(
            'score: 80',
        )
        assert result.score == 80.0
        assert result.feedback == "Acceptable"

    def test_parse_invalid_format_raises(self):
        evaluator = AnswerEvaluator(MockLLMClient())
        with pytest.raises(ValueError):
            evaluator._parse_llm_json_response("bad response")

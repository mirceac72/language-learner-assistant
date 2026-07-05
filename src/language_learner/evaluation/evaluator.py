# Answer Evaluator
import json
import logging
import re

from pydantic import BaseModel, ConfigDict, Field

from language_learner.core.llm_interface import LLMClient
from language_learner.models.exercise import EvaluationResult, Exercise, ExerciseType

logger = logging.getLogger(__name__)

# A translation is accepted as correct when the LLM score exceeds this value.
CORRECT_SCORE_THRESHOLD = 75


class LLMEvaluationOutput(BaseModel):
    """Structured output expected from the LLM when scoring a translation."""

    # extra="forbid" emits "additionalProperties": false, required by Mistral's
    # strict json_schema structured output mode.
    model_config = ConfigDict(extra="forbid")

    score: float = Field(..., ge=0, le=100, description="Score from 0 to 100")
    feedback: str = Field(..., description="Feedback for the user")


class AnswerEvaluator:
    """Evaluate user answers, using the LLM to judge non-exact translations."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_answer(self, exercise: Exercise, user_answer: str) -> EvaluationResult:
        """Evaluate a user's answer.

        Exact (case/whitespace-insensitive) matches are accepted directly.
        Otherwise, translation exercises are scored by the LLM; all other
        exercise types are marked incorrect.
        """
        normalized_user = user_answer.lower().strip()
        normalized_expected = exercise.correct_answer.lower().strip()

        if normalized_user == normalized_expected:
            return EvaluationResult(
                score=100.0,
                is_correct=True,
                feedback="Correct!",
                correct_answer=exercise.correct_answer,
            )

        if exercise.exercise_type == ExerciseType.TRANSLATION:
            return self._evaluate_translation_with_llm(exercise, user_answer)

        return self._incorrect_result(exercise)

    def _evaluate_translation_with_llm(
        self, exercise: Exercise, user_answer: str
    ) -> EvaluationResult:
        """Use the LLM to semantically score a translation that did not match exactly."""
        prompt = (
            f"Evaluate this translation exercise.\n"
            f'Question: "{exercise.question}"\n'
            f'Expected answer: "{exercise.correct_answer}"\n'
            f'User answer: "{user_answer}"\n\n'
            f"Respond with a JSON object containing score (0-100) and feedback."
        )

        schema = LLMEvaluationOutput.model_json_schema()
        try:
            response = self.llm.generate(
                prompt, temperature=0.3, max_tokens=200, response_schema=schema
            )
            result = self._parse_llm_json_response(response)
        except Exception as exc:
            logger.error(
                "LLM evaluation failed for exercise %s: %s", exercise.exercise_id, exc
            )
            return self._incorrect_result(exercise)

        is_correct = result.score > CORRECT_SCORE_THRESHOLD
        logger.debug(
            "Exercise %s scored %s (is_correct=%s)",
            exercise.exercise_id,
            result.score,
            is_correct,
        )
        return EvaluationResult(
            score=result.score,
            is_correct=is_correct,
            feedback=result.feedback,
            correct_answer=exercise.correct_answer,
        )

    @staticmethod
    def _parse_llm_json_response(response: str) -> LLMEvaluationOutput:
        """Parse the LLM response into an LLMEvaluationOutput.

        Accepts a bare JSON object, a JSON object embedded in surrounding text,
        or a plain ``score: <n>`` fallback. Raises ValueError if none apply.
        """
        match = re.search(r"\{[^{}]*\}", response, re.DOTALL)
        if match:
            return LLMEvaluationOutput(**json.loads(match.group(0)))

        try:
            return LLMEvaluationOutput(**json.loads(response.strip()))
        except json.JSONDecodeError:
            pass

        score_match = re.search(r"score[:\s]+(\d+)", response, re.IGNORECASE)
        if score_match:
            feedback = response.replace(score_match.group(0), "").strip()
            return LLMEvaluationOutput(
                score=float(score_match.group(1)), feedback=feedback or "Acceptable"
            )

        raise ValueError(f"Could not parse LLM response: {response[:200]}")

    @staticmethod
    def _incorrect_result(exercise: Exercise) -> EvaluationResult:
        """Build the standard result for an answer judged incorrect."""
        return EvaluationResult(
            score=0.0,
            is_correct=False,
            feedback="Incorrect, try again.",
            correct_answer=exercise.correct_answer,
        )

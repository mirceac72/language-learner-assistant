# Answer Evaluator
from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.models.exercise import EvaluationResult, Exercise


class AnswerEvaluator:
    """Evaluate user answers using LLM"""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def evaluate_answer(self, exercise: Exercise, user_answer: str) -> EvaluationResult:
        """Evaluate a user's answer"""
        # Simple evaluation for now
        is_correct = (
            user_answer.lower().strip() == exercise.correct_answer.lower().strip()
        )

        return EvaluationResult(
            score=100.0 if is_correct else 0.0,
            is_correct=is_correct,
            feedback="Correct!" if is_correct else "Incorrect, try again.",
            correct_answer=exercise.correct_answer,
            explanation=f"The correct answer is: {exercise.correct_answer}",
            learning_tips=["Review the vocabulary word and its usage"],
        )

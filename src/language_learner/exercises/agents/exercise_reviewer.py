# Exercise Reviewer Agent using LangGraph
import logging
from collections.abc import Callable
from typing import Any, TypedDict

from language_learner.core.llm_interface import LLMClient
from language_learner.models.exercise import Exercise, ExerciseType

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExerciseReviewerState(TypedDict):
    """State for exercise reviewer agent"""
    generated_exercises: list[Exercise]
    reviewed_exercises: list[Exercise]
    rejected_exercises: list[dict[str, Any]]
    feedback: list[str]
    iteration: int


class ExerciseReviewerAgent:
    """Agent that reviews and filters language exercises for quality"""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize exercise reviewer agent.

        Args:
            llm_client: LLM client for exercise review
        """
        self.llm = llm_client

    def create_node(self) -> Callable:
        """Create LangGraph node for exercise review.

        Returns:
            LangGraph node function
        """

        def reviewer_node(state: ExerciseReviewerState) -> ExerciseReviewerState:
            """Review and filter exercises for quality."""
            generated_exercises = state.get("generated_exercises", [])
            reviewed_exercises = state.get("reviewed_exercises", [])
            rejected_exercises = state.get("rejected_exercises", [])
            feedback = state.get("feedback", [])
            iteration = state.get("iteration", 1)

            logger.info(f"Reviewer node started with {len(generated_exercises)} exercises to review, iteration {iteration}")

            # Review each exercise
            for exercise in generated_exercises:
                if exercise not in reviewed_exercises and exercise not in [e["exercise"] for e in rejected_exercises]:
                    logger.info(f"Reviewing exercise: {exercise.exercise_type.value} - {exercise.question[:50]}...")
                    review_result = self._review_exercise(exercise, iteration)

                    exercise_details = {
                        "exercise": exercise
                    }
                    if "quality_score" in review_result:
                        exercise_details["quality_score"] = review_result["quality_score"]
                    if "feedback" in review_result:
                        exercise_details["feedback"] = review_result["feedback"]
                    if review_result["approved"]:
                        reviewed_exercises.append(exercise_details)
                        logger.info(f"Approved exercise: {exercise.exercise_type.value}")
                    else:
                        exercise_details["reason"] = review_result["reason"]
                        rejected_exercises.append(exercise_details)
                        logger.info(f"Rejected exercise: {exercise.exercise_type.value}, reason: {review_result['reason']}")

            # Update state
            new_state = {
                "generated_exercises": generated_exercises,
                "reviewed_exercises": reviewed_exercises,
                "rejected_exercises": rejected_exercises,
                "feedback": feedback,
                "iteration": iteration,
            }

            return new_state

        return reviewer_node

    def _review_exercise(self, exercise: Exercise, iteration: int = 1) -> dict[str, Any]:
        """Review a single exercise for quality using a pipeline of checks.

        Args:
            exercise: Exercise to review
            iteration: Current iteration number

        Returns:
            Dictionary with review result including approval status and feedback
        """
        logger.info(f"Starting review for exercise: {exercise.exercise_type.value}")

        # Run checks through the pipeline
        final_score, final_feedback, final_details = self._run_quality_pipeline(exercise, iteration)
        logger.info(f"Final quality score: {final_score}")

        if final_score < 70:  # Threshold for approval
            logger.info(f"Exercise rejected with score {final_score}: {final_feedback}")
            return {
                "approved": False,
                "reason": "low_quality",
                "quality_score": final_score,
                "feedback": final_feedback,
                "details": final_details
            }

        logger.info(f"Exercise approved with quality score: {final_score}")
        return {
            "approved": True,
            "reason": "approved",
            "quality_score": final_score,
            "feedback": final_feedback,
            "details": final_details
        }

    def _run_quality_pipeline(self, exercise: Exercise, iteration: int = 1) -> tuple[int, str, dict[str, Any]]:
        """Run quality checks through a pipeline and merge results using minimum strategy.

        Pipeline order:
        1. Trivial check (if fails, score = 0)
        2. Specific checks (e.g., translation quality for TRANSLATION)
        3. General quality check

        Merging: Keep the minimum score and its corresponding feedback.

        Args:
            exercise: Exercise to check
            iteration: Current iteration number

        Returns:
            Tuple of (final_score, final_feedback, final_details)
        """
        checks: list[tuple[int, str, dict[str, Any]]] = []

        # Step 1: Trivial check (failing = score 0)
        trivial_check = self._check_trivial_exercise(exercise)
        if trivial_check["trivial"]:
            checks.append((0, trivial_check["feedback"], {"source": "trivial_check", **trivial_check["details"]}))
        else:
            checks.append((100, trivial_check["feedback"], {"source": "trivial_check", "passed": True}))

        # Step 2: Specific checks (e.g., translation quality)
        specific_result = self._run_specific_checks(exercise, iteration)
        checks.append((specific_result["quality_score"], specific_result["feedback"], {"source": "specific_checks", **specific_result["details"]}))

        # Step 3: General quality check
        general_result = self._run_general_quality_check(exercise, iteration)
        checks.append((general_result["quality_score"], general_result["feedback"], {"source": "general_check", **general_result["details"]}))

        # Find the minimum score and its corresponding feedback
        min_score = min(check[0] for check in checks)
        min_checks = [check for check in checks if check[0] == min_score]
        # If multiple checks have the same minimum score, use the first one's feedback
        final_score = min_score
        final_feedback = min_checks[0][1]
        final_details = {
            "pipeline_results": {check[2]["source"]: {"score": check[0], "feedback": check[1]} for check in checks},
            "min_source": min_checks[0][2]["source"]
        }

        return final_score, final_feedback, final_details

    def _run_specific_checks(self, exercise: Exercise, iteration: int = 1) -> dict[str, Any]:
        """Run exercise-type specific quality checks.

        Args:
            exercise: Exercise to check
            iteration: Current iteration number

        Returns:
            Dictionary with quality score, feedback, and details
        """
        if exercise.exercise_type == ExerciseType.TRANSLATION:
            return self._check_translation_quality(exercise, iteration)
        else:
            # For non-translation exercises, return a neutral score
            # The general check will handle the actual assessment
            return {
                "quality_score": 100,
                "feedback": "No specific checks for this exercise type",
                "details": {"exercise_type": exercise.exercise_type.value}
            }

    def _run_general_quality_check(self, exercise: Exercise, iteration: int = 1) -> dict[str, Any]:
        """Run general quality assessment using LLM.

        Args:
            exercise: Exercise to assess
            iteration: Current iteration number

        Returns:
            Dictionary with quality assessment
        """
        prompt = f"""Assess the quality of this language learning exercise:

Exercise Type: {exercise.exercise_type.value}
Question: {exercise.question}
Correct Answer: {exercise.correct_answer}
Context: {exercise.context or 'None'}

Please evaluate this exercise on the following criteria:
1. Learning Value (0-30): Does it effectively teach the vocabulary word?
2. Challenge Level (0-25): Is it appropriately challenging?
3. Clarity (0-20): Is the question clear and unambiguous?
4. Originality (0-15): Is it creative and not too formulaic?
5. Contextual Relevance (0-10): Does it use natural language context?

Provide your assessment in EXACTLY this format:
quality_score|feedback|improvement_suggestions

Where:
- quality_score is a number from 0-100
- feedback is a brief explanation of the score
- improvement_suggestions are specific ways to improve the exercise

Example: 85|Good exercise with clear question and appropriate challenge|Could add more context about word usage

Iteration {iteration}: Be {'more strict' if iteration > 1 else 'balanced'} in your assessment."""

        try:
            response = self.llm.generate(prompt, temperature=0.5, max_tokens=150)
            parts = response.split("|")

            if len(parts) >= 3:
                try:
                    quality_score = int(parts[0].strip())
                    feedback = parts[1].strip()
                    suggestions = parts[2].strip()

                    return {
                        "quality_score": quality_score,
                        "feedback": feedback,
                        "details": {
                            "suggestions": suggestions,
                            "raw_response": response
                        }
                    }
                except ValueError:
                    # Fallback if score parsing fails
                    return {
                        "quality_score": 60,
                        "feedback": "Automatic quality assessment failed, using default score.",
                        "details": {"error": "score_parsing_failed", "raw_response": response}
                    }

            # Fallback if parsing fails
            return {
                "quality_score": 50,
                "feedback": "Could not parse quality assessment response.",
                "details": {"error": "parsing_failed", "raw_response": response}
            }

        except Exception as e:
            print(f"Error assessing exercise quality: {e}")
            # Default to moderate quality if assessment fails
            return {
                "quality_score": 65,
                "feedback": "Automatic quality assessment unavailable, using default moderate score.",
                "details": {"error": str(e)}
            }

    def _check_trivial_exercise(self, exercise: Exercise) -> dict[str, Any]:
        """Check if exercise is trivial or too easy.

        Args:
            exercise: Exercise to check

        Returns:
            Dictionary with trivial check result
        """
        # Check question length
        if len(exercise.question) < 15:
            return {
                "trivial": True,
                "feedback": "Exercise question is too short and likely trivial.",
                "details": {"issue": "short_question", "length": len(exercise.question)}
            }

        # Check answer length
        if len(exercise.correct_answer) < 2:
            return {
                "trivial": True,
                "feedback": "Exercise answer is too short and likely trivial.",
                "details": {"issue": "short_answer", "length": len(exercise.correct_answer)}
            }

        # Check for obvious patterns
        if exercise.exercise_type == ExerciseType.FILL_BLANK:
            if "___" not in exercise.question:
                return {
                    "trivial": True,
                    "feedback": "Fill-in-the-blank exercise missing blank space.",
                    "details": {"issue": "missing_blank"}
                }

        elif exercise.exercise_type == ExerciseType.MULTIPLE_CHOICE:
            if not exercise.options or len(exercise.options) < 3:
                return {
                    "trivial": True,
                    "feedback": "Multiple choice exercise needs at least 3 options.",
                    "details": {"issue": "insufficient_options", "count": len(exercise.options or [])}
                }

        return {"trivial": False, "feedback": "", "details": {}}

    def _check_translation_quality(self, exercise: Exercise, iteration: int = 1) -> dict[str, Any]:
        """Check translation quality specifically for translation exercises.

        Args:
            exercise: Translation exercise to assess
            iteration: Current iteration number

        Returns:
            Dictionary with translation quality assessment score and feedback.
        """
        translation_prompt = f"""Assess the translation quality of this language learning exercise:

Exercise Type: {exercise.exercise_type.value}
Question (French): {exercise.question}
Correct Answer (English): {exercise.correct_answer}
Context: {exercise.context or 'None'}

Please evaluate this exercise on the following criteria:
1. Translation Accuracy (0-40): Is the English translation accurate and faithful to the French text?
2. Learning Value (0-25): Does it effectively teach the vocabulary word?
3. Challenge Level (0-15): Is it appropriately challenging?
4. Clarity (0-10): Is the question clear and unambiguous?
5. Contextual Relevance (0-10): Does it use natural language context?

Provide your assessment in EXACTLY this format:
quality_score|feedback|improvement_suggestions

Where:
- quality_score is a number from 0-100
- feedback is a brief explanation of the score
- improvement_suggestions are specific ways to improve the exercise

Example: 85|Good exercise with clear question and appropriate challenge|Could add more context about word usage

Iteration {iteration}: Be {'more strict' if iteration > 1 else 'balanced'} in your assessment."""

        try:
            response = self.llm.generate(translation_prompt, temperature=0.5, max_tokens=150)
            parts = response.split("|")

            if len(parts) >= 3:
                try:
                    translation_score = int(parts[0].strip())
                    translation_feedback = parts[1].strip()
                    return {
                        "quality_score": translation_score,
                        "feedback": translation_feedback,
                        "details": {
                            "suggestions": parts[2].strip(),
                            "raw_response": response
                        }
                    }
                except ValueError:
                    pass

            # Fallback if parsing fails
            return {
                "quality_score": 60,
                "feedback": "Translation quality assessment parsing failed",
                "details": {"error": "parsing_failed", "raw_response": response}
            }

        except Exception as e:
            return {
                "quality_score": 60,
                "feedback": "Translation quality assessment unavailable",
                "details": {"error": str(e)}
            }

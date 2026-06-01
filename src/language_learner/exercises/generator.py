# Exercise Generator using LLM
from uuid import uuid4

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.exceptions import ExerciseGenerationError
from src.language_learner.models.exercise import DifficultyLevel, Exercise, ExerciseType


class ExerciseGenerator:
    """Generate language exercises from vocabulary words using LLM"""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize exercise generator with LLM client.

        Args:
            llm_client: LLM client for generating exercises
        """
        self.llm = llm_client
        from src.language_learner.exercises.agents.exercise_workflow import (
            ExerciseWorkflow,
        )
        self.workflow = ExerciseWorkflow(llm_client)

    def generate_exercises(
        self, vocabulary_words: list[str], count_per_word: int = 2
    ) -> list[Exercise]:
        """Generate exercises for vocabulary words using agent-based workflow.

        Args:
            vocabulary_words: List of vocabulary words
            count_per_word: Number of exercises per word (kept for API compatibility, but workflow handles its own count)

        Returns:
            List of generated exercises
        """
        exercises = self.workflow.run_workflow(vocabulary_words, max_iterations=2)
        print(f"Agent workflow generated {len(exercises)} approved exercises")
        return exercises

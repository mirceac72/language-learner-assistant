# Main Application Module

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.evaluation.evaluator import AnswerEvaluator
from src.language_learner.exercises.generator import ExerciseGenerator
from src.language_learner.exercises.player import ExercisePlayer
from src.language_learner.models.exercise import Exercise


class LanguageLearnerApplication:
    """Main application class"""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize the application with an LLM client.

        Args:
            llm_client: LLM client for exercise generation and evaluation
        """
        self.llm_client = llm_client
        self.exercise_generator = ExerciseGenerator(llm_client)
        self.answer_evaluator = AnswerEvaluator(llm_client)
        self.current_player = None

    def create_exercises(self, vocabulary_words: list[str]) -> list[Exercise]:
        """Create exercises from vocabulary words.

        Args:
            vocabulary_words: List of vocabulary words

        Returns:
            List of generated exercises

        Raises:
            ExerciseGenerationError: If exercise generation fails
        """
        return self.exercise_generator.generate_exercises(vocabulary_words)

    def start_exercise_session(self, exercises: list[Exercise]) -> ExercisePlayer:
        """Start a new exercise session.

        Args:
            exercises: List of exercises for the session

        Returns:
            Exercise player for managing the session
        """
        self.current_player = ExercisePlayer(exercises)
        return self.current_player

    def evaluate_answer(self, exercise: Exercise, user_answer: str):
        """Evaluate a user's answer.

        Args:
            exercise: Exercise being answered
            user_answer: User's answer

        Returns:
            Evaluation result
        """
        return self.answer_evaluator.evaluate_answer(exercise, user_answer)

    def get_current_player(self) -> ExercisePlayer:
        """Get the current exercise player.

        Returns:
            Current exercise player or None if no session started
        """
        return self.current_player

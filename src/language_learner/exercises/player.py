# Exercise Player

from datetime import datetime

from src.language_learner.models.exercise import Exercise, ExerciseSession


class ExercisePlayer:
    """Manage exercise sessions and user interaction"""

    def __init__(self, exercises: list[Exercise]) -> None:
        """Initialize exercise player with a list of exercises.

        Args:
            exercises: List of exercises for the session
        """
        self.exercises = exercises
        self.current_index = 0

        self.session = ExerciseSession(
            session_id="session_1",
            vocabulary_source="web_extraction",
            exercises=exercises,
            start_time=datetime.now(),
        )

    def get_current_exercise(self) -> Exercise | None:
        """Get the current exercise.

        Returns:
            Current exercise or None if all exercises are completed
        """
        if self.current_index < len(self.exercises):
            return self.exercises[self.current_index]
        return None

    def submit_answer(self, exercise_id: str, user_answer: str) -> bool:
        """Submit an answer for the current exercise.

        Args:
            exercise_id: ID of the exercise being answered
            user_answer: User's answer

        Returns:
            True if answer was submitted successfully, False otherwise
        """
        current_exercise = self.get_current_exercise()
        if current_exercise and current_exercise.exercise_id == exercise_id:
            current_exercise.user_answer = user_answer
            self.current_index += 1
            return True
        return False

    def has_more_exercises(self) -> bool:
        """Check if there are more exercises.

        Returns:
            True if more exercises remain, False otherwise
        """
        return self.current_index < len(self.exercises)

    def get_progress(self) -> str:
        """Get progress information.

        Returns:
            String showing completed/total exercises
        """
        completed = self.current_index
        total = len(self.exercises)
        return f"{completed}/{total}"

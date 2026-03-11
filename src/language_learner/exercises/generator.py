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

    def generate_exercises(
        self, vocabulary_words: list[str], count_per_word: int = 2
    ) -> list[Exercise]:
        """Generate exercises for vocabulary words.

        Args:
            vocabulary_words: List of vocabulary words
            count_per_word: Number of exercises per word

        Returns:
            List of generated exercises
        """
        exercises = []

        for word in vocabulary_words[:10]:  # Limit to top 10 words
            for _ in range(count_per_word):
                exercise = self._generate_single_exercise(word)
                if exercise:
                    exercises.append(exercise)

        return exercises

    def _generate_single_exercise(self, word: str) -> Exercise | None:
        """Generate a single exercise for a vocabulary word.

        Args:
            word: Vocabulary word to create exercise for

        Returns:
            Generated exercise or None if generation failed
        """
        exercise_type = self._choose_exercise_type()

        if exercise_type == ExerciseType.FILL_BLANK:
            return self._generate_fill_blank_exercise(word)
        elif exercise_type == ExerciseType.MULTIPLE_CHOICE:
            return self._generate_multiple_choice_exercise(word)
        elif exercise_type == ExerciseType.TRANSLATION:
            return self._generate_translation_exercise(word)
        else:
            return self._generate_fill_blank_exercise(word)

    def _choose_exercise_type(self) -> ExerciseType:
        """Choose a random exercise type.

        Returns:
            Randomly selected exercise type
        """
        import random

        types = [
            ExerciseType.FILL_BLANK,
            ExerciseType.MULTIPLE_CHOICE,
            ExerciseType.TRANSLATION,
        ]
        return random.choice(types)

    def _generate_fill_blank_exercise(self, word: str) -> Exercise | None:
        """Generate fill-in-the-blank exercise.

        Args:
            word: Vocabulary word for the exercise

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French fill-in-the-blank exercise for the word "{word}".
Provide ONLY the sentence with the word missing (use ___), the correct answer, and English translation.
Use EXACTLY this format: sentence|correct_answer|translation
Example: J'aime manger des ___.|pommes|I like to eat apples."""

        try:
            response = self.llm.generate(prompt, temperature=0.8, max_tokens=100)
            parts = response.split("|")
            if len(parts) >= 3:
                return Exercise(
                    exercise_id=str(uuid4()),
                    exercise_type=ExerciseType.FILL_BLANK,
                    question=f"Complete the sentence: {parts[0].strip()}",
                    correct_answer=parts[1].strip(),
                    context=f"Translation: {parts[2].strip()}",
                    difficulty=DifficultyLevel.MEDIUM,
                )
        except Exception as e:
            raise ExerciseGenerationError(
                f"Failed to generate fill-in-the-blank exercise for '{word}': {e}"
            ) from e

        return None

    def _generate_multiple_choice_exercise(self, word: str) -> Exercise | None:
        """Generate multiple choice exercise.

        Args:
            word: Vocabulary word for the exercise

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French multiple choice exercise for the word "{word}".
Provide ONLY the question, correct answer, and 3 incorrect options.
Use EXACTLY this format: question|correct_answer|option1|option2|option3
Example: What does 'pomme' mean?|apple|fruit|red|tree"""

        try:
            response = self.llm.generate(prompt, temperature=0.8, max_tokens=100)
            parts = response.split("|")
            if len(parts) >= 5:
                options = [
                    parts[2].strip(),
                    parts[3].strip(),
                    parts[4].strip(),
                    parts[1].strip(),
                ]
                import random

                random.shuffle(options)

                return Exercise(
                    exercise_id=str(uuid4()),
                    exercise_type=ExerciseType.MULTIPLE_CHOICE,
                    question=parts[0].strip(),
                    correct_answer=parts[1].strip(),
                    options=options,
                    context=f"Choose the correct meaning/usage of '{word}'",
                    difficulty=DifficultyLevel.MEDIUM,
                )
        except Exception as e:
            raise ExerciseGenerationError(
                f"Failed to generate multiple choice exercise for '{word}': {e}"
            ) from e

        return None

    def _generate_translation_exercise(self, word: str) -> Exercise | None:
        """Generate translation exercise.

        Args:
            word: Vocabulary word for the exercise

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French to English translation exercise for the word "{word}".
Provide ONLY the French sentence containing the word and its English translation.
Use EXACTLY this format: french_sentence|english_translation
Example: J'aime les pommes.|I like apples."""

        try:
            response = self.llm.generate(prompt, temperature=0.7, max_tokens=80)
            parts = response.split("|")
            if len(parts) >= 2:
                return Exercise(
                    exercise_id=str(uuid4()),
                    exercise_type=ExerciseType.TRANSLATION,
                    question=f"Translate to English: {parts[0].strip()}",
                    correct_answer=parts[1].strip(),
                    context=f"Focus on translating the word '{word}' correctly",
                    difficulty=DifficultyLevel.MEDIUM,
                )
        except Exception as e:
            raise ExerciseGenerationError(
                f"Failed to generate translation exercise for '{word}': {e}"
            ) from e

        return None

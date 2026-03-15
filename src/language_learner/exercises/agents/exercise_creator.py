# Exercise Creator Agent using LangGraph
import logging
import random
from collections.abc import Callable
from typing import TypedDict
from uuid import uuid4

from src.language_learner.core.llm_interface import LLMClient
from src.language_learner.models.exercise import DifficultyLevel, Exercise, ExerciseType

# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class ExerciseCreatorState(TypedDict):
    """State for exercise creator agent"""
    vocabulary_words: list[str]
    generated_exercises: list[Exercise]
    iteration: int


class ExerciseCreatorAgent:
    """Agent that creates language exercises using LLM"""

    def __init__(self, llm_client: LLMClient) -> None:
        """Initialize exercise creator agent.

        Args:
            llm_client: LLM client for exercise generation
        """
        self.llm = llm_client

    def create_node(self) -> Callable:
        """Create LangGraph node for exercise creation.

        Returns:
            LangGraph node function
        """

        def creator_node(state: ExerciseCreatorState) -> ExerciseCreatorState:
            """Create exercises for all vocabulary words."""
            vocabulary_words = state["vocabulary_words"]
            generated_exercises = state.get("generated_exercises", [])
            iteration = state.get("iteration", 1)

            logger.info(f"Creator node started with {len(vocabulary_words)} words, iteration {iteration}")

            # Generate exercises for ALL vocabulary words
            for word in vocabulary_words:
                # Generate 2-3 exercises per word
                exercises_to_generate = 2 if iteration == 1 else 1
                logger.info(f"Generating {exercises_to_generate} exercises for word: {word}")

                for _ in range(exercises_to_generate):
                    exercise = self._generate_single_exercise(word, iteration)
                    if exercise:
                        generated_exercises.append(exercise)
                        logger.info(f"Generated exercise: {exercise.exercise_type.value} for word {word}")

            # Update state
            new_state = {
                "vocabulary_words": vocabulary_words,
                "generated_exercises": generated_exercises,
                "iteration": iteration,
            }

            return new_state

        return creator_node

    def _generate_single_exercise(self, word: str, iteration: int = 1) -> Exercise | None:
        """Generate a single exercise for a vocabulary word.

        Args:
            word: Vocabulary word to create exercise for
            iteration: Current iteration number (affects exercise variety)

        Returns:
            Generated exercise or None if generation failed
        """
        exercise_type = self._choose_exercise_type(iteration)
        logger.info(f"Generating {exercise_type.value} exercise for word: {word}")

        if exercise_type == ExerciseType.FILL_BLANK:
            return self._generate_fill_blank_exercise(word, iteration)
        elif exercise_type == ExerciseType.MULTIPLE_CHOICE:
            return self._generate_multiple_choice_exercise(word, iteration)
        elif exercise_type == ExerciseType.TRANSLATION:
            return self._generate_translation_exercise(word, iteration)
        else:
            return self._generate_fill_blank_exercise(word, iteration)

    def _choose_exercise_type(self, iteration: int = 1) -> ExerciseType:
        """Choose an exercise type, with variety based on iteration.

        Args:
            iteration: Current iteration number

        Returns:
            Randomly selected exercise type
        """
        # Vary exercise types more in later iterations
        if iteration > 1:
            types = [
                ExerciseType.FILL_BLANK,
                ExerciseType.MULTIPLE_CHOICE,
                ExerciseType.TRANSLATION,
                ExerciseType.SENTENCE_CONSTRUCTION,
            ]
        else:
            types = [
                ExerciseType.FILL_BLANK,
                ExerciseType.MULTIPLE_CHOICE,
                ExerciseType.TRANSLATION,
            ]

        return random.choice(types)

    def _generate_fill_blank_exercise(self, word: str, iteration: int = 1) -> Exercise | None:
        """Generate fill-in-the-blank exercise.

        Args:
            word: Vocabulary word for the exercise
            iteration: Current iteration number

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French fill-in-the-blank exercise for the word "{word}".
Provide ONLY the sentence with the word missing (use ___), the correct answer, and English translation.
Use EXACTLY this format: sentence|correct_answer|translation
Example: J'aime manger des ___.|pommes|I like to eat apples.

Iteration {iteration}: Focus on creating {'more challenging' if iteration > 1 else 'varied'} exercises."""

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
            print(f"Error generating fill-in-the-blank exercise: {e}")

        return None

    def _generate_multiple_choice_exercise(self, word: str, iteration: int = 1) -> Exercise | None:
        """Generate multiple choice exercise.

        Args:
            word: Vocabulary word for the exercise
            iteration: Current iteration number

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French multiple choice exercise for the word "{word}".
Provide ONLY the question, correct answer, and 3 incorrect options.
Use EXACTLY this format: question|correct_answer|option1|option2|option3
Example: What does 'pomme' mean?|apple|fruit|red|tree

Iteration {iteration}: Focus on creating {'more challenging' if iteration > 1 else 'clear'} questions."""

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
            print(f"Error generating multiple choice exercise: {e}")

        return None

    def _generate_translation_exercise(self, word: str, iteration: int = 1) -> Exercise | None:
        """Generate translation exercise.

        Args:
            word: Vocabulary word for the exercise
            iteration: Current iteration number

        Returns:
            Generated exercise or None if generation failed
        """
        prompt = f"""Create a French to English translation exercise for the word "{word}".
Provide ONLY the French sentence containing the word and its English translation.
Use EXACTLY this format: french_sentence|english_translation
Example: J'aime les pommes.|I like apples.

Iteration {iteration}: Focus on creating {'more complex' if iteration > 1 else 'natural'} sentences."""

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
            print(f"Error generating translation exercise: {e}")

        return None

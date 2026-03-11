"""Exercise Display Module

This module provides functionality to display exercises and handle user interactions.
"""

import streamlit as st

from ..core.application import LanguageLearnerApplication
from ..exercises.player import ExercisePlayer
from ..models.exercise import Exercise


def display_exercise(
    exercise: Exercise, player: ExercisePlayer, app: LanguageLearnerApplication
) -> bool:
    """Display an exercise and handle user input.

    Args:
        exercise: The current exercise to display
        player: The exercise player managing the session
        app: The language learner application

    Returns:
        True if exercise was completed, False otherwise
    """
    # Check if this exercise has been answered
    if exercise.user_answer is None:
        # Show the exercise
        st.write(f"Exercise {player.get_progress()}")
        st.write(f"**Question:** {exercise.question}")

        if exercise.context:
            st.write(f"*Context:* {exercise.context}")

        # Display exercise based on type
        if exercise.exercise_type.value == "fill_blank":
            user_answer = st.text_input(
                "Your answer:", key=f"answer_{exercise.exercise_id}"
            )
            if st.button("Submit Answer"):
                # Store the answer and evaluation
                evaluation = app.evaluate_answer(exercise, user_answer)
                exercise.user_answer = user_answer
                exercise.evaluation = {
                    "score": evaluation.score,
                    "is_correct": evaluation.is_correct,
                    "feedback": evaluation.feedback,
                    "correct_answer": evaluation.correct_answer,
                    "explanation": evaluation.explanation,
                    "learning_tips": evaluation.learning_tips,
                }
                return True

        elif exercise.exercise_type.value == "multiple_choice":
            if exercise.options:
                st.write("Choose the correct answer:")
                user_answer = st.radio(
                    "Options:", exercise.options, key=f"answer_{exercise.exercise_id}"
                )
                if st.button("Submit Answer"):
                    # Store the answer and evaluation
                    evaluation = app.evaluate_answer(exercise, user_answer)
                    exercise.user_answer = user_answer
                    exercise.evaluation = {
                        "score": evaluation.score,
                        "is_correct": evaluation.is_correct,
                        "feedback": evaluation.feedback,
                        "correct_answer": evaluation.correct_answer,
                        "explanation": evaluation.explanation,
                        "learning_tips": evaluation.learning_tips,
                    }
                    return True

        elif exercise.exercise_type.value == "translation":
            st.write("Provide your translation:")
            user_answer = st.text_input(
                "Your translation:", key=f"answer_{exercise.exercise_id}"
            )
            if st.button("Submit Answer"):
                # Store the answer and evaluation
                evaluation = app.evaluate_answer(exercise, user_answer)
                exercise.user_answer = user_answer
                exercise.evaluation = {
                    "score": evaluation.score,
                    "is_correct": evaluation.is_correct,
                    "feedback": evaluation.feedback,
                    "correct_answer": evaluation.correct_answer,
                    "explanation": evaluation.explanation,
                    "learning_tips": evaluation.learning_tips,
                }
                return True
    else:
        # Show feedback and ask for confirmation
        display_exercise_feedback(exercise)
        if st.button("Continue to Next Exercise"):
            # Move to next exercise
            player.submit_answer(exercise.exercise_id, exercise.user_answer)
            return True

    return False


def display_exercise_feedback(exercise: Exercise) -> None:
    """Display feedback for a completed exercise.

    Args:
        exercise: The exercise with user answer and evaluation
    """
    st.write("Exercise Feedback")
    st.write(f"**Question:** {exercise.question}")
    st.write(f"**Your Answer:** {exercise.user_answer}")

    if exercise.evaluation:
        evaluation = exercise.evaluation
        st.write(f"**Feedback:** {evaluation['feedback']}")
        st.write(f"**Score:** {evaluation['score']}/100")

        if not evaluation["is_correct"]:
            st.write(f"**Correct Answer:** {evaluation['correct_answer']}")
            st.write(f"**Explanation:** {evaluation['explanation']}")


def display_exercise_completion() -> None:
    """Display completion message when all exercises are done."""
    st.success("You have completed all exercises!")
    st.balloons()

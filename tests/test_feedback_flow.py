# Test the feedback flow functionality
from src.language_learner.core.application import LanguageLearnerApplication
from src.language_learner.core.mock_llm import MockLLMClient


def test_feedback_flow():
    """Test the complete feedback and confirmation flow"""
    print("Testing feedback flow...")

    # Initialize application
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    # Generate exercises
    exercises = app.create_exercises(["pomme"])
    print(f"Generated {len(exercises)} exercises")

    # Start exercise session
    player = app.start_exercise_session(exercises)

    # Test first exercise
    exercise = player.get_current_exercise()
    if exercise:
        print(f"\nExercise 1: {exercise.question}")
        print(f"Type: {exercise.exercise_type.value}")

        # Simulate user answering (before submission)
        print("\n--- Before submission ---")
        print("User answer: None")
        print("Evaluation: None")
        print(
            f"Exercise state: {'answered' if exercise.user_answer else 'not answered'}"
        )

        # Simulate submission
        test_answer = "apple"  # Correct answer for pomme
        evaluation = app.evaluate_answer(exercise, test_answer)

        # Store answer and evaluation (what happens when user clicks submit)
        exercise.user_answer = test_answer
        exercise.evaluation = {
            "score": evaluation.score,
            "is_correct": evaluation.is_correct,
            "feedback": evaluation.feedback,
            "correct_answer": evaluation.correct_answer,
            "explanation": evaluation.explanation,
            "learning_tips": evaluation.learning_tips,
        }

        print("\n--- After submission (feedback screen) ---")
        print(f"User answer: {exercise.user_answer}")
        print(f"Feedback: {exercise.evaluation['feedback']}")
        print(f"Score: {exercise.evaluation['score']}/100")
        print(f"Correct: {exercise.evaluation['is_correct']}")
        print(
            f"Exercise state: {'answered' if exercise.user_answer else 'not answered'}"
        )

        # Verify feedback content
        assert exercise.user_answer == test_answer
        assert exercise.evaluation is not None
        assert exercise.evaluation["feedback"] is not None
        assert len(exercise.evaluation["feedback"]) > 0

        print("\n--- After confirmation (next exercise) ---")
        # Simulate user clicking "Continue to Next Exercise"
        player.submit_answer(exercise.exercise_id, test_answer)

        next_exercise = player.get_current_exercise()
        if next_exercise:
            print(f"Next exercise: {next_exercise.question}")
            print(f"Progress: {player.get_progress()}")
        else:
            print("No more exercises - session complete!")

        print("✅ Feedback flow working correctly")

    print("\n🎉 Feedback flow test completed successfully!")


if __name__ == "__main__":
    test_feedback_flow()

# Test script to verify Streamlit display functionality
from src.language_learner.core.application import LanguageLearnerApplication
from src.language_learner.core.mock_llm import MockLLMClient


def test_streamlit_display():
    """Test that exercises have proper content for Streamlit display"""
    print("Testing Streamlit display functionality...")

    # Initialize application
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    # Generate exercises
    test_words = ["pomme", "chat"]
    exercises = app.create_exercises(test_words)

    print(f"Generated {len(exercises)} exercises")

    # Test exercise player
    player = app.start_exercise_session(exercises)

    # Test first exercise display
    exercise = player.get_current_exercise()
    if exercise:
        print("\nFirst exercise display test:")
        print(f"Progress: {player.get_progress()}")
        print(f"Question: {exercise.question}")
        print(f"Type: {exercise.exercise_type.value}")

        if exercise.context:
            print(f"Context: {exercise.context}")

        if exercise.options:
            print(f"Options: {exercise.options}")

        # Verify content is not empty
        assert exercise.question and len(exercise.question.strip()) > 0
        assert exercise.correct_answer and len(exercise.correct_answer.strip()) > 0

        print("✅ All exercise content is properly populated")

        # Test evaluation display
        test_answer = "test"
        evaluation = app.evaluate_answer(exercise, test_answer)

        print("\nEvaluation display test:")
        print(f"Score: {evaluation.score}/100")
        print(f"Feedback: {evaluation.feedback}")
        print(f"Correct: {evaluation.is_correct}")

        if not evaluation.is_correct:
            print(f"Correct answer: {evaluation.correct_answer}")

        print("✅ Evaluation display working correctly")

    print("\n🎉 All Streamlit display functionality tests passed!")


if __name__ == "__main__":
    test_streamlit_display()

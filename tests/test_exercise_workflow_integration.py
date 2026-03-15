# Test the implementation using pytest
from src.language_learner.core.application import LanguageLearnerApplication
from src.language_learner.core.mock_llm import MockLLMClient
from src.language_learner.models.exercise import Exercise, ExerciseType


def test_exercise_generation():
    """Test exercise generation functionality"""
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    test_words = ["pomme", "chat", "maison"]
    exercises = app.create_exercises(test_words)

    assert len(exercises) > 0, "Should generate at least one exercise"

    for exercise in exercises:
        assert isinstance(exercise, Exercise)
        assert exercise.exercise_id is not None
        assert exercise.question is not None
        assert exercise.correct_answer is not None
        assert exercise.exercise_type in [
            ExerciseType.FILL_BLANK,
            ExerciseType.MULTIPLE_CHOICE,
            ExerciseType.TRANSLATION,
        ]


def test_exercise_player():
    """Test exercise player functionality"""
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    test_words = ["test"]
    exercises = app.create_exercises(test_words)

    if exercises:
        player = app.start_exercise_session(exercises)

        # Test initial state
        assert player.has_more_exercises()
        # Should have at least 2 exercises (2 in iteration 1 + potentially more in iteration 2)
        progress = player.get_progress()
        total_exercises = int(progress.split('/')[1])
        assert total_exercises >= 2, f"Expected at least 2 exercises, got {total_exercises}"

        # Test getting current exercise
        current_exercise = player.get_current_exercise()
        assert current_exercise is not None

        # Test submitting answer
        result = player.submit_answer(current_exercise.exercise_id, "test answer")
        assert result

        # Test progress after submission
        assert player.has_more_exercises() or player.get_progress() == "1/2"


def test_answer_evaluation():
    """Test answer evaluation functionality"""
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    # Create a simple exercise for testing
    test_exercise = Exercise(
        exercise_id="test_1",
        exercise_type=ExerciseType.FILL_BLANK,
        question="Test question",
        correct_answer="correct",
    )

    # Test correct answer
    evaluation = app.evaluate_answer(test_exercise, "correct")
    assert evaluation.is_correct
    assert evaluation.score == 100.0

    # Test incorrect answer
    evaluation = app.evaluate_answer(test_exercise, "wrong")
    assert not evaluation.is_correct
    assert evaluation.score == 0.0


def test_mock_llm_client():
    """Test mock LLM client functionality"""
    llm_client = MockLLMClient()

    # Test fill-in-the-blank prompt
    response = llm_client.generate("fill-in-the-blank exercise")
    assert "|" in response
    assert "Le chat est sur le ___." in response

    # Test multiple choice prompt
    response = llm_client.generate("multiple choice exercise")
    assert "|" in response
    assert "What does 'pomme' mean?" in response

    # Test translation prompt
    response = llm_client.generate("translation exercise")
    assert "|" in response
    assert "J'aime les pommes." in response


def test_exercise_content():
    """Test that exercises have proper content"""
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    test_words = ["pomme"]
    exercises = app.create_exercises(test_words)

    assert len(exercises) > 0

    for exercise in exercises:
        # Ensure exercise has content
        assert exercise.question is not None
        assert len(exercise.question.strip()) > 0, (
            "Exercise question should not be empty"
        )

        assert exercise.correct_answer is not None
        assert len(exercise.correct_answer.strip()) > 0, (
            "Exercise correct answer should not be empty"
        )

        # Check that the exercise has meaningful content
        # Note: Mock LLM generates specific responses, so we check for general content quality
        assert len(exercise.question) > 10, (
            "Exercise question should have substantial content"
        )
        assert len(exercise.correct_answer) > 1, (
            "Exercise answer should have substantial content"
        )


def test_feedback_flow():
    """Test the feedback and confirmation flow"""
    llm_client = MockLLMClient()
    app = LanguageLearnerApplication(llm_client)

    # Create exercises
    exercises = app.create_exercises(["test"])
    assert len(exercises) > 0

    # Test exercise submission and feedback
    exercise = exercises[0]

    # Simulate user answering
    test_answer = "user answer"
    evaluation = app.evaluate_answer(exercise, test_answer)

    # Store answer and evaluation (simulating what happens when user submits)
    # Convert to dict to match app behavior
    exercise.user_answer = test_answer
    exercise.evaluation = {
        "score": evaluation.score,
        "is_correct": evaluation.is_correct,
        "feedback": evaluation.feedback,
        "correct_answer": evaluation.correct_answer,
        "explanation": evaluation.explanation,
        "learning_tips": evaluation.learning_tips,
    }

    # Verify feedback is available
    assert exercise.user_answer == test_answer
    assert exercise.evaluation is not None
    assert exercise.evaluation["score"] >= 0
    assert exercise.evaluation["feedback"] is not None
    assert exercise.evaluation["is_correct"] is not None

    # Verify we can access feedback for display
    assert exercise.evaluation["feedback"] is not None
    assert len(exercise.evaluation["feedback"]) > 0

# Test the Exercise Creator Agent

import pytest

from src.language_learner.core.mock_llm import MockLLMClient
from src.language_learner.exercises.agents.exercise_creator import (
    ExerciseCreatorAgent,
    ExerciseCreatorState,
)
from src.language_learner.models.exercise import Exercise


def test_creator_generates_exercises_for_all_words():
    """Test that creator agent generates exercises for all vocabulary words in one visit"""
    # Setup
    llm_client = MockLLMClient()
    creator_agent = ExerciseCreatorAgent(llm_client)
    creator_node = creator_agent.create_node()

    # Test data
    test_words = ["pomme", "chat", "maison"]

    # Initial state
    initial_state: ExerciseCreatorState = {
        "vocabulary_words": test_words,
        "generated_exercises": [],
        "iteration": 1,
    }

    # Execute creator node
    result_state = creator_node(initial_state)

    # Validation
    assert "vocabulary_words" in result_state
    assert "generated_exercises" in result_state
    assert "iteration" in result_state
    assert "current_word" not in result_state  # Should be removed

    # Should have generated exercises for all words
    generated_exercises = result_state["generated_exercises"]
    assert len(generated_exercises) > 0, "Should generate exercises"

    # Check that exercises were created for each word
    # Since MockLLM returns generic responses, we'll verify by counting exercises
    # Should generate 2 exercises per word in iteration 1
    expected_min_exercises = len(test_words) * 2
    assert len(generated_exercises) >= expected_min_exercises, \
        f"Expected at least {expected_min_exercises} exercises (2 per word), got {len(generated_exercises)}"

    # Verify all exercises are properly structured
    for exercise in generated_exercises:
        assert isinstance(exercise, Exercise)
        assert exercise.exercise_id is not None
        assert exercise.question is not None
        assert exercise.correct_answer is not None
        assert len(exercise.question.strip()) > 0
        assert len(exercise.correct_answer.strip()) > 0


def test_creator_state_structure():
    """Test that creator node maintains correct state structure"""
    llm_client = MockLLMClient()
    creator_agent = ExerciseCreatorAgent(llm_client)
    creator_node = creator_agent.create_node()

    test_words = ["test1", "test2"]
    initial_state: ExerciseCreatorState = {
        "vocabulary_words": test_words,
        "generated_exercises": [],
        "iteration": 1,
    }

    result_state = creator_node(initial_state)

    # Verify state structure
    assert isinstance(result_state, dict)
    assert "vocabulary_words" in result_state
    assert "generated_exercises" in result_state
    assert "iteration" in result_state
    assert len(result_state) == 3  # Only these 3 fields should exist

    # Verify vocabulary words are preserved
    assert result_state["vocabulary_words"] == test_words

    # Verify iteration is preserved
    assert result_state["iteration"] == 1


def test_creator_exercise_variety():
    """Test that creator generates different exercise types"""
    llm_client = MockLLMClient()
    creator_agent = ExerciseCreatorAgent(llm_client)
    creator_node = creator_agent.create_node()

    # Use multiple words to test variety (mock LLM returns different types for different words)
    test_words = ["pomme", "chat"]  # pomme -> fill_blank, chat -> translation/multiple_choice
    initial_state: ExerciseCreatorState = {
        "vocabulary_words": test_words,
        "generated_exercises": [],
        "iteration": 1,
    }

    result_state = creator_node(initial_state)
    generated_exercises = result_state["generated_exercises"]

    # Should generate multiple exercises
    assert len(generated_exercises) >= 4, "Should generate at least 2 exercises per word in iteration 1"

    # Check for variety in exercise types
    exercise_types = set()
    for exercise in generated_exercises:
        exercise_types.add(exercise.exercise_type)

    # Should have at least 2 different exercise types (mock LLM generates different types)
    assert len(exercise_types) >= 2, f"Should generate variety of exercise types, got: {exercise_types}"


def test_creator_second_iteration():
    """Test creator behavior in second iteration"""
    llm_client = MockLLMClient()
    creator_agent = ExerciseCreatorAgent(llm_client)
    creator_node = creator_agent.create_node()

    test_words = ["test1", "test2"]
    initial_state: ExerciseCreatorState = {
        "vocabulary_words": test_words,
        "generated_exercises": [],
        "iteration": 2,
    }

    result_state = creator_node(initial_state)
    generated_exercises = result_state["generated_exercises"]

    # In iteration 2, should generate 1 exercise per word
    assert len(generated_exercises) >= 2, "Should generate at least 1 exercise per word in iteration 2"

    # Verify iteration is preserved
    assert result_state["iteration"] == 2


def test_creator_empty_words():
    """Test creator with empty vocabulary words list"""
    llm_client = MockLLMClient()
    creator_agent = ExerciseCreatorAgent(llm_client)
    creator_node = creator_agent.create_node()

    initial_state: ExerciseCreatorState = {
        "vocabulary_words": [],
        "generated_exercises": [],
        "iteration": 1,
    }

    result_state = creator_node(initial_state)

    # Should handle empty list gracefully
    assert result_state["generated_exercises"] == []
    assert result_state["vocabulary_words"] == []
    assert result_state["iteration"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

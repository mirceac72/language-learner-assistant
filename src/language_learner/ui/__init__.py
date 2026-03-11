"""UI module for Language Learner Assistant.

This module contains Streamlit UI components and display logic.
"""

from .exercise_display import display_exercise, display_exercise_completion
from .vocabulary_display import display_vocabulary

__all__ = ["display_vocabulary", "display_exercise", "display_exercise_completion"]

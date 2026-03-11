# Exercise Data Models
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class ExerciseType(Enum):
    """Types of exercises that can be generated"""

    FILL_BLANK = "fill_blank"
    MULTIPLE_CHOICE = "multiple_choice"
    TRANSLATION = "translation"
    SENTENCE_CONSTRUCTION = "sentence_construction"
    WORD_MATCHING = "word_matching"


class DifficultyLevel(Enum):
    """Difficulty levels for exercises"""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class EvaluationResult:
    """Represents the evaluation of a user's answer"""

    score: float  # 0-100
    is_correct: bool
    feedback: str
    correct_answer: str
    explanation: str
    learning_tips: list[str] | None = None

    def __post_init__(self):
        if self.learning_tips is None:
            self.learning_tips = []


@dataclass
class Exercise:
    """Represents a single language learning exercise"""

    exercise_id: str
    exercise_type: ExerciseType
    question: str
    correct_answer: str
    context: str | None = None
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    options: list[str] | None = None  # For multiple choice
    user_answer: str | None = None
    evaluation: dict[str, Any] | None = (
        None  # Store evaluation result as dict to avoid circular import
    )
    feedback: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class ExerciseSession:
    """Represents a complete exercise session"""

    session_id: str
    vocabulary_source: str
    exercises: list[Exercise]
    start_time: datetime
    end_time: datetime | None = None
    results: list[dict[str, Any]] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []

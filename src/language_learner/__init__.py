"""Language Learner Assistant Package

This package provides tools for learning languages through web content analysis
and interactive exercises.
"""

from .core.application import LanguageLearnerApplication
from .models.exercise import Exercise
from .web.vocabulary_extractor import VocabularyExtractor

__version__ = "0.1.0"
__all__ = ["LanguageLearnerApplication", "VocabularyExtractor", "Exercise"]

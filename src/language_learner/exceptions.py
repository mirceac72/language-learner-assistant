"""Custom exception classes for Language Learner Assistant."""


class LanguageLearnerError(Exception):
    """Base exception class for all application errors."""
    pass


class ConfigurationError(LanguageLearnerError):
    """Raised when there's an issue with configuration."""
    pass


class WebFetchError(LanguageLearnerError):
    """Raised when there's an error fetching web content."""
    pass


class LLMError(LanguageLearnerError):
    """Raised when there's an error with LLM operations."""
    pass


class ExerciseGenerationError(LanguageLearnerError):
    """Raised when exercise generation fails."""
    pass


class ValidationError(LanguageLearnerError):
    """Raised when input validation fails."""
    pass

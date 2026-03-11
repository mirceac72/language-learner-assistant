"""Configuration module for Language Learner Assistant.

This module handles application configuration using environment variables
and provides settings management.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application configuration settings."""

    # Application settings
    app_name: str = "Language Learner Assistant"
    app_version: str = "0.1.0"
    debug_mode: bool = Field(False, env="DEBUG_MODE")

    # LLM Configuration
    mistral_api_key: str | None = Field(None, env="MISTRAL_API_KEY")
    llm_timeout: int = Field(30, env="LLM_TIMEOUT")
    llm_max_retries: int = Field(3, env="LLM_MAX_RETRIES")

    # Web scraping configuration
    web_request_timeout: int = Field(10, env="WEB_REQUEST_TIMEOUT")
    user_agent: str = Field(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        env="USER_AGENT",
    )

    # Exercise generation settings
    default_language: str = Field("french", env="DEFAULT_LANGUAGE")
    min_word_length: int = Field(4, env="MIN_WORD_LENGTH")
    top_vocabulary_words: int = Field(50, env="TOP_VOCABULARY_WORDS")
    exercises_per_session: int = Field(10, env="EXERCISES_PER_SESSION")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """Get the application settings.

    Returns:
        AppSettings: The application configuration
    """
    return settings

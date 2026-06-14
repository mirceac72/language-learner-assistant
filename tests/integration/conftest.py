"""Pytest configuration and fixtures for integration tests."""

import os

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires real API)",
    )


@pytest.fixture(scope="session")
def mistral_api_key():
    """Get Mistral API key from environment."""
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        pytest.skip("MISTRAL_API_KEY environment variable not set, skipping integration tests")
    return api_key


@pytest.fixture
def real_llm_client(mistral_api_key):
    """Create a real MistralLLMClient for integration tests."""
    from src.language_learner.config import get_settings
    from src.language_learner.core.llm_client import MistralLLMClient

    # Get settings for model and rate_limit
    settings = get_settings()
    return MistralLLMClient(
        api_key=mistral_api_key,
        model=settings.mistral_model,
        rate_limit=settings.llm_rate_limit,
    )

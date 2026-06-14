"""Integration tests for MistralLLMClient with real Mistral API."""

import asyncio
import time

import pytest


@pytest.mark.integration
class TestMistralLLMClientIntegration:
    """Integration tests for MistralLLMClient using real Mistral API."""

    async def test_single_generate_call(self, real_llm_client):
        """Test a single generate call with real API."""
        result = real_llm_client.generate("What is the capital of France?")

        # Verify we got a non-empty response
        assert result is not None
        assert len(result.strip()) > 0

    async def test_generate_with_custom_parameters(self, real_llm_client):
        """Test generate with custom temperature and max_tokens."""
        result = real_llm_client.generate(
            "Tell me a short joke in one sentence.",
            temperature=0.9,
            max_tokens=50
        )

        # Verify we got a non-empty response
        assert result is not None
        assert len(result.strip()) > 0

    async def test_generate_with_french_prompts(self, real_llm_client):
        """Test generate with French language prompts."""
        prompts = [
            "Traduis 'Hello, how are you?' en français",
            "Quelle est la capitale de l'Espagne?",
        ]

        # Execute all prompts sequentially
        results = [real_llm_client.generate(prompt) for prompt in prompts]

        # Verify we got responses for all prompts
        assert len(results) == len(prompts)
        assert all(result is not None for result in results)
        assert all(len(result.strip()) > 0 for result in results)

    async def test_rate_limiting_minimum_interval(self, real_llm_client):
        """Test that rate limiting enforces minimum interval between calls.
        
        With rate_limit=0.8 calls/second (default), the minimum interval
        should be at least 1.25 seconds. This test verifies that consecutive
        calls are spaced appropriately.
        """
        # First call
        start_time = time.time()
        real_llm_client.generate("What is 2+2?")
        first_call_end = time.time()
        
        # Second call
        real_llm_client.generate("What is 3+3?")
        second_call_end = time.time()
        
        # Time between start of first call and end of second call
        # should be at least 1 second (rate is 0.8/sec = 1 call per 1.25 sec)
        elapsed = second_call_end - start_time
        assert elapsed >= 1.0, f"Expected at least 1.0s between calls, got {elapsed:.2f}s"

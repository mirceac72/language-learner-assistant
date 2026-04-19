"""Vocabulary Extractor Module

This module provides functionality to extract vocabulary from web pages.
It can be used for any language by specifying the appropriate stop words.
"""

import time
from collections import Counter

import requests
from bs4 import BeautifulSoup
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

from ..config import get_settings
from ..exceptions import WebFetchError
from ..logging import get_logger
from .ner_filter import NERFilter


class VocabularyExtractor:
    """Extracts vocabulary from text content.

    This class can be used for any language by specifying the appropriate
    stop words language during initialization.
    """

    def __init__(self, language=None):
        """Initialize the vocabulary extractor.

        Args:
            language (str, optional): Language code for stop words.
                If None, uses default from configuration.
        """
        self.logger = get_logger(__name__)
        self.settings = get_settings()

        # Use provided language or default from settings
        effective_language = language or self.settings.default_language
        self.stop_words = set(stopwords.words(effective_language))

        # Initialize NER filter for named entity recognition
        self.ner_filter = NERFilter(effective_language)

        self.logger.debug(
            f"Initialized VocabularyExtractor with language: {effective_language}"
        )

    def fetch_web_page(self, url: str) -> str:
        """Fetch content from a web page with retry logic

        Args:
            url: URL to fetch

        Returns:
            HTML content of the web page

        Raises:
            WebFetchError: If there's an error fetching the web page
        """
        headers = {"User-Agent": self.settings.user_agent}
        max_retries = self.settings.web_request_max_retries
        timeout = self.settings.web_request_timeout
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.info(f"Fetching web page: {url} (attempt {attempt + 1}/{max_retries + 1})")
                response = requests.get(
                    url, headers=headers, timeout=timeout
                )
                response.raise_for_status()
                self.logger.debug(f"Successfully fetched web page: {url}")
                return response.text
            except requests.RequestException as e:
                last_exception = e
                self.logger.warning(
                    f"Error fetching web page {url} (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                
                # Only retry on transient errors (connection errors, timeouts)
                if isinstance(e, (requests.ConnectionError, requests.Timeout)) and attempt < max_retries:
                    retry_delay = timeout * (attempt + 1)  # Exponential backoff
                    self.logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    continue
                else:
                    # Don't retry for non-transient errors or if we've exhausted retries
                    self.logger.error(f"Failed to fetch web page {url}: {e}")
                    break
        
        raise WebFetchError(f"Failed to fetch web page after {max_retries + 1} attempts: {last_exception}") from last_exception

    def extract_text_from_html(self, html: str) -> str:
        """Extract text content from HTML

        Args:
            html: HTML content to extract text from

        Returns:
            Cleaned text content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text and clean it up
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = "\n".join(chunk for chunk in chunks if chunk)

        return text

    def extract_vocabulary(
        self, text: str, min_word_length: int | None = None, top_n: int | None = None
    ) -> list[tuple[str, int]]:
        """Extract vocabulary from text

        Args:
            text: Text to extract vocabulary from
            min_word_length: Minimum word length to consider
            top_n: Number of top words to return

        Returns:
            List of (word, count) tuples sorted by frequency
        """
        # Use configuration defaults if not provided
        effective_min_length = min_word_length or self.settings.min_word_length
        effective_top_n = top_n or self.settings.top_vocabulary_words

        self.logger.debug(
            f"Extracting vocabulary with min_length={effective_min_length}, "
            f"top_n={effective_top_n}"
        )

        # Identify named entities
        named_entities = self.ner_filter.get_named_entities(text)

        # Tokenize words
        words = word_tokenize(text.lower())

        # Filter words
        filtered_words = [
            word
            for word in words
            if word.isalpha()
            and len(word) >= effective_min_length
            and word not in self.stop_words
            and word not in named_entities
        ]

        # Count word frequencies
        word_counts = Counter(filtered_words)

        result = word_counts.most_common(effective_top_n)
        self.logger.info(f"Extracted {len(result)} vocabulary words from text")

        return result

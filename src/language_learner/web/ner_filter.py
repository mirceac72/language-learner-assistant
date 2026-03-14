"""
Named Entity Recognition Filter Module

This module provides NER filtering capabilities using spaCy to identify and remove
proper nouns (people, locations, organizations) from vocabulary lists.
"""


import spacy

from ..logging import get_logger


class NERFilter:
    """Named Entity Recognition Filter using spaCy"""

    def __init__(self, language: str = "french"):
        """
        Initialize NER filter with specified language

        Args:
            language: Language code (e.g., 'french', 'english')

        Raises:
            RuntimeError: If the required spaCy model is not available
        """
        self.logger = get_logger(__name__)
        self.language = language.lower()
        self.nlp = self._load_model()
        self.entities_to_filter = {"PER", "LOC", "GPE", "ORG", "FAC"}

    def _load_model(self) -> spacy.Language:
        """
        Load appropriate spaCy model based on language

        Returns:
            Loaded spaCy language model

        Raises:
            RuntimeError: If the required spaCy model is not available
        """
        # Map language codes to spaCy model names
        model_map = {
            'french': 'fr_core_news_sm',
            'english': 'en_core_web_sm',
            'german': 'de_core_news_sm',
            'spanish': 'es_core_news_sm'
        }

        model_name = model_map.get(self.language, 'fr_core_news_sm')

        try:
            return spacy.load(model_name)
        except OSError as e:
            raise RuntimeError(
                f"Required spaCy model '{model_name}' is not installed. "
            ) from e

    def get_named_entities(self, text: str) -> set[str]:
        """Extract named entities from text using NER filter

        Args:
            text: Original text to process

        Returns:
            Set of named entity words to filter out
        """
        try:
            # Process text with spaCy NER
            doc = self.nlp(text)

            # Collect all named entity tokens
            named_entities = set()
            for ent in doc.ents:
                if ent.label_ in self.entities_to_filter:
                    # Add all tokens in the entity to the exclusion set (lowercase)
                    for token in ent:
                        named_entities.add(token.text.lower())

            self.logger.debug(f"Found {len(named_entities)} named entities: {named_entities}")
            return named_entities

        except Exception as e:
            self.logger.error(f"Error in named entity extraction: {e}")
            # Return empty set if NER fails (no filtering)
            return set()



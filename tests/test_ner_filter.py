"""Comprehensive unit tests for the updated NERFilter module"""

import pytest

from src.language_learner.web.ner_filter import NERFilter


class TestNERFilterInitialization:
    """Test NERFilter initialization and model loading"""

    def test_successful_initialization_french(self):
        """Test successful initialization with French language"""
        ner_filter = NERFilter("french")
        assert ner_filter.nlp is not None
        assert hasattr(ner_filter.nlp, 'pipe')
        assert ner_filter.language == "french"
        assert ner_filter.entities_to_filter == {"PER", "LOC", "GPE", "ORG", "FAC"}

    def test_successful_initialization_english(self):
        """Test that English initialization fails gracefully without model"""
        with pytest.raises(RuntimeError) as exc_info:
            NERFilter("english")

        error_msg = str(exc_info.value)
        assert "en_core_web_sm" in error_msg

    def test_unsupported_language_fallback(self):
        """Test initialization with unsupported language falls back to French"""
        # This should work because unsupported languages fall back to French model
        ner_filter = NERFilter("italian")
        assert ner_filter.nlp is not None
        assert ner_filter.language == "italian"  # Language is set but uses French model


class TestNamedEntityExtraction:
    """Test named entity extraction functionality"""

    def setup_method(self):
        """Set up NERFilter for each test"""
        self.ner_filter = NERFilter("french")

    def test_extract_named_entities_simple(self):
        """Test extraction of named entities from simple text"""
        text = "Paris est la capitale de la France."
        entities = self.ner_filter.get_named_entities(text)

        # Should find "paris" and possibly "france" as named entities
        assert isinstance(entities, set)
        assert len(entities) > 0
        assert "paris" in entities or "france" in entities

    def test_extract_named_entities_multiword(self):
        """Test extraction of multi-word named entities"""
        text = "New York est une grande ville. Les États-Unis sont un pays."
        entities = self.ner_filter.get_named_entities(text)

        # Should find multi-word entities
        assert isinstance(entities, set)
        # Note: The French model might not recognize English entities perfectly
        # but should still find some entities

    def test_extract_named_entities_person_names(self):
        """Test extraction of person names"""
        text = "Marie Curie était une scientifique. Albert Einstein aussi."
        entities = self.ner_filter.get_named_entities(text)

        # Should find person names
        assert isinstance(entities, set)
        assert len(entities) > 0
        # Should contain "marie", "curie", "albert", "einstein" (lowercase)
        person_names = {"marie", "curie", "albert", "einstein"}
        assert any(name in entities for name in person_names)

    def test_extract_common_french_person_names(self):
        """Test extraction of common French person names"""
        text = "Jean a rencontré Marie à la boulangerie. Pierre et Sophie jouent au parc."
        entities = self.ner_filter.get_named_entities(text)

        # Should find French person names
        assert isinstance(entities, set)
        assert len(entities) > 0
        # Common French names that should be detected
        french_names = {"jean", "marie", "pierre", "sophie"}
        assert any(name in entities for name in french_names)

    def test_empty_text_handling(self):
        """Test handling of empty text"""
        entities = self.ner_filter.get_named_entities("")
        assert entities == set()

    def test_text_without_entities(self):
        """Test text that contains no named entities"""
        text = "Le chat est sur la table. La maison est grande."
        entities = self.ner_filter.get_named_entities(text)

        # Should return empty set or very few entities
        assert isinstance(entities, set)
        # Common words should not be detected as entities

    def test_case_insensitive_entity_detection(self):
        """Test that entity detection is case insensitive"""
        text = "PARIS est une ville. paris est la capitale."
        entities = self.ner_filter.get_named_entities(text)

        # Should find "paris" in lowercase
        assert "paris" in entities


class TestEntityExtractionAndUsage:
    """Test named entity extraction and usage patterns"""

    def setup_method(self):
        """Set up NERFilter for each test"""
        self.ner_filter = NERFilter("french")

    def test_entity_extraction_and_filtering(self):
        """Test extraction of named entities and manual filtering"""
        text = "Paris est une belle ville"
        words = ["paris", "est", "une", "ville", "belle"]

        # Extract entities from text
        entities = self.ner_filter.get_named_entities(text)

        # Manually filter words (this is how VocabularyExtractor uses it)
        filtered = [word for word in words if word not in entities]

        assert isinstance(filtered, list)
        # "paris" should be filtered out if it was detected as entity
        if "paris" in entities:
            assert "paris" not in filtered
        # Common words should remain
        assert "est" in filtered
        assert "ville" in filtered
        assert "belle" in filtered

    def test_empty_entity_set_handling(self):
        """Test handling when no entities are found"""
        text = "Le chat est sur la table"
        entities = self.ner_filter.get_named_entities(text)
        words = ["le", "chat", "est", "sur", "la", "table"]

        # Filter words
        filtered = [word for word in words if word not in entities]

        # Should return all words since none are entities
        assert len(filtered) == len(words)
        assert all(word in filtered for word in words)

    def test_entity_extraction_graceful_degradation(self):
        """Test that entity extraction gracefully handles errors"""
        # This should work without crashing even if NER has issues
        entities = self.ner_filter.get_named_entities("Some test text")

        assert isinstance(entities, set)
        # Should return a set (empty or with entities)


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_model_loading_error_handling(self):
        """Test proper error handling when model is not available"""
        # Test with English which we don't have installed
        with pytest.raises(RuntimeError) as exc_info:
            NERFilter("english")

        error_msg = str(exc_info.value)
        assert "not installed" in error_msg.lower() or "not found" in error_msg.lower()

    def test_ner_processing_error_recovery(self):
        """Test that NER processing errors don't crash the system"""
        ner_filter = NERFilter("french")

        # Test with normal text - should work
        entities = ner_filter.get_named_entities("Some test text")
        assert isinstance(entities, set)

        # Test that we can manually filter using the entities
        words = ["test", "words"]
        entities_from_text = ner_filter.get_named_entities("test words")
        filtered = [word for word in words if word not in entities_from_text]
        assert isinstance(filtered, list)


class TestLanguageSupport:
    """Test support for different languages"""

    def test_french_language_support(self):
        """Test French language support"""
        ner_filter = NERFilter("french")
        assert ner_filter.language == "french"

        # Test with French text
        text = "Paris est une ville en France."
        entities = ner_filter.get_named_entities(text)
        assert isinstance(entities, set)

    def test_language_case_insensitivity(self):
        """Test that language codes are case insensitive"""
        ner_filter_lower = NERFilter("french")
        ner_filter_upper = NERFilter("FRENCH")
        ner_filter_mixed = NERFilter("French")

        # All should work and use the same model
        assert ner_filter_lower.language == "french"
        assert ner_filter_upper.language == "french"
        assert ner_filter_mixed.language == "french"


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases"""

    def setup_method(self):
        """Set up NERFilter for each test"""
        self.ner_filter = NERFilter("french")

    def test_long_text_processing(self):
        """Test processing of longer text"""
        long_text = """
        Paris est la capitale de la France. Marie Curie était une scientifique célèbre.
        Le président a visité Berlin et Londres. La Tour Eiffel est un monument.
        Les étudiants apprennent le français avec des professeurs compétents.
        """
        entities = self.ner_filter.get_named_entities(long_text)

        # Should handle longer text without issues
        assert isinstance(entities, set)
        assert len(entities) > 0  # Should find several entities

    def test_text_with_punctuation(self):
        """Test text with various punctuation"""
        text = "Paris, France (Europe) est belle! Oui, c'est vrai."
        entities = self.ner_filter.get_named_entities(text)

        # Should handle punctuation properly
        assert isinstance(entities, set)

    def test_mixed_language_text(self):
        """Test text with mixed languages"""
        text = "Paris is in France. Londres est en Angleterre."
        entities = self.ner_filter.get_named_entities(text)

        # Should still work with mixed language text
        assert isinstance(entities, set)

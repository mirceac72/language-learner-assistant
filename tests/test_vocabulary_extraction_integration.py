"""Integration tests for the vocabulary extraction pipeline"""

import pytest
from unittest.mock import MagicMock, patch
import requests

from src.language_learner.web.vocabulary_extractor import VocabularyExtractor
from src.language_learner.exceptions import WebFetchError


class TestVocabularyExtractionPipeline:
    """Test the complete vocabulary extraction pipeline"""

    def setup_method(self):
        """Set up for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_complete_pipeline_success(self, mock_get):
        """Test the complete pipeline from URL to vocabulary"""
        # Mock HTML response
        mock_response = MagicMock()
        mock_response.text = """
        <!DOCTYPE html>
        <html lang="fr">
            <head>
                <title>Actualités Françaises</title>
                <script>console.log("test");</script>
                <style>body { font-family: Arial; }</style>
            </head>
            <body>
                <article>
                    <h1>Le président visite la ville</h1>
                    <p>Le président a visité la capitale hier.</p>
                    <p>Il a parlé du pays et de l'Europe.</p>
                </article>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Execute complete pipeline
        html = self.extractor.fetch_web_page("http://example-news.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text)
        
        # Verify each stage
        assert html is not None
        assert len(html) > 0
        assert text is not None
        assert len(text) > 0
        assert vocabulary is not None
        assert len(vocabulary) > 0
        
        # Verify HTML tags removed
        assert "<script>" not in text
        assert "<style>" not in text
        assert "<html>" not in text
        
        # Verify we got valid vocabulary
        assert all(isinstance(item, tuple) and len(item) == 2 for item in vocabulary)
        words = [item[0] for item in vocabulary]
        counts = [item[1] for item in vocabulary]
        
        # Check that some content words are present
        # (exact words depend on NER filtering)
        assert any(len(word) >= 3 for word in words)
        assert all(count > 0 for count in counts)

    @patch('requests.get')
    def test_pipeline_with_french_content(self, mock_get):
        """Test pipeline with authentic French content"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>
                    Dans la ville de Lyon, il y a beaucoup de restaurants.
                    Les gens aiment manger des plats traditionnels.
                    Le marché est très animé le matin.
                </p>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.extractor.fetch_web_page("http://lyon-news.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text)
        
        assert len(vocabulary) > 0
        
        # Verify text contains French content
        assert "Lyon" in text or "restaurants" in text or "marché" in text

    @patch('requests.get')
    def test_pipeline_with_mixed_content(self, mock_get):
        """Test pipeline with HTML containing mixed content types"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head>
                <meta charset="UTF-8">
                <script src="analytics.js"></script>
            </head>
            <body>
                <header><h1>Titre de l'article</h1></header>
                <nav>
                    <ul>
                        <li><a href="/accueil">Accueil</a></li>
                        <li><a href="/actualites">Actualités</a></li>
                    </ul>
                </nav>
                <main>
                    <article>
                        <p>C cañón est un bon exemple de mot avec des caractères spéciaux.</p>
                        <p>1234567890</p>
                    </article>
                </main>
                <footer>© 2024</footer>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.extractor.fetch_web_page("http://mixed-content.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text)
        
        # Verify text extraction worked
        assert "Titre de l'article" in text or "exemple" in text
        
        # Verify vocabulary extraction filtered appropriately
        words = [item[0] for item in vocabulary]
        
        # Numbers should be filtered (not alphabetic)
        assert "1234567890" not in words
        
        # Short words should be filtered based on config
        assert all(len(word) >= self.extractor.settings.min_word_length for word in words)

    @patch('requests.get')
    def test_pipeline_with_different_configurations(self, mock_get):
        """Test pipeline with different configuration settings"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>
                    a bb ccc dddd eeee ffff gggg hhhh iiii jjjj
                </p>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Extract with default configuration
        html = self.extractor.fetch_web_page("http://config-test.com")
        text = self.extractor.extract_text_from_html(html)
        
        # Test with custom min_word_length
        vocabulary_strict = self.extractor.extract_vocabulary(text, min_word_length=5)
        vocabulary_lenient = self.extractor.extract_vocabulary(text, min_word_length=2)
        
        # Stricter filtering should return fewer words
        assert len(vocabulary_strict) <= len(vocabulary_lenient)
        
        # Test with custom top_n
        vocabulary_top5 = self.extractor.extract_vocabulary(text, top_n=5)
        vocabulary_top10 = self.extractor.extract_vocabulary(text, top_n=10)
        
        assert len(vocabulary_top5) <= 5
        assert len(vocabulary_top10) <= 10


class TestVocabularyToExerciseGeneration:
    """Test vocabulary extraction with exercise generation considerations"""

    def setup_method(self):
        """Set up for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_extract_unique_learnable_words(self, mock_get):
        """Test that we extract unique, learnable words suitable for exercises"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>
                    La la la. Le le le. De des du.
                    Mais la maison est belle et grande.
                    La maison a un jardin magnifique.
                </p>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.extractor.fetch_web_page("http://learnable.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text)
        
        # Should filter out stopwords like "la", "le", "de", "des", "du", "est", "et", "un", "a"
        words = [item[0] for item in vocabulary]
        
        stopwords_fr = self.extractor.stop_words
        for word in words:
            assert word not in stopwords_fr, f"Stopword '{word}' should be filtered"
        
        # Should have meaningful content words
        content_words = {"maison", "belle", "grande", "jardin", "magnifique"}
        assert any(word in content_words for word in words), \
            f"Expected some content words from {content_words}, got {words}"

    @patch('requests.get')
    def test_vocabulary_suitability_for_exercises(self, mock_get):
        """Test that extracted vocabulary is suitable for exercise generation"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>
                    J'aime étudier le français. J'apprends beaucoup.
                    Le professeur enseigne la grammaire.
                    Les étudiants lisent et écrivent.
                </p>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.extractor.fetch_web_page("http://suitable.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text, top_n=20)
        
        # Should have enough words for exercises
        assert len(vocabulary) > 0
        
        # All words should be suitable (alphabetic, not too short, not stopwords)
        words = [item[0] for item in vocabulary]
        for word in words:
            assert word.isalpha(), f"Non-alphabetic word: {word}"
            assert len(word) >= self.extractor.settings.min_word_length, \
                f"Word too short: {word}"
            assert word not in self.extractor.stop_words, \
                f"Stopword in vocabulary: {word}"

    def test_vocabulary_diversity(self):
        """Test vocabulary extraction handles diverse text content"""
        # Test with text containing diverse vocabulary
        diverse_texts = [
            # Simple text
            "Le chat est sur la table",
            # Text with repeated words
            "le chat le chat le chat el chat",
            # Text with numbers and punctuation
            "Article 1: Le début. Article 2: La suite!",
            # Text with mixed case
            "PARIS est une VILLE en FRANCE",
            # Text with special characters
            "C'est l'été! Carthage est une ancienne cité.",
            # Text with common French names
            "Jean et Marie parlent à Pierre et Sophie",
        ]
        
        for text in diverse_texts:
            result = self.extractor.extract_vocabulary(text)
            assert isinstance(result, list)
            # All results should be valid tuples
            assert all(isinstance(item, tuple) and len(item) == 2 for item in result)


class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases"""

    def setup_method(self):
        """Set up for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_large_html_document(self, mock_get):
        """Test extraction from large HTML document"""
        # Create large HTML with repeated content
        large_html = "<html><body>" + "<p>Test paragraph</p>" * 1000 + "</body></html>"
        
        mock_response = MagicMock()
        mock_response.text = large_html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        html = self.extractor.fetch_web_page("http://large.com")
        text = self.extractor.extract_text_from_html(html)
        vocabulary = self.extractor.extract_vocabulary(text)
        
        assert len(html) > 10000
        assert len(text) > 0
        assert len(vocabulary) > 0

    def test_empty_and_minimal_input(self):
        """Test with empty and minimal input"""
        test_cases = [
            ("", []),  # Empty text
            ("   ", []),  # Whitespace only
            ("le", []),  # Only stopword
            ("a b c", []),  # Only short words
        ]
        
        for text, expected in test_cases:
            result = self.extractor.extract_vocabulary(text)
            assert isinstance(result, list)

    def test_text_with_all_caps(self):
        """Test text with all uppercase letters"""
        text = "CECI EST UN TEST EN MAJUSCULES"
        result = self.extractor.extract_vocabulary(text)
        
        # All words should be lowercased in result
        words = [item[0] for item in result]
        assert all(word == word.lower() for word in words)

    def test_text_with_mixed_encoding(self):
        """Test text with special encoding and Unicode characters"""
        texts = [
            "café au lait",
            "hôtel de ville",
            "naïve approach",
            "résumé of work",
            "über everything",
        ]
        
        for text in texts:
            result = self.extractor.extract_vocabulary(text, min_word_length=3)
            assert isinstance(result, list)
            # Should handle Unicode without errors

    @patch('requests.get')
    def test_sequential_pipeline_calls(self, mock_get):
        """Test multiple sequential calls to the pipeline"""
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Test content</p></body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        urls = [
            "http://site1.com",
            "http://site2.com",
            "http://site3.com",
        ]
        
        for url in urls:
            html = self.extractor.fetch_web_page(url)
            text = self.extractor.extract_text_from_html(html)
            vocabulary = self.extractor.extract_vocabulary(text)
            
            assert html is not None
            assert text is not None
            assert vocabulary is not None
        
        # Should have made as many requests as URLs
        assert mock_get.call_count == len(urls)


class TestIntegrationWithExistingComponents:
    """Test integration with existing NER filter and configuration"""

    def setup_method(self):
        """Set up for each test"""
        self.extractor = VocabularyExtractor()

    def test_ner_filter_integration(self):
        """Test that NER filter is properly integrated"""
        text = "Paris est la capitale de la France"
        
        # Extract vocabulary
        vocabulary = self.extractor.extract_vocabulary(text)
        
        # Verify that named entities were considered
        # Paris and France should be filtered if NER works
        words = [item[0] for item in vocabulary]
        named_entities = {"paris", "france"}
        
        # If NER is working, at least one named entity should be filtered
        filtered_entities = named_entities - set(words)
        assert len(filtered_entities) > 0, \
            f"Expected NER to filter entities, but all {named_entities} were in result {words}"

    def test_custom_language_support(self):
        """Test support for custom languages"""
        # Test initialization with different languages
        languages = ["french", "english"]
        
        for lang in languages:
            try:
                extractor = VocabularyExtractor(language=lang)
                assert extractor is not None
                assert extractor.ner_filter is not None
                # May fail for English if spaCy model not installed, but NLTK should work
            except RuntimeError:
                # Expected if spaCy model not installed
                pass
        
        # French should always work (main language)
        extractor_fr = VocabularyExtractor(language="french")
        assert extractor_fr is not None

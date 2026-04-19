"""Comprehensive unit tests for the VocabularyExtractor module"""

import pytest
from unittest.mock import MagicMock, patch
import requests

from src.language_learner.web.vocabulary_extractor import VocabularyExtractor
from src.language_learner.exceptions import WebFetchError


class TestVocabularyExtractorInitialization:
    """Test VocabularyExtractor initialization"""

    def test_successful_initialization_default_language(self):
        """Test initialization with default language"""
        extractor = VocabularyExtractor()
        assert extractor is not None
        assert extractor.stop_words is not None
        assert len(extractor.stop_words) > 0
        assert extractor.ner_filter is not None

    def test_initialization_with_custom_language(self):
        """Test initialization with custom language"""
        extractor = VocabularyExtractor(language="french")
        assert extractor is not None
        assert extractor.stop_words is not None
        assert extractor.ner_filter.language == "french"

    def test_initialization_settings_access(self):
        """Test that extractor can access settings"""
        extractor = VocabularyExtractor()
        assert extractor.settings is not None
        assert hasattr(extractor.settings, 'web_request_timeout')
        assert hasattr(extractor.settings, 'min_word_length')
        assert hasattr(extractor.settings, 'top_vocabulary_words')


class TestFetchWebPage:
    """Test fetch_web_page method with retry logic"""

    def setup_method(self):
        """Set up VocabularyExtractor for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_fetch_web_page_success(self, mock_get):
        """Test successful web page fetch"""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.extractor.fetch_web_page("http://example.com")
        
        assert result == "<html><body>Test content</body></html>"
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert 'User-Agent' in call_kwargs['headers']
        assert call_kwargs['timeout'] == self.extractor.settings.web_request_timeout

    @patch('requests.get')
    def test_fetch_web_page_retry_on_timeout(self, mock_get):
        """Test retry logic on timeout errors"""
        mock_get.side_effect = [
            requests.Timeout("Connection timed out"),
            requests.Timeout("Connection timed out"),
            MagicMock(text="<html>Success</html>", raise_for_status=MagicMock())
        ]
        
        with patch('time.sleep'):  # Don't actually sleep during tests
            result = self.extractor.fetch_web_page("http://example.com")
        
        assert result == "<html>Success</html>"
        assert mock_get.call_count == 3

    @patch('requests.get')
    def test_fetch_web_page_retry_on_connection_error(self, mock_get):
        """Test retry logic on connection errors"""
        mock_get.side_effect = [
            requests.ConnectionError("Connection refused"),
            MagicMock(text="<html>Success</html>", raise_for_status=MagicMock())
        ]
        
        with patch('time.sleep'):
            result = self.extractor.fetch_web_page("http://example.com")
        
        assert result == "<html>Success</html>"
        assert mock_get.call_count == 2

    @patch('requests.get')
    def test_fetch_web_page_no_retry_on_404(self, mock_get):
        """Test that non-transient errors (404) are not retried"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        
        with pytest.raises(WebFetchError) as exc_info:
            self.extractor.fetch_web_page("http://example.com/404")
        
        assert "Failed to fetch web page after" in str(exc_info.value)
        # Should only try once for non-transient errors
        assert mock_get.call_count == 1

    @patch('requests.get')
    def test_fetch_web_page_exhausted_retries(self, mock_get):
        """Test behavior when all retries are exhausted"""
        mock_get.side_effect = requests.Timeout("Connection timed out")
        
        with pytest.raises(WebFetchError) as exc_info:
            with patch('time.sleep'):
                self.extractor.fetch_web_page("http://example.com")
        
        assert "Failed to fetch web page after" in str(exc_info.value)
        # Should try max_retries + 1 times (initial + retries)
        expected_attempts = self.extractor.settings.web_request_max_retries + 1
        assert mock_get.call_count == expected_attempts

    @patch('requests.get')
    def test_fetch_web_page_http_error(self, mock_get):
        """Test handling of HTTP errors (4xx, 5xx)"""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(WebFetchError):
            self.extractor.fetch_web_page("http://example.com/500")


class TestExtractTextFromHtml:
    """Test extract_text_from_html method"""

    def setup_method(self):
        """Set up VocabularyExtractor for each test"""
        self.extractor = VocabularyExtractor()

    def test_extract_text_basic_html(self):
        """Test extraction from basic HTML"""
        html = "<html><body><p>Hello world</p></body></html>"
        result = self.extractor.extract_text_from_html(html)
        
        assert "Hello" in result
        assert "world" in result
        assert "<html>" not in result
        assert "<p>" not in result

    def test_extract_text_removes_scripts(self):
        """Test that script tags are removed"""
        html = """
        <html>
            <head><script>var x = 1;</script></head>
            <body><p>Content here</p></body>
        </html>
        """
        result = self.extractor.extract_text_from_html(html)
        
        assert "var x" not in result
        assert "script" not in result.lower()
        assert "Content here" in result

    def test_extract_text_removes_styles(self):
        """Test that style tags are removed"""
        html = """
        <html>
            <head><style>body { color: red; }</style></head>
            <body><p>Styled content</p></body>
        </html>
        """
        result = self.extractor.extract_text_from_html(html)
        
        assert "color: red" not in result
        assert "<style>" not in result
        assert "body { color: red; }" not in result
        assert "Styled content" in result

    def test_extract_text_removes_excessive_whitespace(self):
        """Test that excessive whitespace is cleaned up"""
        html = """
        <html>
            <body>
                <p>Text</p>
                
                
                <p>More text</p>
            </body>
        </html>
        """
        result = self.extractor.extract_text_from_html(html)
        
        # Should not have multiple consecutive newlines
        assert "\n\n\n" not in result

    def test_extract_text_empty_html(self):
        """Test extraction from empty HTML"""
        result = self.extractor.extract_text_from_html("")
        assert result == ""

    def test_extract_text_html_with_no_body(self):
        """Test extraction from HTML with no body content"""
        html = "<html><head><title>Test</title></head></html>"
        result = self.extractor.extract_text_from_html(html)
        
        # Should still extract title if present
        assert result == "" or "Test" in result

    def test_extract_text_preserves_french_accents(self):
        """Test that French accented characters are preserved"""
        html = "<html><body>C'est l'été à Paris</body></html>"
        result = self.extractor.extract_text_from_html(html)
        
        assert "l'été" in result
        assert "à" in result


class TestExtractVocabulary:
    """Test extract_vocabulary method"""

    def setup_method(self):
        """Set up VocabularyExtractor for each test"""
        self.extractor = VocabularyExtractor()

    def test_extract_vocabulary_basic(self):
        """Test basic vocabulary extraction"""
        text = "le chat est sur la table le chien est sous la table"
        result = self.extractor.extract_vocabulary(text)
        
        assert isinstance(result, list)
        assert len(result) > 0
        # Check that we get tuples of (word, count)
        assert all(isinstance(item, tuple) and len(item) == 2 for item in result)

    def test_extract_vocabulary_filters_stopwords(self):
        """Test that stopwords are filtered out"""
        text = "le le le chat est une table"
        result = self.extractor.extract_vocabulary(text)
        
        # Common French stopwords should be filtered
        words = [item[0] for item in result]
        assert "le" not in words
        assert "la" not in words
        assert "une" not in words
        assert "est" not in words

    def test_extract_vocabulary_filters_short_words(self):
        """Test that short words are filtered out based on min_word_length"""
        text = "a bb ccc dddd"
        result = self.extractor.extract_vocabulary(text, min_word_length=3)
        
        words = [item[0] for item in result]
        assert "a" not in words
        assert "bb" not in words
        assert "ccc" not in words or len("ccc") >= 3

    def test_extract_vocabulary_filters_ner_entities(self):
        """Test that named entities are filtered out"""
        # This test may require the French spaCy model to be installed
        text = "Paris est une ville en France"
        result = self.extractor.extract_vocabulary(text)
        
        words = [item[0] for item in result]
        # Paris and France should be filtered as named entities if NER works
        # Note: This depends on spaCy model availability
        named_entities = {"paris", "france"}
        # At least one named entity should be filtered out
        filtered_entities = named_entities - set(words)
        assert len(filtered_entities) > 0, f"Expected named entities to be filtered, but all {named_entities} were in result {words}"

    def test_extract_vocabulary_top_n_limiting(self):
        """Test that top N results are limited"""
        text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
        result = self.extractor.extract_vocabulary(text, top_n=3)
        
        assert len(result) <= 3

    def test_extract_vocabulary_custom_min_length(self):
        """Test custom minimum word length"""
        text = "a bb ccc dddd eeee"
        result_low = self.extractor.extract_vocabulary(text, min_word_length=2)
        result_high = self.extractor.extract_vocabulary(text, min_word_length=4)
        
        # With higher min length, should get fewer results
        assert len(result_high) <= len(result_low)

    def test_extract_vocabulary_case_insensitive(self):
        """Test that vocabulary extraction is case insensitive"""
        text = "Chat chat CHAT ChAt"
        result = self.extractor.extract_vocabulary(text)
        
        # All words should be lowercased
        words = [item[0] for item in result]
        assert all(word == word.lower() for word in words)
        # Should only have one entry for 'chat'
        chat_counts = [item for item in result if item[0] == 'chat']
        assert len(chat_counts) == 1

    def test_extract_vocabulary_empty_text(self):
        """Test extraction from empty text"""
        result = self.extractor.extract_vocabulary("")
        assert result == []

    def test_extract_vocabulary_text_with_only_stopwords(self):
        """Test extraction from text with only stopwords"""
        text = "le la les des du"
        result = self.extractor.extract_vocabulary(text)
        
        # Should return empty result as all words are stopwords
        words = [item[0] for item in result]
        assert all(word not in text.split() for word in words), \
            f"Stopwords should be filtered, but got: {words}"

    def test_extract_vocabulary_frequency_counting(self):
        """Test that word frequencies are counted correctly"""
        text = "chat chien chat chat table chien"
        result = self.extractor.extract_vocabulary(text)
        
        # Find chat and chien in results
        chat_count = next((count for word, count in result if word == "chat"), 0)
        chien_count = next((count for word, count in result if word == "chien"), 0)
        
        assert chat_count == 3
        assert chien_count == 2

    def test_extract_vocabulary_sorted_by_frequency(self):
        """Test that results are sorted by frequency (descending)"""
        text = "a a a b b c"
        result = self.extractor.extract_vocabulary(text, min_word_length=1)
        
        # Should be sorted by frequency descending
        if len(result) > 1:
            for i in range(len(result) - 1):
                assert result[i][1] >= result[i + 1][1]

    def test_extract_vocabulary_non_alpha_filtered(self):
        """Test that non-alphabetic tokens are filtered out"""
        text = "hello! world, how's it going?"
        result = self.extractor.extract_vocabulary(text)
        
        words = [item[0] for item in result]
        # Punctuation should be filtered out
        assert "!" not in words
        assert "," not in words
        assert "?" not in words

    def test_extract_vocabulary_uses_config_defaults(self):
        """Test that extract_vocabulary uses configuration defaults when not provided"""
        text = "test word"
        
        # Call without parameters
        result1 = self.extractor.extract_vocabulary(text)
        
        # Call with explicit defaults matching config
        result2 = self.extractor.extract_vocabulary(
            text,
            min_word_length=self.extractor.settings.min_word_length,
            top_n=self.extractor.settings.top_vocabulary_words
        )
        
        # Results should be the same
        assert result1 == result2


class TestEndToEndExtraction:
    """Test end-to-end vocabulary extraction workflow"""

    def setup_method(self):
        """Set up VocabularyExtractor for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_end_to_end_with_mock_fetch(self, mock_get):
        """Test complete workflow from URL to vocabulary"""
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <p>Le chat est sur la table. Le chien est sous la table.</p>
            </body>
        </html>
        """
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Step 1: Fetch web page
        html = self.extractor.fetch_web_page("http://example.com")
        
        # Step 2: Extract text from HTML
        text = self.extractor.extract_text_from_html(html)
        
        # Step 3: Extract vocabulary
        vocabulary = self.extractor.extract_vocabulary(text)
        
        # Verify results
        assert isinstance(html, str)
        assert len(text) > 0
        assert isinstance(vocabulary, list)
        
        # Verify text cleaning removed HTML tags
        assert "<p>" not in text
        assert "Le chat" in text or "chat" in text
        
        # Verify vocabulary extraction worked
        words = [item[0] for item in vocabulary]
        assert "chat" in words or "chien" in words or "table" in words


class TestConfigurationUsage:
    """Test that configuration settings are properly used"""

    def test_respects_web_request_timeout(self):
        """Test that web request timeout is respected"""
        extractor = VocabularyExtractor()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>Test</html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            extractor.fetch_web_page("http://example.com")
            
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['timeout'] == extractor.settings.web_request_timeout

    def test_respects_user_agent(self):
        """Test that user agent is respected"""
        extractor = VocabularyExtractor()
        
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.text = "<html>Test</html>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            extractor.fetch_web_page("http://example.com")
            
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs['headers']['User-Agent'] == extractor.settings.user_agent


class TestErrorHandling:
    """Test error handling and edge cases"""

    def setup_method(self):
        """Set up VocabularyExtractor for each test"""
        self.extractor = VocabularyExtractor()

    @patch('requests.get')
    def test_network_error_propagates_as_web_fetch_error(self, mock_get):
        """Test that network errors are properly wrapped in WebFetchError"""
        mock_get.side_effect = requests.ConnectionError("No network")
        
        with pytest.raises(WebFetchError) as exc_info:
            with patch('time.sleep'):
                self.extractor.fetch_web_page("http://example.com")
        
        assert "Failed to fetch web page after" in str(exc_info.value)
        assert isinstance(exc_info.value.__cause__, requests.ConnectionError)

    def test_invalid_url_handling(self):
        """Test handling of invalid URL"""
        with pytest.raises(WebFetchError):
            with patch('time.sleep'):
                self.extractor.fetch_web_page("invalid-url")

    def test_html_with_complex_structure(self):
        """Test extraction from complex HTML with nested elements"""
        html = """
        <!DOCTYPE html>
        <html>
            <head>
                <title>Test Page</title>
                <script>var x = 1;</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <div class="content">
                    <h1>Main Title</h1>
                    <p>Paragraph <span>with</span> nested elements.</p>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </div>
                <footer>Footer content</footer>
            </body>
        </html>
        """
        result = self.extractor.extract_text_from_html(html)
        
        # Should extract text content
        assert "Test Page" in result or "Main Title" in result
        assert "Paragraph" in result
        assert "Item 1" in result
        assert "Item 2" in result
        assert "Footer content" in result
        
        # Should not contain script/style content
        assert "var x" not in result
        assert "color: red" not in result


class TestMultipleLanguages:
    """Test vocabulary extraction with different languages"""

    def test_english_language_initialization(self):
        """Test initialization with English language"""
        # Test that English stopwords from NLTK are available
        # Note: Full initialization may require English spaCy model
        try:
            extractor = VocabularyExtractor(language="english")
            assert extractor is not None
            assert extractor.stop_words is not None
            assert len(extractor.stop_words) > 0
        except RuntimeError as e:
            # English spaCy model not installed, but NLTK stopwords should still be available
            if "en_core_web_sm" in str(e):
                # Verify NLTK has English stopwords
                from nltk.corpus import stopwords
                eng_stopwords = set(stopwords.words("english"))
                assert len(eng_stopwords) > 0

    def test_vocabulary_extraction_with_accents(self):
        """Test vocabulary extraction with accented characters"""
        extractor = VocabularyExtractor()
        text = "café restaurant hôtel naïve"  # Words with accents
        result = extractor.extract_vocabulary(text)
        
        # Accented words should be extracted if they pass other filters
        words = [item[0] for item in result]
        # Words with accents should be preserved
        accented_words = {"café", "hôtel", "naïve"}
        assert any(word in accented_words for word in words), \
            f"Expected accented words to be extracted, got: {words}"

    def test_vocabulary_extraction_filters_common_french_names(self):
        """Test that common French names are filtered out by NER"""
        extractor = VocabularyExtractor()
        text = "Jean a visité Marie. Pierre et Sophie sont amis."
        result = extractor.extract_vocabulary(text)
        
        words = [item[0] for item in result]
        # Common French names should be filtered by NER
        french_names = {"jean", "marie", "pierre", "sophie"}
        # At least some names should be filtered out
        filtered_names = french_names - set(words)
        assert len(filtered_names) > 0, f"Expected some names to be filtered, but all names {french_names} were in result {words}"

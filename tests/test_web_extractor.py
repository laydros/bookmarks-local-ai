"""
Tests for web content extraction.
"""

import pytest
import requests
from unittest.mock import Mock, patch
from core.web_extractor import WebExtractor


class TestWebExtractor:
    """Test WebExtractor class."""

    def test_extractor_initialization(self):
        """Test WebExtractor initialization."""
        extractor = WebExtractor(timeout=15)
        assert extractor.timeout == 15
        assert "User-Agent" in extractor.headers

    @patch("requests.get")
    def test_extract_content_success(self, mock_get, mock_web_response):
        """Test successful content extraction."""
        # Mock successful response
        mock_response = Mock()
        mock_response.content = mock_web_response.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == "Test Page Title"
        assert description == "Test page description"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_extract_content_timeout(self, mock_get):
        """Test content extraction with timeout."""
        mock_get.side_effect = requests.exceptions.Timeout()

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == ""
        assert description == ""

    @patch("requests.get")
    def test_extract_content_request_error(self, mock_get):
        """Test content extraction with request error."""
        mock_get.side_effect = requests.exceptions.RequestException("Connection error")

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == ""
        assert description == ""

    @patch("requests.get")
    def test_extract_content_with_og_description(self, mock_get):
        """Test extraction with Open Graph description."""
        html_content = """
        <html>
            <head>
                <title>Test Title</title>
                <meta property="og:description" content="Open Graph description">
            </head>
        </html>
        """

        mock_response = Mock()
        mock_response.content = html_content.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == "Test Title"
        assert description == "Open Graph description"

    @patch("requests.get")
    def test_extract_content_with_twitter_description(self, mock_get):
        """Test extraction with Twitter card description."""
        html_content = """
        <html>
            <head>
                <title>Test Title</title>
                <meta name="twitter:description" content="Twitter description">
            </head>
        </html>
        """

        mock_response = Mock()
        mock_response.content = html_content.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == "Test Title"
        assert description == "Twitter description"

    @patch("requests.get")
    def test_extract_content_no_meta(self, mock_get):
        """Test extraction with no meta description."""
        html_content = """
        <html>
            <head>
                <title>Test Title</title>
            </head>
        </html>
        """

        mock_response = Mock()
        mock_response.content = html_content.encode("utf-8")
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        extractor = WebExtractor()
        title, description = extractor.extract_content("https://example.com")

        assert title == "Test Title"
        assert description == ""

    @patch("requests.head")
    def test_is_valid_url_success(self, mock_head):
        """Test URL validation with successful response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        extractor = WebExtractor()
        assert extractor.is_valid_url("https://example.com")

    @patch("requests.head")
    def test_is_valid_url_client_error(self, mock_head):
        """Test URL validation with client error."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        extractor = WebExtractor()
        assert not extractor.is_valid_url("https://example.com/nonexistent")

    @patch("requests.head")
    def test_is_valid_url_server_error(self, mock_head):
        """Test URL validation with server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        extractor = WebExtractor()
        assert not extractor.is_valid_url("https://example.com")

    def test_is_valid_url_invalid_format(self):
        """Test URL validation with invalid format."""
        extractor = WebExtractor()
        assert not extractor.is_valid_url("not-a-url")
        assert not extractor.is_valid_url("ftp://example.com")  # Missing scheme/netloc

    @patch("requests.head")
    def test_is_valid_url_exception(self, mock_head):
        """Test URL validation with exception."""
        mock_head.side_effect = requests.exceptions.RequestException()

        extractor = WebExtractor()
        assert not extractor.is_valid_url("https://example.com")

    def test_extract_domain(self):
        """Test domain extraction."""
        extractor = WebExtractor()

        assert extractor.extract_domain("https://github.com/user/repo") == "github.com"
        assert (
            extractor.extract_domain("http://subdomain.example.com")
            == "subdomain.example.com"
        )
        assert extractor.extract_domain("invalid-url") == ""
        assert extractor.extract_domain("") == ""

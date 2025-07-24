"""
Web content extraction utilities.
"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import Tuple
from urllib.parse import urlparse

from .url_utils import is_valid_url

logger = logging.getLogger(__name__)


class WebExtractor:
    """Handles extraction of content from web pages."""

    def __init__(self, timeout: int = 10):
        """
        Initialize web extractor.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) " "AppleWebKit/537.36"
            )
        }

    def extract_content(self, url: str) -> Tuple[str, str]:
        """
        Extract title and description from a webpage.

        Args:
            url: URL to extract content from

        Returns:
            Tuple of (title, description)
        """
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            title = self._extract_title(soup)
            description = self._extract_description(soup)

            return title, description

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout extracting content from {url}")
            return "", ""
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            return "", ""
        except Exception as e:
            logger.warning(f"Failed to extract content from {url}: {e}")
            return "", ""

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from soup."""
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.text.strip()
        return ""

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract description from meta tags."""
        # Try standard meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            return meta_desc["content"].strip()

        # Try Open Graph description
        og_desc = soup.find("meta", attrs={"property": "og:description"})
        if og_desc and og_desc.get("content"):
            return og_desc["content"].strip()

        # Try Twitter card description
        twitter_desc = soup.find("meta", attrs={"name": "twitter:description"})
        if twitter_desc and twitter_desc.get("content"):
            return twitter_desc["content"].strip()

        return ""

    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is valid and accessible.

        Args:
            url: URL to check

        Returns:
            True if URL is valid and accessible, False otherwise
        """
        if not is_valid_url(url):
            return False

        try:
            response = requests.head(
                url, timeout=5, headers=self.headers, allow_redirects=True
            )
            return response.status_code < 400
        except Exception:
            return False

    def extract_domain(self, url: str) -> str:
        """
        Extract domain from URL.

        Args:
            url: URL to extract domain from

        Returns:
            Domain string or empty string if invalid
        """
        try:
            return urlparse(url).netloc
        except Exception:
            return ""

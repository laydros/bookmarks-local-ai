"""
Data models and types for bookmark processing.
"""

import re
from typing import Dict, List, Optional, Union
from dataclasses import dataclass
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted.

    Args:
        url: URL string to validate

    Returns:
        True if URL is valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())

        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False

        # Check for valid scheme
        if parsed.scheme not in ["http", "https", "ftp", "ftps"]:
            return False

        # Basic domain validation - simplified
        domain = parsed.netloc.split(":")[0]  # Remove port if present

        # Domain cannot be empty or start/end with dots
        if not domain or domain.startswith(".") or domain.endswith("."):
            return False

        # Allow localhost
        if domain == "localhost":
            return True

        # Simple IP check - avoid complex regex
        ip_parts = domain.split(".")
        if len(ip_parts) == 4:
            try:
                for part in ip_parts:
                    num = int(part)
                    if not (0 <= num <= 255):
                        break
                else:
                    return True  # Valid IP
            except ValueError:
                pass  # Not an IP

        # Domain name check - must have at least one dot and reasonable characters
        if "." in domain and ".." not in domain:
            # Check for reasonable characters (letters, numbers, dots, hyphens)
            allowed_chars = set(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-"
            )
            if all(c in allowed_chars for c in domain):
                # Don't start or end with hyphen
                if not domain.startswith("-") and not domain.endswith("-"):
                    return True

        return False

    except Exception:
        return False


@dataclass
class Bookmark:
    """Represents a bookmark with flexible field support."""

    url: str
    title: str = ""
    description: str = ""
    excerpt: str = ""
    tags: List[str] = None
    bookmark_type: str = "link"
    source_file: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    @classmethod
    def from_dict(cls, data: Dict) -> "Bookmark":
        """Create Bookmark from dictionary with flexible field names."""
        url = data.get("url") or data.get("link", "")
        title = data.get("title", "")
        description = data.get("description", "")
        excerpt = data.get("excerpt", "")
        tags = data.get("tags", [])
        bookmark_type = data.get("type", "link")
        source_file = data.get("_source_file", "")

        return cls(
            url=url,
            title=title,
            description=description,
            excerpt=excerpt,
            tags=tags,
            bookmark_type=bookmark_type,
            source_file=source_file,
        )

    def to_dict(self, include_source_file: bool = False) -> Dict:
        """Convert bookmark back to dictionary with consistent field ordering."""
        # Start with base fields in preferred order
        result = {}

        # URL field (use original field name preference)
        if self.url.startswith("http"):
            result["url"] = self.url
        else:
            result["link"] = self.url

        # Title
        if self.title:
            result["title"] = self.title

        # Description/excerpt (preserve original field preference)
        if self.description:
            result["description"] = self.description
        elif self.excerpt:
            result["excerpt"] = self.excerpt

        # Tags
        if self.tags:
            result["tags"] = self.tags

        # Type
        if self.bookmark_type:
            result["type"] = self.bookmark_type

        # Source file (if requested)
        if include_source_file and self.source_file:
            result["_source_file"] = self.source_file

        return result

    @property
    def is_valid_url(self) -> bool:
        """Check if bookmark has a valid URL."""
        return is_valid_url(self.url)

    @property
    def domain(self) -> str:
        """Extract domain from URL."""
        try:
            return urlparse(self.url).netloc
        except:
            return ""

    @property
    def content_text(self) -> str:
        """Get the main content text (description or excerpt)."""
        return self.description or self.excerpt

    @property
    def is_enriched(self) -> bool:
        """Check if bookmark has both content and tags."""
        return bool(self.content_text and self.tags)

    @property
    def search_text(self) -> str:
        """Get text suitable for searching/embedding."""
        parts = [self.title]
        if self.content_text:
            parts.append(self.content_text)
        if self.tags:
            parts.append(" ".join(self.tags))
        return " ".join(filter(None, parts))


@dataclass
class SimilarBookmark:
    """Represents a similar bookmark from vector search."""

    bookmark: Bookmark
    similarity_score: float
    content: str

    def __str__(self) -> str:
        return f"{self.bookmark.title} (score: {self.similarity_score:.3f})"


@dataclass
class SearchResult:
    """Results from a bookmark search."""

    query: str
    similar_bookmarks: List[SimilarBookmark]
    total_results: int

    def __str__(self) -> str:
        return f"Found {self.total_results} results for '{self.query}'"


@dataclass
class DuplicateGroup:
    """Group of potentially duplicate bookmarks."""

    bookmarks: List[Bookmark]
    similarity_score: float
    reason: str  # 'url', 'title', 'content'

    def __str__(self) -> str:
        titles = [
            b.title[:47] + "..." if len(b.title) > 50 else b.title
            for b in self.bookmarks
        ]
        return f"Duplicate group ({self.reason}): {', '.join(titles)}"

"""
Tests for data models.
"""

from core.models import Bookmark, SimilarBookmark, SearchResult, DuplicateGroup


class TestBookmark:
    """Test Bookmark model."""

    def test_bookmark_creation(self):
        """Test basic bookmark creation."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example",
            description="Test description",
            tags=["test", "example"],
        )

        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Example"
        assert bookmark.description == "Test description"
        assert bookmark.tags == ["test", "example"]
        assert bookmark.excerpt == ""

    def test_bookmark_from_dict_url_field(self):
        """Test creating bookmark from dict with 'url' field."""
        data = {
            "url": "https://example.com",
            "title": "Example",
            "description": "Test description",
            "tags": ["test"],
            "type": "link",
        }

        bookmark = Bookmark.from_dict(data)
        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Example"
        assert bookmark.description == "Test description"
        assert bookmark.bookmark_type == "link"

    def test_bookmark_from_dict_link_field(self):
        """Test creating bookmark from dict with 'link' field."""
        data = {
            "link": "https://example.com",
            "title": "Example",
            "excerpt": "Test excerpt",
            "tags": ["test"],
        }

        bookmark = Bookmark.from_dict(data)
        assert bookmark.url == "https://example.com"
        assert bookmark.excerpt == "Test excerpt"
        assert bookmark.description == ""

    def test_bookmark_to_dict(self):
        """Test converting bookmark to dict."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example",
            description="Test description",
            tags=["test"],
        )

        data = bookmark.to_dict()
        expected = {
            "url": "https://example.com",
            "title": "Example",
            "description": "Test description",
            "tags": ["test"],
            "type": "link",
        }

        assert data == expected

    def test_bookmark_to_dict_with_excerpt(self):
        """Test converting bookmark with excerpt to dict."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example",
            excerpt="Test excerpt",
            tags=["test"],
        )

        data = bookmark.to_dict()
        assert "excerpt" in data
        assert "description" not in data

    def test_bookmark_domain_property(self):
        """Test domain extraction."""
        bookmark = Bookmark(url="https://github.com/user/repo")
        assert bookmark.domain == "github.com"

        bookmark_invalid = Bookmark(url="invalid-url")
        assert bookmark_invalid.domain == ""

    def test_bookmark_content_text_property(self):
        """Test content_text property."""
        bookmark1 = Bookmark(url="https://example.com", description="Description")
        assert bookmark1.content_text == "Description"

        bookmark2 = Bookmark(url="https://example.com", excerpt="Excerpt")
        assert bookmark2.content_text == "Excerpt"

        bookmark3 = Bookmark(
            url="https://example.com", description="Desc", excerpt="Exc"
        )
        assert bookmark3.content_text == "Desc"  # Description takes precedence

    def test_bookmark_is_enriched_property(self):
        """Test is_enriched property."""
        # Enriched: has content and tags
        enriched = Bookmark(
            url="https://example.com", description="Description", tags=["test"]
        )
        assert enriched.is_enriched

        # Not enriched: missing tags
        not_enriched1 = Bookmark(url="https://example.com", description="Description")
        assert not not_enriched1.is_enriched

        # Not enriched: missing content
        not_enriched2 = Bookmark(url="https://example.com", tags=["test"])
        assert not not_enriched2.is_enriched

    def test_bookmark_search_text_property(self):
        """Test search_text property."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Title",
            description="Example description",
            tags=["tag1", "tag2"],
        )

        expected = "Example Title Example description tag1 tag2"
        assert bookmark.search_text == expected

    def test_bookmark_defaults(self):
        """Test bookmark with minimal data."""
        bookmark = Bookmark(url="https://example.com")

        assert bookmark.title == ""
        assert bookmark.description == ""
        assert bookmark.excerpt == ""
        assert bookmark.tags == []
        assert bookmark.bookmark_type == "link"
        assert bookmark.source_file == ""


class TestSimilarBookmark:
    """Test SimilarBookmark model."""

    def test_similar_bookmark_creation(self):
        """Test SimilarBookmark creation."""
        bookmark = Bookmark(url="https://example.com", title="Example")
        similar = SimilarBookmark(
            bookmark=bookmark, similarity_score=0.95, content="Example content"
        )

        assert similar.bookmark == bookmark
        assert similar.similarity_score == 0.95
        assert similar.content == "Example content"

    def test_similar_bookmark_str(self):
        """Test SimilarBookmark string representation."""
        bookmark = Bookmark(url="https://example.com", title="Example")
        similar = SimilarBookmark(
            bookmark=bookmark, similarity_score=0.95, content="Content"
        )

        assert str(similar) == "Example (score: 0.950)"


class TestSearchResult:
    """Test SearchResult model."""

    def test_search_result_creation(self):
        """Test SearchResult creation."""
        bookmark = Bookmark(url="https://example.com", title="Example")
        similar = SimilarBookmark(
            bookmark=bookmark, similarity_score=0.95, content="Content"
        )

        result = SearchResult(
            query="test query", similar_bookmarks=[similar], total_results=1
        )

        assert result.query == "test query"
        assert len(result.similar_bookmarks) == 1
        assert result.total_results == 1

    def test_search_result_str(self):
        """Test SearchResult string representation."""
        result = SearchResult(query="test", similar_bookmarks=[], total_results=5)

        assert str(result) == "Found 5 results for 'test'"


class TestDuplicateGroup:
    """Test DuplicateGroup model."""

    def test_duplicate_group_creation(self):
        """Test DuplicateGroup creation."""
        bookmark1 = Bookmark(url="https://example.com", title="Example 1")
        bookmark2 = Bookmark(url="https://example.com", title="Example 2")

        group = DuplicateGroup(
            bookmarks=[bookmark1, bookmark2], similarity_score=1.0, reason="url"
        )

        assert len(group.bookmarks) == 2
        assert group.similarity_score == 1.0
        assert group.reason == "url"

    def test_duplicate_group_str(self):
        """Test DuplicateGroup string representation."""
        bookmark1 = Bookmark(url="https://example.com", title="Short")
        bookmark2 = Bookmark(
            url="https://example.com",
            title=(
                "Very long title that should be truncated because it exceeds "
                "fifty characters"
            ),
        )

        group = DuplicateGroup(
            bookmarks=[bookmark1, bookmark2], similarity_score=1.0, reason="title"
        )

        str_repr = str(group)
        assert "Duplicate group (title):" in str_repr
        assert "Short" in str_repr
        assert "Very long title that should be truncated becaus..." in str_repr

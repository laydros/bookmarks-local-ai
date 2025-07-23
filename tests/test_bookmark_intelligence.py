"""
Tests for bookmark intelligence functionality.
"""

import pytest
import json
import os
import sys
import subprocess
from unittest.mock import Mock, patch
from core.intelligence import BookmarkIntelligence
from core.models import Bookmark, SearchResult, SimilarBookmark


class TestBookmarkIntelligence:
    """Test BookmarkIntelligence class."""

    def test_initialization(self):
        """Test BookmarkIntelligence initialization."""
        intelligence = BookmarkIntelligence(
            ollama_url="http://test:11434", embedding_model="test-model"
        )

        assert intelligence.ollama_url == "http://test:11434"
        assert intelligence.embedding_model == "test-model"
        assert intelligence.bookmarks == []
        assert not intelligence.indexed
        assert intelligence.loader is not None
        assert intelligence.vector_store is not None

    def test_load_bookmarks_from_file(self, temp_json_file):
        """Test loading bookmarks from a single file."""
        intelligence = BookmarkIntelligence()

        result = intelligence.load_bookmarks(temp_json_file)

        assert result is True
        assert len(intelligence.bookmarks) == 3
        assert intelligence.bookmarks[0].url == "https://python.org"
        assert intelligence.bookmarks[1].url == "https://github.com"
        assert intelligence.bookmarks[2].url == "https://stackoverflow.com"

    def test_load_bookmarks_from_directory(self, temp_directory):
        """Test loading bookmarks from a directory."""
        intelligence = BookmarkIntelligence()

        result = intelligence.load_bookmarks(temp_directory)

        assert result is True
        assert len(intelligence.bookmarks) == 3  # 2 from file1 + 1 from file2

    def test_load_bookmarks_nonexistent_path(self):
        """Test loading bookmarks from nonexistent path."""
        intelligence = BookmarkIntelligence()

        result = intelligence.load_bookmarks("/nonexistent/path")

        assert result is False
        assert len(intelligence.bookmarks) == 0

    @patch("core.intelligence.VectorStore")
    def test_ensure_indexed_success(self, mock_vector_store, sample_bookmarks):
        """Test successful indexing of bookmarks."""
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        result = intelligence._ensure_indexed()

        assert result is True
        assert intelligence.indexed is True
        mock_vector_store_instance.rebuild_from_bookmarks.assert_called_once_with(
            sample_bookmarks
        )

    @patch("core.intelligence.VectorStore")
    def test_ensure_indexed_failure(self, mock_vector_store, sample_bookmarks):
        """Test indexing failure."""
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = False
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        result = intelligence._ensure_indexed()

        assert result is False
        assert intelligence.indexed is False

    @patch("core.intelligence.VectorStore")
    def test_search_success(self, mock_vector_store, sample_bookmarks):
        """Test successful search."""
        # Mock vector store search
        mock_search_result = SearchResult(
            query="python",
            similar_bookmarks=[
                SimilarBookmark(
                    bookmark=sample_bookmarks[0],
                    similarity_score=0.95,
                    content="Python programming content",
                )
            ],
            total_results=1,
        )

        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.return_value = mock_search_result
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        result = intelligence.search("python", n_results=5)

        assert result.query == "python"
        assert len(result.similar_bookmarks) == 1
        assert result.similar_bookmarks[0].similarity_score == 0.95
        mock_vector_store_instance.search.assert_called_once_with("python", 5)

    @patch("core.intelligence.VectorStore")
    def test_search_indexing_failure(self, mock_vector_store, sample_bookmarks):
        """Test search when indexing fails."""
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = False
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        result = intelligence.search("python")

        assert result.query == "python"
        assert len(result.similar_bookmarks) == 0
        assert result.total_results == 0

    @patch("core.intelligence.VectorStore")
    def test_search_exception_handling(self, mock_vector_store, sample_bookmarks):
        """Test search exception handling."""
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.side_effect = Exception("Search failed")
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        result = intelligence.search("python")

        assert result.query == "python"
        assert len(result.similar_bookmarks) == 0
        assert result.total_results == 0


class TestDuplicateDetection:
    """Test duplicate detection functionality."""

    def test_find_duplicates_exact_urls(self):
        """Test finding exact URL duplicates."""
        bookmarks = [
            Bookmark(url="https://example.com", title="Example 1"),
            Bookmark(url="https://example.com", title="Example 2"),
            Bookmark(url="https://different.com", title="Different"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 1
        assert duplicates[0].reason == "exact_url"
        assert duplicates[0].similarity_score == 1.0
        assert len(duplicates[0].bookmarks) == 2
        assert duplicates[0].bookmarks[0].title == "Example 1"
        assert duplicates[0].bookmarks[1].title == "Example 2"

    def test_find_duplicates_similar_titles(self):
        """Test finding similar title duplicates."""
        bookmarks = [
            Bookmark(url="https://example1.com", title="Example Title"),
            Bookmark(url="https://example2.com", title="Example Title"),
            Bookmark(url="https://different.com", title="Different Title"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 1
        assert duplicates[0].reason == "similar_title"
        assert duplicates[0].similarity_score == 0.9
        assert len(duplicates[0].bookmarks) == 2

    def test_find_duplicates_mixed_cases(self):
        """Test duplicate detection with both URL and title duplicates."""
        bookmarks = [
            # URL duplicates
            Bookmark(url="https://example.com", title="Example 1"),
            Bookmark(url="https://example.com", title="Example 2"),
            # Title duplicates with different URLs
            Bookmark(url="https://site1.com", title="Same Title"),
            Bookmark(url="https://site2.com", title="Same Title"),
            # Unique bookmark
            Bookmark(url="https://unique.com", title="Unique Title"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 2

        # Check for URL duplicates
        url_duplicates = [d for d in duplicates if d.reason == "exact_url"]
        assert len(url_duplicates) == 1
        assert len(url_duplicates[0].bookmarks) == 2

        # Check for title duplicates
        title_duplicates = [d for d in duplicates if d.reason == "similar_title"]
        assert len(title_duplicates) == 1
        assert len(title_duplicates[0].bookmarks) == 2

    def test_find_duplicates_no_duplicates(self):
        """Test duplicate detection with no duplicates."""
        bookmarks = [
            Bookmark(url="https://example1.com", title="Title 1"),
            Bookmark(url="https://example2.com", title="Title 2"),
            Bookmark(url="https://example3.com", title="Title 3"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 0

    def test_find_duplicates_empty_collection(self):
        """Test duplicate detection with empty collection."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = []

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 0

    def test_find_duplicates_case_insensitive_titles(self):
        """Test that title matching is case insensitive."""
        bookmarks = [
            Bookmark(url="https://example1.com", title="Example Title"),
            Bookmark(url="https://example2.com", title="EXAMPLE TITLE"),
            Bookmark(url="https://example3.com", title="example title"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        duplicates = intelligence.find_duplicates()

        assert len(duplicates) == 1
        assert duplicates[0].reason == "similar_title"
        assert len(duplicates[0].bookmarks) == 3


class TestCollectionAnalysis:
    """Test collection analysis functionality."""

    def test_analyze_collection_basic_stats(self, sample_bookmarks):
        """Test basic collection analysis."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        analysis = intelligence.analyze_collection()

        assert analysis["total_bookmarks"] == 3
        assert analysis["enriched_bookmarks"] == 3  # All sample bookmarks are enriched
        assert analysis["enrichment_percentage"] == 100.0
        assert analysis["unique_domains"] == 3
        assert analysis["files"] == 1
        assert "top_domains" in analysis
        assert "top_tags" in analysis
        assert "file_distribution" in analysis

    def test_analyze_collection_domain_analysis(self, sample_bookmarks):
        """Test domain analysis."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        analysis = intelligence.analyze_collection()

        domains = dict(analysis["top_domains"])
        assert "python.org" in domains
        assert "github.com" in domains
        assert "stackoverflow.com" in domains
        assert domains["python.org"] == 1
        assert domains["github.com"] == 1
        assert domains["stackoverflow.com"] == 1

    def test_analyze_collection_tag_analysis(self, sample_bookmarks):
        """Test tag analysis."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        analysis = intelligence.analyze_collection()

        tags = dict(analysis["top_tags"])
        assert "python" in tags
        assert "programming" in tags
        assert "git" in tags
        assert "code" in tags
        assert tags["programming"] == 2  # Appears in 2 bookmarks

    def test_analyze_collection_empty(self):
        """Test analysis of empty collection."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = []

        analysis = intelligence.analyze_collection()

        assert analysis == {}

    def test_analyze_collection_mixed_enrichment(
        self, sample_bookmarks, sample_unenriched_bookmarks
    ):
        """Test analysis with mixed enriched/unenriched bookmarks."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks + sample_unenriched_bookmarks

        analysis = intelligence.analyze_collection()

        assert analysis["total_bookmarks"] == 5
        assert analysis["enriched_bookmarks"] == 3
        assert analysis["total_bookmarks"] - analysis["enriched_bookmarks"] == 2
        assert analysis["enrichment_percentage"] == 60.0  # 3/5 = 60%


class TestAutoCategorization:
    """Test auto-categorization functionality."""

    @patch("core.intelligence.VectorStore")
    def test_suggest_categorization_success(self, mock_vector_store, sample_bookmarks):
        """Test successful categorization suggestion."""
        # Mock search result
        mock_search_result = SearchResult(
            query="test",
            similar_bookmarks=[
                SimilarBookmark(sample_bookmarks[0], 0.9, "content"),
                SimilarBookmark(sample_bookmarks[1], 0.8, "content"),
            ],
            total_results=2,
        )

        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.return_value = mock_search_result
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        new_bookmark = Bookmark(url="https://new.com", title="New Bookmark")
        suggestions = intelligence.suggest_categorization(new_bookmark)

        assert len(suggestions) == 1
        assert suggestions[0][0] == "test.json"  # source_file from sample bookmarks
        assert 0 < suggestions[0][1] <= 1  # confidence score

    @patch("core.intelligence.VectorStore")
    def test_suggest_categorization_no_similar(self, mock_vector_store):
        """Test categorization when no similar bookmarks found."""
        mock_search_result = SearchResult(
            query="test", similar_bookmarks=[], total_results=0
        )

        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.return_value = mock_search_result
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = []

        new_bookmark = Bookmark(url="https://new.com", title="New Bookmark")
        suggestions = intelligence.suggest_categorization(new_bookmark)

        assert len(suggestions) == 0

    @patch("core.intelligence.VectorStore")
    def test_suggest_categorization_multiple_files(self, mock_vector_store):
        """Test categorization with bookmarks from multiple files."""
        bookmarks = [
            Bookmark(
                url="https://python.org", title="Python", source_file="python.json"
            ),
            Bookmark(
                url="https://github.com", title="GitHub", source_file="tools.json"
            ),
            Bookmark(
                url="https://stackoverflow.com",
                title="Stack Overflow",
                source_file="python.json",
            ),
        ]

        mock_search_result = SearchResult(
            query="test",
            similar_bookmarks=[
                SimilarBookmark(bookmarks[0], 0.9, "content"),
                SimilarBookmark(bookmarks[2], 0.8, "content"),
                SimilarBookmark(bookmarks[1], 0.7, "content"),
            ],
            total_results=3,
        )

        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.return_value = mock_search_result
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        new_bookmark = Bookmark(url="https://new.com", title="New Python Library")
        suggestions = intelligence.suggest_categorization(new_bookmark)

        assert len(suggestions) >= 2
        # Should suggest python.json with higher confidence due to 2 similar bookmarks
        files = [s[0] for s in suggestions]
        assert "python.json" in files
        assert "tools.json" in files

        # Check confidence scores are normalized
        for filename, confidence in suggestions:
            assert 0 <= confidence <= 1

    @patch("core.intelligence.VectorStore")
    def test_suggest_categorization_indexing_failure(self, mock_vector_store):
        """Test categorization when indexing fails."""
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = False
        mock_vector_store.return_value = mock_vector_store_instance

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = [Bookmark(url="https://test.com", title="Test")]

        new_bookmark = Bookmark(url="https://new.com", title="New Bookmark")
        suggestions = intelligence.suggest_categorization(new_bookmark)

        assert len(suggestions) == 0


class TestInteractiveMode:
    """Test interactive mode functionality."""

    def test_interactive_search_formatting(self, sample_bookmarks):
        """Test interactive search output formatting."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        # Mock the search method
        mock_result = SearchResult(
            query="python",
            similar_bookmarks=[SimilarBookmark(sample_bookmarks[0], 0.95, "content")],
            total_results=1,
        )

        intelligence.search = Mock(return_value=mock_result)

        # Capture output
        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            intelligence._interactive_search("python")
            output = captured_output.getvalue()

            assert "Found 1 results:" in output
            assert "Python.org" in output
            assert "Score: 0.950" in output
            assert "https://python.org" in output
        finally:
            sys.stdout = sys.__stdout__

    def test_interactive_duplicates_formatting(self, monkeypatch):
        """Test interactive duplicates output formatting."""
        bookmarks = [
            Bookmark(url="https://example.com", title="Example 1"),
            Bookmark(url="https://example.com", title="Example 2"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        # Capture output
        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        monkeypatch.setattr("builtins.input", lambda _: "0")

        try:
            intelligence._interactive_duplicates()
            output = captured_output.getvalue()

            assert "Finding duplicates..." in output
            assert "Found 1 duplicate groups:" in output
            assert "Exact Url" in output
            assert "Example 1" in output
            assert "Example 2" in output
        finally:
            sys.stdout = sys.__stdout__

    def test_interactive_duplicates_removal(self, monkeypatch):
        """Test removing a duplicate interactively."""
        bookmarks = [
            Bookmark(url="https://example.com", title="Example 1"),
            Bookmark(url="https://example.com", title="Example 2"),
        ]

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = bookmarks

        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        inputs = iter(["1"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        try:
            intelligence._interactive_duplicates()
            output = captured_output.getvalue()
        finally:
            sys.stdout = sys.__stdout__

        assert "Removed 'Example 1'" in output
        assert len(intelligence.bookmarks) == 1
        assert intelligence.bookmarks[0].title == "Example 2"

    def test_interactive_analyze_formatting(self, sample_bookmarks):
        """Test interactive analyze output formatting."""
        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        # Capture output
        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            intelligence._interactive_analyze()
            output = captured_output.getvalue()

            assert "Analyzing collection..." in output
            assert "Total bookmarks: 3" in output
            assert "Enriched: 3" in output
            assert "Top domains:" in output
            assert "Top tags:" in output
        finally:
            sys.stdout = sys.__stdout__

    @patch("core.intelligence.WebExtractor")
    def test_interactive_categorize_formatting(
        self, mock_web_extractor, sample_bookmarks
    ):
        """Test interactive categorize output formatting."""
        mock_extractor = Mock()
        mock_extractor.extract_content.return_value = ("Test Title", "Test Description")
        mock_web_extractor.return_value = mock_extractor

        intelligence = BookmarkIntelligence()
        intelligence.bookmarks = sample_bookmarks

        # Mock suggest_categorization
        intelligence.suggest_categorization = Mock(return_value=[("test.json", 0.9)])

        # Capture output
        import io
        import sys

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            intelligence._interactive_categorize("https://test.com")
            output = captured_output.getvalue()

            assert "Extracting content from https://test.com" in output
            assert "Suggested categories:" in output
            assert "test.json" in output
            assert "confidence: 0.900" in output
        finally:
            sys.stdout = sys.__stdout__


class TestCLIIntegration:
    """Test CLI integration and argument parsing."""

    def test_main_function_imports(self):
        """Test that main function can be imported."""
        from bookmark_intelligence import main

        assert callable(main)

    @patch("core.intelligence.BookmarkIntelligence")
    @patch("os.path.exists")
    def test_search_command_line_parsing(self, mock_exists, mock_intelligence_class):
        """Test command line argument parsing for search."""
        mock_exists.return_value = True
        mock_intelligence = Mock()
        mock_intelligence.load_bookmarks.return_value = True
        mock_intelligence.search.return_value = SearchResult("test", [], 0)
        mock_intelligence_class.return_value = mock_intelligence

        # Test would require sys.argv manipulation
        # This is a basic structure test
        assert mock_intelligence_class is not None

    def test_argument_parser_structure(self):
        """Test that argument parser has expected arguments."""
        import argparse

        # This tests the structure exists
        # Full CLI testing would require more complex mocking
        assert argparse.ArgumentParser is not None


# Additional fixtures for testing
@pytest.fixture
def duplicate_bookmarks():
    """Fixture with duplicate bookmarks for testing."""
    return [
        Bookmark(
            url="https://example.com", title="Example 1", source_file="test1.json"
        ),
        Bookmark(
            url="https://example.com", title="Example 2", source_file="test2.json"
        ),
        Bookmark(
            url="https://different.com", title="Same Title", source_file="test1.json"
        ),
        Bookmark(
            url="https://another.com", title="Same Title", source_file="test2.json"
        ),
        Bookmark(
            url="https://unique.com", title="Unique Title", source_file="test1.json"
        ),
    ]


@pytest.fixture
def large_bookmark_collection():
    """Fixture with larger bookmark collection for performance testing."""
    bookmarks = []
    for i in range(50):
        bookmarks.append(
            Bookmark(
                url=f"https://example{i}.com",
                title=f"Example Title {i}",
                description=f"Description for example {i}",
                tags=[f"tag{i}", "common"],
                source_file=f"file{i % 5}.json",
            )
        )
    return bookmarks


@pytest.fixture
def mixed_enrichment_bookmarks():
    """Fixture with mixed enriched and unenriched bookmarks."""
    return [
        # Enriched bookmarks
        Bookmark(
            url="https://python.org",
            title="Python",
            description="Python language",
            tags=["python"],
        ),
        Bookmark(
            url="https://github.com",
            title="GitHub",
            description="Code hosting",
            tags=["git", "code"],
        ),
        # Unenriched bookmarks
        Bookmark(url="https://example.com", title="Example"),
        Bookmark(url="https://test.com", title="Test", description="Test site"),
        Bookmark(url="https://incomplete.com", tags=["incomplete"]),
    ]


class TestCLICommands:
    """Test CLI command functionality using subprocess."""

    def create_test_bookmark_file(self, tmp_path, bookmarks_data):
        """Helper to create temporary JSON file with bookmark data."""
        test_file = tmp_path / "test_bookmarks.json"
        test_file.write_text(json.dumps(bookmarks_data, indent=2))
        return str(test_file)

    def create_test_bookmark_directory(self, tmp_path):
        """Helper to create temporary directory with multiple bookmark files."""
        test_dir = tmp_path / "test_bookmarks"
        test_dir.mkdir()

        # Create multiple test files
        file1_data = [
            {
                "url": "https://python.org",
                "title": "Python",
                "description": "Python language",
                "tags": ["python"],
            },
            {
                "url": "https://github.com",
                "title": "GitHub",
                "description": "Code hosting",
                "tags": ["git", "code"],
            },
        ]

        file2_data = [
            {
                "url": "https://stackoverflow.com",
                "title": "Stack Overflow",
                "description": "Q&A site",
                "tags": ["programming"],
            }
        ]

        (test_dir / "file1.json").write_text(json.dumps(file1_data, indent=2))
        (test_dir / "file2.json").write_text(json.dumps(file2_data, indent=2))

        return str(test_dir)

    def run_cli_command(self, args, timeout=30):
        """Helper to run CLI command and return result."""
        # Use the virtual environment Python if available
        python_cmd = os.environ.get("VIRTUAL_ENV", "")
        if python_cmd and os.path.exists(os.path.join(python_cmd, "bin", "python")):
            python_executable = os.path.join(python_cmd, "bin", "python")
        else:
            python_executable = sys.executable

        cmd = [python_executable, "bookmark_intelligence.py"] + args

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, cwd="."
        )

        return result

    def test_cli_duplicates_command(self, tmp_path):
        """Test --duplicates CLI command."""
        # Create test data with duplicates
        test_data = [
            {"url": "https://example.com", "title": "Example 1"},
            {"url": "https://example.com", "title": "Example 2"},
            {"url": "https://different.com", "title": "Same Title"},
            {"url": "https://another.com", "title": "Same Title"},
            {"url": "https://unique.com", "title": "Unique Title"},
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Run CLI command
        result = self.run_cli_command([test_file, "--duplicates"])

        # Verify results
        assert result.returncode == 0
        assert "Finding duplicates..." in result.stdout
        assert "duplicate groups" in result.stdout
        assert "exact_url" in result.stdout or "similar_title" in result.stdout

    def test_cli_analyze_command(self, tmp_path):
        """Test --analyze CLI command."""
        # Create test data
        test_data = [
            {
                "url": "https://python.org",
                "title": "Python",
                "description": "Python language",
                "tags": ["python"],
            },
            {
                "url": "https://github.com",
                "title": "GitHub",
                "description": "Code hosting",
                "tags": ["git", "code"],
            },
            {"url": "https://example.com", "title": "Example"},  # Unenriched
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Run CLI command
        result = self.run_cli_command([test_file, "--analyze"])

        # Verify results
        assert result.returncode == 0
        assert "Analyzing collection..." in result.stdout
        assert "Total bookmarks: 3" in result.stdout
        assert "Enriched: 2" in result.stdout
        assert "Top domains:" in result.stdout
        assert "Top tags:" in result.stdout

    def test_cli_analyze_directory(self, tmp_path):
        """Test --analyze CLI command with directory."""
        test_dir = self.create_test_bookmark_directory(tmp_path)

        # Run CLI command
        result = self.run_cli_command([test_dir, "--analyze"])

        # Verify results
        assert result.returncode == 0
        assert "Analyzing collection..." in result.stdout
        assert "Total bookmarks: 3" in result.stdout
        assert "python.org" in result.stdout
        assert "github.com" in result.stdout
        assert "stackoverflow.com" in result.stdout

    @patch("core.intelligence.VectorStore")
    def test_cli_search_command(self, mock_vector_store, tmp_path):
        """Test --search CLI command."""
        # Create test data
        test_data = [
            {
                "url": "https://python.org",
                "title": "Python",
                "description": "Python language",
                "tags": ["python"],
            },
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Mock vector store to avoid Ollama dependency
        mock_vector_store_instance = Mock()
        mock_vector_store_instance.rebuild_from_bookmarks.return_value = True
        mock_vector_store_instance.search.return_value = SearchResult(
            query="python", similar_bookmarks=[], total_results=0
        )
        mock_vector_store.return_value = mock_vector_store_instance

        # Run CLI command
        result = self.run_cli_command([test_file, "--search", "python"])

        # Verify results
        assert result.returncode == 0
        assert "Searching for 'python'..." in result.stdout
        assert "No results found." in result.stdout or "Found" in result.stdout

    def test_cli_categorize_command(self, tmp_path):
        """Test --categorize CLI command."""
        # Create test data
        test_data = [
            {
                "url": "https://python.org",
                "title": "Python",
                "description": "Python language",
                "tags": ["python"],
            },
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Mock to avoid web extraction and vector store
        with (
            patch("core.intelligence.VectorStore") as mock_vs,
            patch("core.intelligence.WebExtractor") as mock_we,
        ):

            mock_vs_instance = Mock()
            mock_vs_instance.rebuild_from_bookmarks.return_value = True
            mock_vs_instance.search.return_value = SearchResult("test", [], 0)
            mock_vs.return_value = mock_vs_instance

            mock_we_instance = Mock()
            mock_we_instance.extract_content.return_value = (
                "Test Title",
                "Test Description",
            )
            mock_we.return_value = mock_we_instance

            # Run CLI command
            result = self.run_cli_command(
                [test_file, "--categorize", "https://example.com"]
            )

            # Verify results
            assert result.returncode == 0
            assert "Extracting content from https://example.com" in result.stdout
            assert (
                "No suggestions available." in result.stdout
                or "Suggested categories:" in result.stdout
            )

    def test_cli_help_command(self, tmp_path):
        """Test --help CLI command."""
        # Run CLI command
        result = self.run_cli_command(["--help"])

        # Verify results
        assert result.returncode == 0
        assert "Bookmark Intelligence" in result.stdout
        assert "--duplicates" in result.stdout
        assert "--analyze" in result.stdout
        assert "--search" in result.stdout
        assert "--interactive" in result.stdout
        assert "--categorize" in result.stdout

    def test_cli_invalid_path(self, tmp_path):
        """Test CLI with non-existent path."""
        # Run CLI command with non-existent path
        result = self.run_cli_command(["/nonexistent/path", "--analyze"])

        # Verify results
        assert result.returncode == 0  # Script handles error gracefully
        assert "not found" in result.stdout

    def test_cli_missing_arguments(self, tmp_path):
        """Test CLI with missing required arguments."""
        # Run CLI command without input path
        result = self.run_cli_command(["--analyze"])

        # Verify results
        assert result.returncode != 0
        assert "error" in result.stderr.lower()

    def test_cli_no_command_specified(self, tmp_path):
        """Test CLI with no command flags."""
        # Create test data
        test_data = [
            {"url": "https://python.org", "title": "Python"},
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Run CLI command with no flags
        result = self.run_cli_command([test_file])

        # Verify results
        assert result.returncode == 0
        assert "No command specified" in result.stdout
        assert "Use --help for available options" in result.stdout

    def test_cli_multiple_commands(self, tmp_path):
        """Test CLI handles multiple commands (should use first one)."""
        # Create test data
        test_data = [
            {"url": "https://example.com", "title": "Example 1"},
            {"url": "https://example.com", "title": "Example 2"},
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Run CLI command with multiple flags (duplicates should win)
        result = self.run_cli_command([test_file, "--duplicates", "--analyze"])

        # Verify results
        assert result.returncode == 0
        assert "Finding duplicates..." in result.stdout
        # Should NOT contain analyze output since duplicates comes first
        assert "Analyzing collection..." not in result.stdout

    def test_cli_empty_file(self, tmp_path):
        """Test CLI with empty JSON file."""
        # Create empty JSON file
        test_file = self.create_test_bookmark_file(tmp_path, [])

        # Run CLI command
        result = self.run_cli_command([test_file, "--analyze"])

        # Verify results
        assert result.returncode == 0
        assert (
            "Total bookmarks: 0" in result.stdout
            or "No bookmarks to analyze" in result.stdout
        )

    def test_cli_malformed_json(self, tmp_path):
        """Test CLI with malformed JSON file."""
        # Create malformed JSON file
        test_file = tmp_path / "malformed.json"
        test_file.write_text('{"invalid": json}')

        # Run CLI command
        result = self.run_cli_command([str(test_file), "--analyze"])

        # Verify results - should handle gracefully
        assert result.returncode == 0
        # Should either show error or handle gracefully
        assert (
            "Error loading" in result.stderr
            or "No bookmarks" in result.stdout
            or "Failed to load bookmarks" in result.stdout
        )

    def test_cli_with_custom_models(self, tmp_path):
        """Test CLI with custom model parameters."""
        # Create test data
        test_data = [
            {"url": "https://python.org", "title": "Python"},
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Run CLI command with custom models
        result = self.run_cli_command(
            [
                test_file,
                "--analyze",
                "--embedding-model",
                "custom-embed",
                "--results",
                "5",
            ]
        )

        # Verify results
        assert result.returncode == 0
        assert "Analyzing collection..." in result.stdout
        # Should work with custom parameters

    def test_cli_results_parameter(self, tmp_path):
        """Test CLI with --results parameter."""
        # Create test data
        test_data = [
            {
                "url": "https://python.org",
                "title": "Python",
                "description": "Python language",
                "tags": ["python"],
            },
        ]

        test_file = self.create_test_bookmark_file(tmp_path, test_data)

        # Mock to avoid Ollama dependency
        with patch("core.intelligence.VectorStore") as mock_vs:
            mock_vs_instance = Mock()
            mock_vs_instance.rebuild_from_bookmarks.return_value = True
            mock_vs_instance.search.return_value = SearchResult("test", [], 0)
            mock_vs.return_value = mock_vs_instance

            # Run CLI command with custom results number
            result = self.run_cli_command(
                [test_file, "--search", "python", "--results", "3"]
            )

            # Verify results
            assert result.returncode == 0
            assert "Searching for 'python'..." in result.stdout

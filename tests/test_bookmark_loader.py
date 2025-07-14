"""
Tests for bookmark loader functionality.
"""

import pytest
import json
import os
from core.bookmark_loader import BookmarkLoader
from core.models import Bookmark


class TestBookmarkLoader:
    """Test BookmarkLoader class."""

    def test_load_from_file(self, temp_json_file):
        """Test loading bookmarks from a single file."""
        bookmarks = BookmarkLoader.load_from_file(temp_json_file)

        assert len(bookmarks) == 3
        assert all(isinstance(b, Bookmark) for b in bookmarks)
        assert bookmarks[0].url == "https://python.org"
        assert bookmarks[0].title == "Python.org"
        assert bookmarks[0].tags == ["python", "programming", "official"]

    def test_load_from_directory(self, temp_directory):
        """Test loading bookmarks from directory."""
        bookmarks = BookmarkLoader.load_from_directory(temp_directory)

        assert len(bookmarks) == 3
        assert all(isinstance(b, Bookmark) for b in bookmarks)

        # Check source files are set
        source_files = {b.source_file for b in bookmarks}
        assert "file1.json" in source_files
        assert "file2.json" in source_files

    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        bookmarks = BookmarkLoader.load_from_file("nonexistent.json")
        assert bookmarks == []

    def test_load_nonexistent_directory(self):
        """Test loading from nonexistent directory."""
        bookmarks = BookmarkLoader.load_from_directory("nonexistent")
        assert bookmarks == []

    def test_save_to_file(self, sample_bookmarks, tmp_path):
        """Test saving bookmarks to file."""
        output_file = tmp_path / "output.json"

        success = BookmarkLoader.save_to_file(sample_bookmarks, str(output_file))
        assert success
        assert output_file.exists()

        # Verify content
        with open(output_file) as f:
            data = json.load(f)

        assert len(data) == 3
        assert data[0]["url"] == "https://python.org"
        assert data[0]["title"] == "Python.org"

    def test_save_by_source_file(self, sample_bookmarks, tmp_path):
        """Test saving bookmarks by source file."""
        # Set different source files
        sample_bookmarks[0].source_file = "python.json"
        sample_bookmarks[1].source_file = "github.json"
        sample_bookmarks[2].source_file = "python.json"

        success = BookmarkLoader.save_by_source_file(sample_bookmarks, str(tmp_path))
        assert success

        # Check files were created
        python_file = tmp_path / "python.json"
        github_file = tmp_path / "github.json"

        assert python_file.exists()
        assert github_file.exists()

        # Verify content
        with open(python_file) as f:
            python_data = json.load(f)
        assert len(python_data) == 2  # python.org and stackoverflow

        with open(github_file) as f:
            github_data = json.load(f)
        assert len(github_data) == 1  # github

    def test_filter_enriched(self, sample_bookmarks, sample_unenriched_bookmarks):
        """Test filtering enriched bookmarks."""
        all_bookmarks = sample_bookmarks + sample_unenriched_bookmarks
        enriched = BookmarkLoader.filter_enriched(all_bookmarks)

        assert len(enriched) == 3  # Only the sample_bookmarks are enriched
        assert all(b.is_enriched for b in enriched)

    def test_filter_unenriched(self, sample_bookmarks, sample_unenriched_bookmarks):
        """Test filtering unenriched bookmarks."""
        all_bookmarks = sample_bookmarks + sample_unenriched_bookmarks
        unenriched = BookmarkLoader.filter_unenriched(all_bookmarks)

        assert len(unenriched) == 2  # Only the sample_unenriched_bookmarks
        assert all(not b.is_enriched for b in unenriched)

    def test_get_stats(self, sample_bookmarks, sample_unenriched_bookmarks):
        """Test getting bookmark statistics."""
        all_bookmarks = sample_bookmarks + sample_unenriched_bookmarks
        stats = BookmarkLoader.get_stats(all_bookmarks)

        assert stats["total"] == 5
        assert stats["enriched"] == 3
        assert stats["unenriched"] == 2
        assert stats["enrichment_percentage"] == 60.0
        assert stats["files"] == 1  # All have same source_file
        assert "file_counts" in stats
        assert "top_domains" in stats

    def test_get_stats_empty(self):
        """Test getting stats for empty list."""
        stats = BookmarkLoader.get_stats([])
        assert stats == {}

"""
Tests for enhanced bookmark enricher functionality.
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from core.config_manager import BookmarkConfig
from core.models import Bookmark, is_valid_url


class TestURLValidation:
    """Test URL validation functionality."""

    def test_valid_urls(self):
        """Test valid URL formats."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://subdomain.example.com",
            "https://example.com/path/to/page",
            "https://example.com:8080",
            "https://192.168.1.1",
            "http://localhost",
        ]

        for url in valid_urls:
            assert is_valid_url(url), f"Should be valid: {url}"

    def test_invalid_urls(self):
        """Test invalid URL formats."""
        invalid_urls = [
            "",
            None,
            "not-a-url",
            "example.com",  # Missing scheme
            "https://",  # Missing domain
            "https://.com",  # Invalid domain
            "https://example",  # No TLD
        ]

        for url in invalid_urls:
            assert not is_valid_url(url), f"Should be invalid: {url}"

    def test_bookmark_url_validation(self):
        """Test bookmark URL validation property."""
        valid_bookmark = Bookmark(url="https://example.com", title="Valid")
        invalid_bookmark = Bookmark(url="not-a-url", title="Invalid")

        assert valid_bookmark.is_valid_url
        assert not invalid_bookmark.is_valid_url


class TestBookmarkConfig:
    """Test bookmark configuration integration."""

    def test_config_creation_with_overrides(self):
        """Test configuration with command line style overrides."""
        config = BookmarkConfig.default()

        # Simulate command line overrides
        config.models.embedding = "custom-embedding"
        config.models.llm = "custom-llm"
        config.output.backup_original = False

        assert config.models.embedding == "custom-embedding"
        assert config.models.llm == "custom-llm"
        assert config.output.backup_original is False

    def test_quality_controls(self):
        """Test quality control settings."""
        config = BookmarkConfig.default()

        # Test description length controls
        assert config.quality.min_description_length == 10
        assert config.quality.max_description_length == 500

        # Test tag controls
        assert config.quality.min_tags == 1
        assert config.quality.max_tags == 10

        # Test validation flags
        assert config.quality.enable_url_validation is True
        assert config.quality.standardize_tags is True

    def test_processing_controls(self):
        """Test processing control settings."""
        config = BookmarkConfig.default()

        assert config.processing.delay_between_requests == 0.5
        assert config.processing.max_retries == 3
        assert config.processing.enable_web_extraction is True
        assert config.processing.web_extraction_timeout == 10


class TestConfigFileHandling:
    """Test configuration file operations."""

    def test_config_file_creation(self):
        """Test creating a default configuration file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            temp_path = f.name

        try:
            config = BookmarkConfig.default()
            success = config.save_to_file(temp_path)

            assert success
            assert os.path.exists(temp_path)

            # Verify file contains expected content
            with open(temp_path, "r") as f:
                content = f.read()
                assert "models:" in content
                assert "nomic-embed-text" in content
                assert "processing:" in content
                assert "quality:" in content

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_config_auto_discovery(self):
        """Test automatic configuration file discovery."""
        # This would test the load_config() function that looks for
        # config files in standard locations
        from core.config_manager import load_config

        # When no config file exists, should return defaults
        config = load_config("nonexistent_config.yaml")
        assert config.models.embedding == "nomic-embed-text"


class TestProgressTracking:
    """Test progress tracking functionality."""

    def test_progress_tracker_creation(self):
        """Test creating a progress tracker."""
        from core.progress_tracker import ProgressTracker

        tracker = ProgressTracker(
            total=100,
            description="Test processing",
            show_progress_bar=False,  # Don't show in tests
        )

        assert tracker.total == 100
        assert tracker.completed == 0
        assert tracker.successful == 0
        assert tracker.failed == 0
        assert tracker.skipped == 0

    def test_progress_updates(self):
        """Test progress tracker updates."""
        from core.progress_tracker import ProgressTracker

        tracker = ProgressTracker(total=10, description="Test", show_progress_bar=False)

        # Test successful update
        tracker.update(success=True)
        assert tracker.completed == 1
        assert tracker.successful == 1
        assert tracker.failed == 0

        # Test failed update
        tracker.update(success=False)
        assert tracker.completed == 2
        assert tracker.successful == 1
        assert tracker.failed == 1

        # Test skipped update
        tracker.update(skip=True)
        assert tracker.completed == 3
        assert tracker.skipped == 1

    def test_progress_stats(self):
        """Test progress statistics calculation."""
        from core.progress_tracker import ProgressTracker

        tracker = ProgressTracker(total=10, show_progress_bar=False)

        # Add some progress
        for i in range(5):
            tracker.update(success=True)

        stats = tracker.get_stats()
        assert stats.total == 10
        assert stats.completed == 5
        assert stats.successful == 5
        assert stats.completion_rate == 0.5
        assert stats.success_rate == 1.0


class TestBackupFunctionality:
    """Test backup functionality."""

    def test_backup_manager_creation(self):
        """Test creating a backup manager."""
        from core.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_manager = BackupManager(backup_dir=temp_dir)
            assert backup_manager.backup_dir == temp_dir
            assert backup_manager.keep_backups == 10
            assert backup_manager.backup_suffix == ".backup"

    def test_file_backup_creation(self):
        """Test creating a file backup."""
        from core.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a test file
            test_file = os.path.join(temp_dir, "test.json")
            with open(test_file, "w") as f:
                f.write('{"test": "data"}')

            # Create backup
            backup_manager = BackupManager(backup_dir=temp_dir)
            backup_path = backup_manager.create_backup(test_file)

            assert backup_path is not None
            assert os.path.exists(backup_path)
            assert backup_path.endswith(".backup")

            # Verify backup content
            with open(backup_path, "r") as f:
                content = f.read()
                assert '{"test": "data"}' in content

    def test_backup_listing(self):
        """Test listing available backups."""
        from core.backup_manager import BackupManager

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_manager = BackupManager(backup_dir=temp_dir)

            # Initially no backups
            backups = backup_manager.list_backups()
            assert len(backups) == 0

            # Create a test file and backup
            test_file = os.path.join(temp_dir, "test.json")
            with open(test_file, "w") as f:
                f.write('{"test": "data"}')

            backup_path = backup_manager.create_backup(test_file)

            # Now should have one backup
            backups = backup_manager.list_backups()
            assert len(backups) == 1
            assert backups[0]["path"] == backup_path

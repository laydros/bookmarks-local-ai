import json
from unittest.mock import patch

from core.importer import BookmarkImporter
from core.bookmark_loader import BookmarkLoader
from core.models import Bookmark


def create_test_file(tmp_path, data):
    file_path = tmp_path / "test.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


def test_duplicate_detection_by_url(tmp_path):
    """Test that duplicate URLs are detected and skipped."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    # Create existing bookmarks with one URL
    existing_bookmarks = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "description": "A test site",
        }
    ]
    target_file = existing_dir / "existing.json"
    BookmarkLoader.save_to_file(
        [Bookmark.from_dict(b) for b in existing_bookmarks], str(target_file)
    )

    # Try to import the same URL
    new_data = [{"url": "https://example.com", "title": "Same Site"}]
    new_file = create_test_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with patch("core.importer.WebExtractor.is_valid_url", return_value=True):
            dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert len(duplicates) == 1
    assert "https://example.com" in duplicates[0]
    assert "duplicate of existing bookmark" in duplicates[0]

    # Verify the bookmark wasn't added again
    final_bookmarks = BookmarkLoader.load_from_file(str(target_file))
    assert len(final_bookmarks) == 1  # Still only one bookmark


def test_duplicate_detection_by_title(tmp_path):
    """Test that duplicate titles are detected and skipped."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    # Create existing bookmarks with one title
    existing_bookmarks = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "description": "A test site",
        }
    ]
    target_file = existing_dir / "existing.json"
    BookmarkLoader.save_to_file(
        [Bookmark.from_dict(b) for b in existing_bookmarks], str(target_file)
    )

    # Try to import different URL but same title
    new_data = [{"url": "https://different.com", "title": "Example Site"}]
    new_file = create_test_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with patch("core.importer.WebExtractor.is_valid_url", return_value=True):
            dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert len(duplicates) == 1
    assert "https://different.com" in duplicates[0]
    assert "duplicate of existing bookmark" in duplicates[0]


def test_no_duplicates_allows_import(tmp_path):
    """Test that non-duplicate bookmarks are imported successfully."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    # Create existing bookmarks
    existing_bookmarks = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "description": "A test site",
        }
    ]
    target_file = existing_dir / "existing.json"
    BookmarkLoader.save_to_file(
        [Bookmark.from_dict(b) for b in existing_bookmarks], str(target_file)
    )

    # Try to import completely different bookmark
    new_data = [{"url": "https://different.com", "title": "Different Site"}]
    new_file = create_test_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with (
            patch("core.importer.WebExtractor.is_valid_url", return_value=True),
            patch(
                "core.importer.WebExtractor.extract_content",
                return_value=("Different Site", "Another test site"),
            ),
            patch(
                "core.importer.BookmarkIntelligence.suggest_categorization",
                return_value=[("existing.json", 1.0)],
            ),
        ):
            dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert duplicates == []

    # Verify the bookmark was added
    final_bookmarks = BookmarkLoader.load_from_file(str(target_file))
    assert len(final_bookmarks) == 2  # Now has both bookmarks
    assert any(b.url == "https://different.com" for b in final_bookmarks)


def test_skip_duplicate_check_option(tmp_path):
    """Test that --no-duplicate-check option bypasses duplicate detection."""
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()

    # Create existing bookmarks with one URL
    existing_bookmarks = [
        {
            "url": "https://example.com",
            "title": "Example Site",
            "description": "A test site",
        }
    ]
    target_file = existing_dir / "existing.json"
    BookmarkLoader.save_to_file(
        [Bookmark.from_dict(b) for b in existing_bookmarks], str(target_file)
    )

    # Try to import the same URL with duplicate checking disabled
    new_data = [{"url": "https://example.com", "title": "Same Site"}]
    new_file = create_test_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with (
            patch("core.importer.WebExtractor.is_valid_url", return_value=True),
            patch(
                "core.importer.WebExtractor.extract_content",
                return_value=("Same Site", "Same description"),
            ),
            patch(
                "core.importer.BookmarkIntelligence.suggest_categorization",
                return_value=[("existing.json", 1.0)],
            ),
        ):
            dead, duplicates = importer.import_from_file(
                str(new_file), check_duplicates=False
            )

    assert dead == []
    assert duplicates == []  # No duplicates detected because checking was disabled

    # Verify the duplicate bookmark was actually added
    final_bookmarks = BookmarkLoader.load_from_file(str(target_file))
    assert len(final_bookmarks) == 2  # Now has both bookmarks (including duplicate)

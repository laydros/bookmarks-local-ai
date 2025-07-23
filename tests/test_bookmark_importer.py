import json
from unittest.mock import patch

from bookmark_importer import BookmarkImporter
from core.bookmark_loader import BookmarkLoader


def create_new_file(tmp_path, data):
    file_path = tmp_path / "new.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return file_path


def create_html_file(tmp_path, url):
    content = f'<a href="{url}">Example</a>'
    file_path = tmp_path / "new.html"
    file_path.write_text(content)
    return file_path


def create_markdown_file(tmp_path, url):
    content = f"- [Example]({url})"
    file_path = tmp_path / "new.md"
    file_path.write_text(content)
    return file_path


def create_plain_file(tmp_path, url):
    file_path = tmp_path / "new.txt"
    file_path.write_text(url)
    return file_path


def test_importer_adds_bookmark(tmp_path, sample_bookmarks):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    target_file = existing_dir / "file1.json"
    BookmarkLoader.save_to_file(sample_bookmarks, str(target_file))

    new_data = [{"url": "https://new.com", "title": "New"}]
    new_file = create_new_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with patch(
            "bookmark_importer.WebExtractor.is_valid_url", return_value=True
        ), patch(
            "bookmark_importer.WebExtractor.extract_content",
            return_value=("Title", "Desc"),
        ), patch(
            "bookmark_importer.BookmarkIntelligence.suggest_categorization",
            return_value=[("file1.json", 1.0)],
        ), patch(
            "bookmark_importer.BookmarkIntelligence.is_duplicate",
            return_value=None,
        ):
            dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert duplicates == []

    bookmarks = BookmarkLoader.load_from_file(str(target_file))
    assert any(b.url == "https://new.com" for b in bookmarks)


def test_importer_reports_dead_links(tmp_path):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    BookmarkLoader.save_to_file([], str(existing_dir / "uncategorized.json"))

    new_data = [{"url": "https://dead.com"}]
    new_file = create_new_file(tmp_path, new_data)

    importer = BookmarkImporter(str(existing_dir))
    with patch.object(BookmarkImporter, "print_summary"):
        with patch("bookmark_importer.WebExtractor.is_valid_url", return_value=False):
            dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == ["https://dead.com"]
    assert duplicates == []
    bookmarks = BookmarkLoader.load_from_file(str(existing_dir / "uncategorized.json"))
    assert len(bookmarks) == 0


@patch.object(BookmarkImporter, "print_summary")
def test_importer_parses_html(mock_summary, tmp_path):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    BookmarkLoader.save_to_file([], str(existing_dir / "uncategorized.json"))

    new_file = create_html_file(tmp_path, "https://html.com")

    importer = BookmarkImporter(str(existing_dir))
    with patch("bookmark_importer.WebExtractor.is_valid_url", return_value=True), patch(
        "bookmark_importer.WebExtractor.extract_content",
        return_value=("Title", "Desc"),
    ), patch(
        "bookmark_importer.BookmarkIntelligence.suggest_categorization",
        return_value=[("uncategorized.json", 1.0)],
    ), patch(
        "bookmark_importer.BookmarkIntelligence.is_duplicate",
        return_value=None,
    ):
        dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert duplicates == []
    bookmarks = BookmarkLoader.load_from_file(str(existing_dir / "uncategorized.json"))
    assert any(b.url == "https://html.com" for b in bookmarks)


@patch.object(BookmarkImporter, "print_summary")
def test_importer_parses_markdown(mock_summary, tmp_path):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    BookmarkLoader.save_to_file([], str(existing_dir / "uncategorized.json"))

    new_file = create_markdown_file(tmp_path, "https://md.com")

    importer = BookmarkImporter(str(existing_dir))
    with patch("bookmark_importer.WebExtractor.is_valid_url", return_value=True), patch(
        "bookmark_importer.WebExtractor.extract_content",
        return_value=("Title", "Desc"),
    ), patch(
        "bookmark_importer.BookmarkIntelligence.suggest_categorization",
        return_value=[("uncategorized.json", 1.0)],
    ), patch(
        "bookmark_importer.BookmarkIntelligence.is_duplicate",
        return_value=None,
    ):
        dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert duplicates == []
    bookmarks = BookmarkLoader.load_from_file(str(existing_dir / "uncategorized.json"))
    assert any(b.url == "https://md.com" for b in bookmarks)


@patch.object(BookmarkImporter, "print_summary")
def test_importer_parses_plain_list(mock_summary, tmp_path):
    existing_dir = tmp_path / "existing"
    existing_dir.mkdir()
    BookmarkLoader.save_to_file([], str(existing_dir / "uncategorized.json"))

    new_file = create_plain_file(tmp_path, "https://plain.com")

    importer = BookmarkImporter(str(existing_dir))
    with patch("bookmark_importer.WebExtractor.is_valid_url", return_value=True), patch(
        "bookmark_importer.WebExtractor.extract_content",
        return_value=("Title", "Desc"),
    ), patch(
        "bookmark_importer.BookmarkIntelligence.is_duplicate",
        return_value=None,
    ):
        dead, duplicates = importer.import_from_file(str(new_file))

    assert dead == []
    assert duplicates == []
    bookmarks = BookmarkLoader.load_from_file(str(existing_dir / "uncategorized.json"))
    assert any(b.url == "https://plain.com" for b in bookmarks)

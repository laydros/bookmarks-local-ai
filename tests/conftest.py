"""
Pytest configuration and fixtures.
"""

import pytest
import json
import tempfile
import os
from typing import List
from core.models import Bookmark


@pytest.fixture
def sample_bookmarks() -> List[Bookmark]:
    """Sample bookmarks for testing."""
    return [
        Bookmark(
            url="https://python.org",
            title="Python.org",
            description="Official Python website",
            tags=["python", "programming", "official"],
            source_file="test.json",
        ),
        Bookmark(
            url="https://github.com",
            title="GitHub",
            excerpt="Code hosting platform",
            tags=["git", "code", "hosting"],
            source_file="test.json",
        ),
        Bookmark(
            url="https://stackoverflow.com",
            title="Stack Overflow",
            description="Programming Q&A site",
            tags=["programming", "questions", "community"],
            source_file="test.json",
        ),
    ]


@pytest.fixture
def sample_unenriched_bookmarks() -> List[Bookmark]:
    """Sample unenriched bookmarks for testing."""
    return [
        Bookmark(
            url="https://example.com", title="Example Site", source_file="test.json"
        ),
        Bookmark(
            url="https://test.com",
            title="Test Site",
            description="A test website",
            source_file="test.json",
        ),
    ]


@pytest.fixture
def temp_json_file(sample_bookmarks):
    """Create a temporary JSON file with sample bookmarks."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        data = [bookmark.to_dict() for bookmark in sample_bookmarks]
        json.dump(data, f, indent=2)
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_directory(sample_bookmarks):
    """Create a temporary directory with multiple JSON files."""
    temp_dir = tempfile.mkdtemp()

    # Create multiple files
    file1_data = [sample_bookmarks[0].to_dict(), sample_bookmarks[1].to_dict()]
    file2_data = [sample_bookmarks[2].to_dict()]

    file1_path = os.path.join(temp_dir, "file1.json")
    file2_path = os.path.join(temp_dir, "file2.json")

    with open(file1_path, "w") as f:
        json.dump(file1_data, f, indent=2)

    with open(file2_path, "w") as f:
        json.dump(file2_data, f, indent=2)

    yield temp_dir

    # Cleanup
    import shutil

    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_ollama_response():
    """Mock Ollama API response."""
    return {"embedding": [0.1] * 768}  # Mock embedding vector


@pytest.fixture
def mock_web_response():
    """Mock web response content."""
    return """
    <html>
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="Test page description">
        </head>
        <body>
            <h1>Test Page</h1>
        </body>
    </html>
    """


@pytest.fixture
def duplicate_bookmarks() -> List[Bookmark]:
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
def large_bookmark_collection() -> List[Bookmark]:
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
def mixed_enrichment_bookmarks() -> List[Bookmark]:
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

"""Tests for category management functionality."""

import json
import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from core.category_manager import CategoryManager
from core.models import Bookmark, SearchResult, SimilarBookmark


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    return Mock()


@pytest.fixture
def mock_loader():
    """Mock bookmark loader."""
    return Mock()


@pytest.fixture
def category_manager(mock_vector_store, mock_loader):
    """Create CategoryManager with mocked dependencies."""
    return CategoryManager(mock_vector_store, mock_loader)


@pytest.fixture
def sample_bookmarks():
    """Create sample bookmarks for testing."""
    return [
        Bookmark(
            url="https://example.com/3d-printer",
            title="Best 3D Printers 2024",
            description="Guide to choosing 3D printers",
            source_file="hardware.json",
        ),
        Bookmark(
            url="https://example.com/filament",
            title="3D Printing Filament Guide",
            description="Types of 3D printing filaments",
            source_file="hardware.json",
        ),
        Bookmark(
            url="https://example.com/python",
            title="Python Tutorial",
            description="Learn Python programming",
            source_file="development.json",
        ),
    ]


class TestCategoryManagerCreateCategory:
    """Test category creation functionality."""

    def test_create_category_success(self, category_manager, temp_dir):
        """Test successful category creation."""
        result = category_manager.create_category("test-category", temp_dir)

        assert result is True

        # Check file was created
        expected_path = os.path.join(temp_dir, "test-category.json")
        assert os.path.exists(expected_path)

        # Check file contents
        with open(expected_path, "r") as f:
            content = json.load(f)
        assert content == []

    def test_create_category_with_json_extension(self, category_manager, temp_dir):
        """Test category creation when .json extension is provided."""
        result = category_manager.create_category("test-category.json", temp_dir)

        assert result is True
        expected_path = os.path.join(temp_dir, "test-category.json")
        assert os.path.exists(expected_path)

    def test_create_category_already_exists(self, category_manager, temp_dir):
        """Test handling when category file already exists."""
        # Create the file first
        test_file = os.path.join(temp_dir, "existing.json")
        with open(test_file, "w") as f:
            json.dump([], f)

        result = category_manager.create_category("existing", temp_dir)
        assert result is False

    def test_create_category_invalid_directory(self, category_manager):
        """Test handling when output directory doesn't exist."""
        result = category_manager.create_category("test", "/invalid/path")
        assert result is False

    def test_create_categories_multiple(self, category_manager, temp_dir):
        """Create multiple categories at once."""
        names = ["one", "two"]

        created = category_manager.create_categories(names, temp_dir)

        assert created == 2
        for name in names:
            assert os.path.exists(os.path.join(temp_dir, f"{name}.json"))

    def test_create_categories_skip_existing(self, category_manager, temp_dir):
        """Existing files are skipped."""
        existing = os.path.join(temp_dir, "exists.json")
        with open(existing, "w") as f:
            json.dump([], f)

        created = category_manager.create_categories(["exists", "new"], temp_dir)

        assert created == 1
        assert os.path.exists(os.path.join(temp_dir, "new.json"))


class TestCategoryManagerFindCandidates:
    """Test finding category candidates."""

    def test_find_candidates_success(
        self, category_manager, mock_vector_store, sample_bookmarks
    ):
        """Test successful candidate finding."""
        # Mock search results
        mock_similar = [
            SimilarBookmark(
                bookmark=sample_bookmarks[0],
                similarity_score=0.9,
                content="3d printing content",
            ),
            SimilarBookmark(
                bookmark=sample_bookmarks[1],
                similarity_score=0.87,
                content="filament content",
            ),
            SimilarBookmark(
                bookmark=sample_bookmarks[2],
                similarity_score=0.5,
                content="python content",
            ),  # Below threshold
        ]
        mock_search_result = SearchResult(
            query="3d printing", similar_bookmarks=mock_similar, total_results=3
        )
        mock_vector_store.search.return_value = mock_search_result

        candidates = category_manager.find_category_candidates(
            "3d-printing", sample_bookmarks, limit=5, threshold=0.85
        )

        # Should return 2 candidates above threshold
        assert len(candidates) == 2
        assert candidates[0][0] == sample_bookmarks[0]
        assert candidates[0][1] == 0.9
        assert candidates[1][0] == sample_bookmarks[1]
        assert candidates[1][1] == 0.87

        # Verify search was called with cleaned name
        mock_vector_store.search.assert_called_once_with("3d printing", n_results=15)

    def test_find_candidates_exclude_existing_category(
        self, category_manager, mock_vector_store, sample_bookmarks
    ):
        """Test that bookmarks already in target category are excluded."""
        # Set one bookmark to already be in the target category
        sample_bookmarks[0].source_file = "3d-printing.json"

        mock_similar = [
            SimilarBookmark(
                bookmark=sample_bookmarks[0],
                similarity_score=0.9,
                content="3d printing content",
            ),  # Should be excluded
            SimilarBookmark(
                bookmark=sample_bookmarks[1],
                similarity_score=0.87,
                content="filament content",
            ),
        ]
        mock_search_result = SearchResult(
            query="3d printing", similar_bookmarks=mock_similar, total_results=2
        )
        mock_vector_store.search.return_value = mock_search_result

        candidates = category_manager.find_category_candidates(
            "3d-printing", sample_bookmarks, limit=5, threshold=0.85
        )

        # Should only return 1 candidate (excluded the one already in category)
        assert len(candidates) == 1
        assert candidates[0][0] == sample_bookmarks[1]

    def test_find_candidates_no_results(
        self, category_manager, mock_vector_store, sample_bookmarks
    ):
        """Test handling when no search results are found."""
        mock_search_result = SearchResult(
            query="nonexistent", similar_bookmarks=[], total_results=0
        )
        mock_vector_store.search.return_value = mock_search_result

        candidates = category_manager.find_category_candidates(
            "nonexistent", sample_bookmarks
        )

        assert len(candidates) == 0

    def test_find_candidates_limit_respected(
        self, category_manager, mock_vector_store, sample_bookmarks
    ):
        """Test that the limit parameter is respected."""
        # Create many high-scoring candidates
        mock_similar = [
            SimilarBookmark(
                bookmark=sample_bookmarks[0], similarity_score=0.95, content="content1"
            ),
            SimilarBookmark(
                bookmark=sample_bookmarks[1], similarity_score=0.90, content="content2"
            ),
            SimilarBookmark(
                bookmark=sample_bookmarks[2], similarity_score=0.88, content="content3"
            ),
        ]
        mock_search_result = SearchResult(
            query="test", similar_bookmarks=mock_similar, total_results=3
        )
        mock_vector_store.search.return_value = mock_search_result

        candidates = category_manager.find_category_candidates(
            "test", sample_bookmarks, limit=2, threshold=0.85
        )

        # Should respect limit of 2
        assert len(candidates) == 2

    def test_find_candidates_fallback_low_scores(
        self, category_manager, mock_vector_store, sample_bookmarks
    ):
        """Ensure low-score results are still returned if none meet the threshold."""
        mock_similar = [
            SimilarBookmark(
                bookmark=sample_bookmarks[0], similarity_score=0.55, content="c1"
            ),
            SimilarBookmark(
                bookmark=sample_bookmarks[1], similarity_score=0.50, content="c2"
            ),
        ]
        mock_vector_store.search.return_value = SearchResult(
            query="emacs",
            similar_bookmarks=mock_similar,
            total_results=2,
        )

        candidates = category_manager.find_category_candidates(
            "emacs", sample_bookmarks, limit=5, threshold=0.85
        )

        assert len(candidates) == 2
        assert candidates[0][0] == sample_bookmarks[0]
        assert candidates[0][1] == 0.55


class TestCategoryManagerMoveBookmarks:
    """Test moving bookmarks between categories."""

    def test_move_bookmarks_success(
        self, category_manager, mock_loader, temp_dir, sample_bookmarks
    ):
        """Test successful bookmark moving."""
        # Setup mocks - target category doesn't exist yet
        mock_loader.load_from_file.return_value = []
        mock_loader.save_to_file.return_value = True
        mock_loader.save_by_source_file.return_value = True

        bookmarks_to_move = [sample_bookmarks[0]]
        all_bookmarks = sample_bookmarks.copy()

        result = category_manager.move_bookmarks_to_category(
            bookmarks_to_move, "3d-printing", all_bookmarks, temp_dir
        )

        assert result is True

        # Verify bookmark was removed from main list
        assert sample_bookmarks[0] not in all_bookmarks

        # Verify save methods were called
        expected_target_path = os.path.join(temp_dir, "3d-printing.json")
        mock_loader.save_to_file.assert_called_once_with(
            [sample_bookmarks[0]], expected_target_path
        )
        mock_loader.save_by_source_file.assert_called_once_with(all_bookmarks, temp_dir)

    def test_move_bookmarks_existing_target_category(
        self, category_manager, mock_loader, temp_dir, sample_bookmarks
    ):
        """Test moving bookmarks to existing category file."""
        # Setup - target category already has bookmarks
        existing_bookmark = Bookmark(
            url="https://existing.com", title="Existing", description=""
        )
        expected_target_path = os.path.join(temp_dir, "3d-printing.json")

        # Mock that the target file exists and has existing bookmarks
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            mock_loader.load_from_file.return_value = [existing_bookmark]
            mock_loader.save_to_file.return_value = True
            mock_loader.save_by_source_file.return_value = True

            bookmarks_to_move = [sample_bookmarks[0]]
            all_bookmarks = sample_bookmarks.copy()

            result = category_manager.move_bookmarks_to_category(
                bookmarks_to_move, "3d-printing", all_bookmarks, temp_dir
            )

            assert result is True

            # Verify both existing and new bookmarks were saved
            expected_target_bookmarks = [existing_bookmark, sample_bookmarks[0]]
            mock_loader.save_to_file.assert_called_once_with(
                expected_target_bookmarks, expected_target_path
            )

    def test_move_bookmarks_add_json_extension(
        self, category_manager, mock_loader, temp_dir, sample_bookmarks
    ):
        """Test that .json extension is added if missing."""
        mock_loader.load_from_file.return_value = []
        mock_loader.save_to_file.return_value = True
        mock_loader.save_by_source_file.return_value = True

        # Use the specific bookmark for this test
        bookmarks_to_move = [sample_bookmarks[1]]  # The filament bookmark
        all_bookmarks = sample_bookmarks.copy()

        result = category_manager.move_bookmarks_to_category(
            bookmarks_to_move,
            "3d-printing",
            all_bookmarks,
            temp_dir,  # No .json extension
        )

        assert result is True

        # Verify .json was added to the path
        expected_target_path = os.path.join(temp_dir, "3d-printing.json")
        mock_loader.save_to_file.assert_called_once_with(
            bookmarks_to_move, expected_target_path
        )

    def test_move_bookmarks_empty_list(self, category_manager, mock_loader, temp_dir):
        """Test moving empty list of bookmarks."""
        result = category_manager.move_bookmarks_to_category([], "test", [], temp_dir)

        assert result is True
        # No mock methods should be called
        mock_loader.save_to_file.assert_not_called()
        mock_loader.save_by_source_file.assert_not_called()

    def test_move_bookmarks_save_failure(
        self, category_manager, mock_loader, temp_dir, sample_bookmarks
    ):
        """Test handling when saving fails."""
        mock_loader.load_from_file.return_value = []
        mock_loader.save_to_file.return_value = False  # Simulate save failure

        result = category_manager.move_bookmarks_to_category(
            [sample_bookmarks[0]], "test", sample_bookmarks, temp_dir
        )

        assert result is False


class TestCategoryManagerIntegration:
    """Integration tests for CategoryManager."""

    @pytest.mark.integration
    def test_full_workflow_with_real_files(self, temp_dir):
        """Test complete workflow with real file operations."""
        # Create real bookmark files
        hardware_bookmarks = [
            {
                "url": "https://example.com/3d-printer",
                "title": "Best 3D Printers",
                "description": "Guide to 3D printers",
            },
            {
                "url": "https://example.com/regular-hardware",
                "title": "Computer Parts",
                "description": "PC building guide",
            },
        ]

        hardware_file = os.path.join(temp_dir, "hardware.json")
        with open(hardware_file, "w") as f:
            json.dump(hardware_bookmarks, f, indent=2)

        # Create CategoryManager with real dependencies
        from core.bookmark_loader import BookmarkLoader
        from core.vector_store import VectorStore

        # Mock just the vector store for this test
        mock_vector_store = Mock()
        loader = BookmarkLoader()
        manager = CategoryManager(mock_vector_store, loader)

        # Test 1: Create new category
        result = manager.create_category("3d-printing", temp_dir)
        assert result is True

        category_file = os.path.join(temp_dir, "3d-printing.json")
        assert os.path.exists(category_file)

        # Test 2: Load bookmarks
        bookmarks = loader.load_from_file(hardware_file)
        assert len(bookmarks) == 2

        # Test 3: Mock finding candidates (since we don't have real vector search)
        mock_similar = [
            SimilarBookmark(
                bookmark=bookmarks[0],
                similarity_score=0.9,
                content="3d printer content",
            )  # The 3D printer bookmark
        ]
        mock_search_result = SearchResult(
            query="3d printing", similar_bookmarks=mock_similar, total_results=1
        )
        mock_vector_store.search.return_value = mock_search_result

        candidates = manager.find_category_candidates("3d-printing", bookmarks)
        assert len(candidates) == 1
        assert "3D Printers" in candidates[0][0].title

        # Test 4: Move bookmark
        result = manager.move_bookmarks_to_category(
            [candidates[0][0]], "3d-printing", bookmarks, temp_dir
        )
        assert result is True

        # Verify files were updated
        with open(category_file, "r") as f:
            category_content = json.load(f)
        assert len(category_content) == 1
        assert category_content[0]["title"] == "Best 3D Printers"

        with open(hardware_file, "r") as f:
            hardware_content = json.load(f)
        assert len(hardware_content) == 1  # One bookmark moved out
        assert hardware_content[0]["title"] == "Computer Parts"


@pytest.mark.slow
class TestCategoryManagerInteractive:
    """Test interactive functionality (requires manual input simulation)."""

    def test_populate_category_interactive_mock_input(
        self, category_manager, mock_vector_store, sample_bookmarks, temp_dir
    ):
        """Test interactive population with mocked user input."""
        # Setup search results
        mock_similar = [
            SimilarBookmark(
                bookmark=sample_bookmarks[0], similarity_score=0.9, content="3d content"
            ),
        ]
        mock_search_result = SearchResult(
            query="3d printing", similar_bookmarks=mock_similar, total_results=1
        )
        mock_vector_store.search.return_value = mock_search_result

        # Mock loader for move operation
        category_manager.loader.load_from_file.return_value = []
        category_manager.loader.save_to_file.return_value = True
        category_manager.loader.save_by_source_file.return_value = True

        # Mock user input - select 'y' (yes to move all)
        with patch("builtins.input", return_value="y"):
            result = category_manager.populate_category_interactive(
                "3d-printing", sample_bookmarks, temp_dir
            )

        assert result is True

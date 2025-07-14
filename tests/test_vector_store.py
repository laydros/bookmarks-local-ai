"""
Tests for vector store operations.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from core.vector_store import VectorStore
from core.models import Bookmark


class TestVectorStore:
    """Test VectorStore class."""

    @patch("chromadb.Client")
    def test_vector_store_initialization(self, mock_client_class):
        """Test VectorStore initialization."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()

        assert vs.collection_name == "bookmarks"
        assert vs.embedding_model == "nomic-embed-text"
        mock_client.get_collection.assert_called_once_with(name="bookmarks")

    @patch("chromadb.Client")
    def test_vector_store_create_new_collection(self, mock_client_class):
        """Test creating new collection when none exists."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.side_effect = Exception("Collection not found")
        mock_client.create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()

        mock_client.create_collection.assert_called_once_with(name="bookmarks")
        assert vs.collection == mock_collection

    @patch("ollama.embeddings")
    def test_get_embeddings_success(self, mock_embeddings):
        """Test successful embedding generation."""
        mock_embeddings.return_value = {"embedding": [0.1] * 768}

        with patch("chromadb.Client"):
            vs = VectorStore()
            embeddings = vs.get_embeddings(["test text"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768
        assert embeddings[0][0] == 0.1

    @patch("ollama.embeddings")
    def test_get_embeddings_error(self, mock_embeddings):
        """Test embedding generation with error."""
        mock_embeddings.side_effect = Exception("API Error")

        with patch("chromadb.Client"):
            vs = VectorStore()
            embeddings = vs.get_embeddings(["test text"])

        assert len(embeddings) == 1
        assert len(embeddings[0]) == 768
        assert all(e == 0.0 for e in embeddings[0])  # Zero vector fallback

    @patch("chromadb.Client")
    @patch("ollama.embeddings")
    def test_add_bookmarks_success(self, mock_embeddings, mock_client_class):
        """Test successful bookmark addition."""
        # Setup mocks
        mock_embeddings.return_value = {"embedding": [0.1] * 768}
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()

        bookmarks = [
            Bookmark(
                url="https://example.com",
                title="Example",
                description="Test",
                tags=["test"],
            )
        ]

        result = vs.add_bookmarks(bookmarks)

        assert result is True
        mock_collection.add.assert_called_once()

    @patch("chromadb.Client")
    def test_add_bookmarks_empty_list(self, mock_client_class):
        """Test adding empty bookmark list."""
        mock_client = Mock()
        mock_client.get_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        vs = VectorStore()
        result = vs.add_bookmarks([])

        assert result is True

    @patch("chromadb.Client")
    def test_add_bookmarks_invalid_bookmark(self, mock_client_class):
        """Test adding bookmark with no URL."""
        mock_client = Mock()
        mock_client.get_collection.return_value = Mock()
        mock_client_class.return_value = mock_client

        vs = VectorStore()

        # Bookmark with no URL
        bookmarks = [Bookmark(url="", title="No URL")]
        result = vs.add_bookmarks(bookmarks)

        assert result is False  # No valid documents to add

    @patch("chromadb.Client")
    @patch("ollama.embeddings")
    def test_search_success(self, mock_embeddings, mock_client_class):
        """Test successful search."""
        # Setup mocks
        mock_embeddings.return_value = {"embedding": [0.1] * 768}
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "documents": [["Test document"]],
            "metadatas": [
                [{"url": "https://example.com", "title": "Example", "tags": ["test"]}]
            ],
            "distances": [[0.2]],
        }
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()
        result = vs.search("test query")

        assert result.query == "test query"
        assert result.total_results == 1
        assert len(result.similar_bookmarks) == 1
        assert result.similar_bookmarks[0].bookmark.url == "https://example.com"

    @patch("chromadb.Client")
    @patch("ollama.embeddings")
    def test_search_no_results(self, mock_embeddings, mock_client_class):
        """Test search with no results."""
        # Setup mocks
        mock_embeddings.return_value = {"embedding": [0.1] * 768}
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.query.return_value = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()
        result = vs.search("test query")

        assert result.query == "test query"
        assert result.total_results == 0
        assert len(result.similar_bookmarks) == 0

    @patch("chromadb.Client")
    def test_clear_success(self, mock_client_class):
        """Test successful vector store clearing."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.delete_collection.return_value = None
        mock_client.create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()
        result = vs.clear()

        assert result is True
        mock_client.delete_collection.assert_called_once_with(name="bookmarks")

    @patch("chromadb.Client")
    def test_get_stats(self, mock_client_class):
        """Test getting vector store statistics."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.count.return_value = 42
        mock_client.get_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        vs = VectorStore()
        stats = vs.get_stats()

        assert stats["total_documents"] == 42
        assert stats["collection_name"] == "bookmarks"
        assert stats["embedding_model"] == "nomic-embed-text"

    @patch("chromadb.Client")
    def test_rebuild_from_bookmarks(self, mock_client_class):
        """Test rebuilding vector store from bookmarks."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.get_collection.return_value = mock_collection
        mock_client.delete_collection.return_value = None
        mock_client.create_collection.return_value = mock_collection
        mock_client_class.return_value = mock_client

        with patch.object(VectorStore, "add_bookmarks", return_value=True) as mock_add:
            vs = VectorStore()
            bookmarks = [Bookmark(url="https://example.com", title="Test")]
            result = vs.rebuild_from_bookmarks(bookmarks)

            assert result is True
            mock_add.assert_called_once_with(bookmarks)

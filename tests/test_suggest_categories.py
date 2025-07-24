"""Tests for category suggestion feature."""

from unittest.mock import Mock, patch

from core.category_suggester import CategorySuggester


def test_suggest_categories_basic(sample_bookmarks):
    vs = Mock()
    vs.get_embeddings.return_value = [0.0]
    suggester = CategorySuggester(vs)

    # Create clusters with at least 3 bookmarks each to pass the new filtering
    # Add more bookmarks to sample_bookmarks if needed
    extended_bookmarks = sample_bookmarks * 3  # Ensure we have enough bookmarks

    with (
        patch.object(suggester, "_cluster_embeddings", return_value=[0, 0, 0, 1, 1, 1]),
        patch("core.category_suggester.ProgressTracker"),
        patch.object(
            suggester,
            "_generate_cluster_summary",
            side_effect=[
                {"name": "Cat A", "description": "desc"},
                {"name": "Cat B", "description": "desc"},
            ],
        ),
    ):
        suggestions = suggester.suggest(extended_bookmarks)

    assert len(suggestions) == 2
    assert suggestions[0].name == "Cat A"
    assert suggestions[1].name == "Cat B"
    assert len(suggestions[0].bookmarks) > 0


def test_suggest_categories_with_kmeans(sample_bookmarks):
    """Test category suggestions with forced K-means clustering."""
    vs = Mock()
    vs.get_embeddings.return_value = [0.0]
    suggester = CategorySuggester(vs)

    extended_bookmarks = sample_bookmarks * 2  # 6 bookmarks total

    with (
        patch("sklearn.cluster.KMeans") as mock_kmeans,
        patch("core.category_suggester.ProgressTracker"),
        patch.object(
            suggester,
            "_generate_cluster_summary",
            side_effect=[
                {
                    "name": "Tech Resources",
                    "description": "Technology-related bookmarks",
                },
                {"name": "Learning Materials", "description": "Educational content"},
            ],
        ),
    ):
        # Mock KMeans to return clusters [0, 0, 0, 1, 1, 1] as numpy array
        import numpy as np

        mock_instance = Mock()
        mock_instance.fit_predict.return_value = np.array([0, 0, 0, 1, 1, 1])
        mock_kmeans.return_value = mock_instance

        # Force K-means with k=2
        suggestions = suggester.suggest(extended_bookmarks, use_kmeans=2)

    assert len(suggestions) == 2
    assert suggestions[0].name == "Tech Resources"
    assert suggestions[1].name == "Learning Materials"
    # Verify K-means was called with the correct parameters
    mock_kmeans.assert_called_once_with(n_clusters=2, random_state=42)

"""Tests for category suggestion feature."""

from unittest.mock import Mock, patch

from core.category_suggester import CategorySuggester


def test_suggest_categories_basic(sample_bookmarks):
    vs = Mock()
    vs.get_embeddings.return_value = [0.0]
    suggester = CategorySuggester(vs)

    with patch.object(suggester, "_cluster_embeddings", return_value=[0, 0, 1]), patch(
        "core.category_suggester.ProgressTracker"
    ), patch.object(
        suggester,
        "_generate_cluster_summary",
        side_effect=[
            {"name": "Cat A", "description": "desc"},
            {"name": "Cat B", "description": "desc"},
        ],
    ):
        suggestions = suggester.suggest(sample_bookmarks)

    assert len(suggestions) == 2
    assert suggestions[0].name == "Cat A"
    assert suggestions[1].name == "Cat B"
    assert len(suggestions[0].bookmarks) > 0

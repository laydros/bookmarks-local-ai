from contextlib import contextmanager
from unittest.mock import patch, Mock

from core.enricher import BookmarkEnricher
from core.models import Bookmark


@contextmanager
def no_spinner(*args, **kwargs):
    yield


def _make_stub(bookmark: Bookmark) -> Bookmark:
    bookmark.description = "desc"
    bookmark.tags = ["tag"]
    return bookmark


def test_process_bookmarks_limit(mixed_enrichment_bookmarks):
    enricher = BookmarkEnricher()
    enricher.vector_store.rebuild_from_bookmarks = Mock(return_value=True)

    with (
        patch("core.enricher.Spinner", no_spinner),
        patch("core.enricher.time.sleep"),
        patch.object(
            enricher, "enrich_bookmark", side_effect=_make_stub
        ) as mock_enrich,
    ):
        enricher._process_bookmarks(mixed_enrichment_bookmarks, limit=2)

    assert mock_enrich.call_count == 2
    assert mixed_enrichment_bookmarks[2].description == "desc"
    assert mixed_enrichment_bookmarks[3].description == "desc"
    # Last unenriched bookmark unchanged
    assert mixed_enrichment_bookmarks[4].description == ""


def test_process_directory_limit(mixed_enrichment_bookmarks):
    enricher = BookmarkEnricher()
    with (
        patch.object(
            enricher.loader,
            "load_from_directory",
            return_value=mixed_enrichment_bookmarks,
        ),
        patch.object(
            enricher.loader, "save_by_source_file", return_value=True
        ) as mock_save,
        patch.object(
            enricher.vector_store, "rebuild_from_bookmarks", return_value=True
        ),
        patch("core.enricher.Spinner", no_spinner),
        patch("core.enricher.time.sleep"),
        patch.object(
            enricher, "enrich_bookmark", side_effect=_make_stub
        ) as mock_enrich,
    ):
        enricher.process_directory("dummy", limit=1)

    mock_save.assert_called_once()
    assert mock_enrich.call_count == 1
    assert mixed_enrichment_bookmarks[2].description == "desc"
    assert mixed_enrichment_bookmarks[3].description == "Test site"

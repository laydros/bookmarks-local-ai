"""Environment configuration helpers."""

from __future__ import annotations

__all__ = ["configure_chromadb_env"]

import logging
import os


def configure_chromadb_env() -> None:
    """Configure environment and logging for ChromaDB.

    This should be called before importing modules that initialize ChromaDB so
    that the environment variables take effect early. The function disables
    telemetry, adjusts file descriptor limits, and suppresses verbose logging
    from the telemetry subsystem.
    """
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_SERVER_NOFILE", "1")

    logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

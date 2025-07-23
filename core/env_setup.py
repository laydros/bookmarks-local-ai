"""Environment configuration helpers."""

from __future__ import annotations

import logging
import os


def configure_chromadb_env() -> None:
    """Configure environment and logging for ChromaDB.

    Sets environment variables to disable telemetry and adjust file limits, and
    suppresses verbose telemetry logging from ChromaDB.
    """
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_SERVER_NOFILE", "1")

    logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

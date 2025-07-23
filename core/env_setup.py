"""Environment setup utilities."""

from __future__ import annotations

import logging
import os


def configure_chromadb_env() -> None:
    """Configure environment variables and logging for ChromaDB."""
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    os.environ.setdefault("CHROMA_SERVER_NOFILE", "1")
    logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
    logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

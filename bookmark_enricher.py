#!/usr/bin/env python3
"""Bookmark Enricher using RAG with Ollama and ChromaDB - CLI."""

import argparse
import logging
import os

from core.enricher import BookmarkEnricher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("ollama").setLevel(logging.WARNING)

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_SERVER_NOFILE"] = "1"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


def main() -> None:
    """Run the bookmark enricher."""
    parser = argparse.ArgumentParser(description="Enrich bookmarks using RAG")
    parser.add_argument(
        "input", help="Input JSON file or directory with bookmark files"
    )
    parser.add_argument(
        "--output", "-o", help="Output JSON file (only used for single file mode)"
    )
    parser.add_argument(
        "--embedding-model",
        default="nomic-embed-text",
        help="Embedding model for Ollama (default: nomic-embed-text)",
    )
    parser.add_argument(
        "--llm-model",
        default="llama3.1:8b",
        help="LLM model for Ollama (default: llama3.1:8b)",
    )
    parser.add_argument(
        "--directory",
        "-d",
        action="store_true",
        help="Process all JSON files in the specified directory",
    )
    parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=None,
        help="Only process the first N unenriched bookmarks",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input path {args.input} not found")
        return

    try:
        enricher = BookmarkEnricher(
            embedding_model=args.embedding_model, llm_model=args.llm_model
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to initialize enricher: {e}")
        return

    try:
        if args.directory or os.path.isdir(args.input):
            enricher.process_directory(args.input, limit=args.limit)
        else:
            enricher.process_single_file(args.input, args.output, limit=args.limit)
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:  # noqa: BLE001
        logger.error(f"Processing failed: {e}")


if __name__ == "__main__":
    main()

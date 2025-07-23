#!/usr/bin/env python3
"""Bookmark importer CLI."""

import argparse

from core.importer import BookmarkImporter


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Import new bookmarks")
    parser.add_argument("collection", help="Existing bookmark file or directory")
    parser.add_argument(
        "new",
        help="Bookmark file to import (JSON, HTML, Markdown, or plain URLs)",
    )
    parser.add_argument(
        "--no-duplicate-check",
        action="store_true",
        help="Skip duplicate checking (faster but may create duplicates)",
    )
    args = parser.parse_args()

    importer = BookmarkImporter(args.collection)
    dead, duplicates = importer.import_from_file(
        args.new, check_duplicates=not args.no_duplicate_check
    )
    BookmarkImporter.print_summary(dead, duplicates)


if __name__ == "__main__":
    main()

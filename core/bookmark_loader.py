"""
Bookmark loading utilities.
"""

import json
import os
import logging
from typing import Dict, List
from .models import Bookmark

logger = logging.getLogger(__name__)


class BookmarkLoader:
    """Handles loading bookmarks from various sources."""

    @staticmethod
    def load_from_file(file_path: str) -> List[Bookmark]:
        """
        Load bookmarks from a single JSON file.

        Args:
            file_path: Path to JSON file

        Returns:
            List of Bookmark objects
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            bookmarks = []
            filename = os.path.basename(file_path)

            for item in data:
                bookmark = Bookmark.from_dict(item)
                bookmark.source_file = filename
                bookmarks.append(bookmark)

            logger.info(f"Loaded {len(bookmarks)} bookmarks from {filename}")
            return bookmarks

        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return []

    @staticmethod
    def load_from_directory(directory_path: str) -> List[Bookmark]:
        """
        Load bookmarks from all JSON files in a directory.

        Args:
            directory_path: Path to directory containing JSON files

        Returns:
            List of all Bookmark objects from all files
        """
        if not os.path.isdir(directory_path):
            logger.error(f"Directory not found: {directory_path}")
            return []

        all_bookmarks = []
        json_files = []

        # Find all JSON files
        for filename in os.listdir(directory_path):
            if filename.endswith(".json"):
                json_files.append(os.path.join(directory_path, filename))

        if not json_files:
            logger.warning(f"No JSON files found in {directory_path}")
            return []

        logger.info(f"Found {len(json_files)} JSON files to load")

        # Load bookmarks from each file
        for json_file in sorted(json_files):
            bookmarks = BookmarkLoader.load_from_file(json_file)
            all_bookmarks.extend(bookmarks)

        logger.info(f"Total bookmarks loaded: {len(all_bookmarks)}")
        return all_bookmarks

    @staticmethod
    def save_to_file(bookmarks: List[Bookmark], file_path: str) -> bool:
        """
        Save bookmarks to a JSON file.

        Args:
            bookmarks: List of Bookmark objects
            file_path: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            data = [bookmark.to_dict() for bookmark in bookmarks]

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, separators=(",", ": "))

            logger.info(f"Saved {len(bookmarks)} bookmarks to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving to {file_path}: {e}")
            return False

    @staticmethod
    def save_by_source_file(bookmarks: List[Bookmark], directory_path: str) -> bool:
        """
        Save bookmarks back to their original files.

        Args:
            bookmarks: List of Bookmark objects with source_file metadata
            directory_path: Directory to save files to

        Returns:
            True if all files saved successfully, False otherwise
        """
        # Group bookmarks by source file
        files_dict = {}
        for bookmark in bookmarks:
            source_file = bookmark.source_file
            if source_file:
                if source_file not in files_dict:
                    files_dict[source_file] = []
                files_dict[source_file].append(bookmark)

        success = True

        # Save each file
        for filename, file_bookmarks in files_dict.items():
            output_path = os.path.join(directory_path, filename)
            if not BookmarkLoader.save_to_file(file_bookmarks, output_path):
                success = False

        return success

    @staticmethod
    def filter_enriched(bookmarks: List[Bookmark]) -> List[Bookmark]:
        """
        Filter to only enriched bookmarks (have both content and tags).

        Args:
            bookmarks: List of Bookmark objects

        Returns:
            List of enriched Bookmark objects
        """
        return [b for b in bookmarks if b.is_enriched]

    @staticmethod
    def filter_unenriched(bookmarks: List[Bookmark]) -> List[Bookmark]:
        """
        Filter to only unenriched bookmarks (missing content or tags).

        Args:
            bookmarks: List of Bookmark objects

        Returns:
            List of unenriched Bookmark objects
        """
        return [b for b in bookmarks if not b.is_enriched]

    @staticmethod
    def get_stats(bookmarks: List[Bookmark]) -> Dict:
        """
        Get statistics about a bookmark collection.

        Args:
            bookmarks: List of Bookmark objects

        Returns:
            Dictionary with statistics
        """
        if not bookmarks:
            return {}

        enriched = BookmarkLoader.filter_enriched(bookmarks)
        unenriched = BookmarkLoader.filter_unenriched(bookmarks)

        # Count by source file
        file_counts = {}
        for bookmark in bookmarks:
            file_counts[bookmark.source_file] = (
                file_counts.get(bookmark.source_file, 0) + 1
            )

        # Count by domain
        domain_counts = {}
        for bookmark in bookmarks:
            domain = bookmark.domain
            if domain:
                domain_counts[domain] = domain_counts.get(domain, 0) + 1

        return {
            "total": len(bookmarks),
            "enriched": len(enriched),
            "unenriched": len(unenriched),
            "enrichment_percentage": (len(enriched) / len(bookmarks)) * 100,
            "files": len(file_counts),
            "file_counts": file_counts,
            "top_domains": sorted(
                domain_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
        }

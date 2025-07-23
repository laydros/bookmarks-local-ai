"""Category management utilities."""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Sequence, Tuple

from .bookmark_loader import BookmarkLoader
from .models import Bookmark
from .spinner import Spinner
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class CategoryManager:
    """Manage bookmark categories and population."""

    def __init__(self, vector_store: VectorStore, bookmark_loader: BookmarkLoader):
        self.vector_store = vector_store
        self.loader = bookmark_loader

    def create_category(self, category_name: str, output_dir: str) -> bool:
        """
        Create a new empty category file.

        Args:
            category_name: Name of the category (with or without .json extension)
            output_dir: Directory to create the file in

        Returns:
            True if successful, False otherwise
        """
        import json

        # Ensure .json extension
        if not category_name.endswith(".json"):
            category_name = f"{category_name}.json"

        file_path = os.path.join(output_dir, category_name)

        if os.path.exists(file_path):
            logger.warning(f"Category file already exists: {file_path}")
            return False

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            logger.info(f"Created empty category file: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error creating category file: {e}")
            return False

    def create_categories(self, category_names: Sequence[str], output_dir: str) -> int:
        """Create multiple empty category files.

        Args:
            category_names: Iterable of category names (with or without .json)
            output_dir: Directory to create files in

        Returns:
            Number of files successfully created
        """
        created = 0
        os.makedirs(output_dir, exist_ok=True)

        for name in category_names:
            if self.create_category(name, output_dir):
                created += 1

        return created

    def find_category_candidates(
        self,
        category_name: str,
        bookmarks: List[Bookmark],
        limit: int = 5,
        threshold: float = 0.85,
    ) -> List[Tuple[Bookmark, float]]:
        """
        Find bookmarks that should belong in a specific category.

        Args:
            category_name: Name of the category to populate (e.g., "3d-printing")
            bookmarks: List of all bookmarks to search through
            limit: Maximum number of candidates to return
            threshold: Minimum similarity score to consider

        Returns:
            List of (bookmark, confidence_score) tuples sorted by confidence
        """
        # Clean category name (remove .json extension if present)
        clean_name = (
            category_name.replace(".json", "").replace("-", " ").replace("_", " ")
        )

        # Search for bookmarks similar to this category
        with Spinner(f"Finding candidates for '{clean_name}' category..."):
            search_result = self.vector_store.search(
                clean_name, n_results=limit * 3
            )  # Get extra for filtering

            if not search_result.similar_bookmarks:
                return []

            # Filter by threshold and exclude bookmarks already in target category
            target_filename = (
                category_name
                if category_name.endswith(".json")
                else f"{category_name}.json"
            )
            candidates = []

            for similar in search_result.similar_bookmarks:
                bookmark = similar.bookmark
                score = similar.similarity_score

                # Skip if already in target category
                if (
                    bookmark.source_file
                    and os.path.basename(bookmark.source_file) == target_filename
                ):
                    continue

                if score >= threshold:
                    candidates.append((bookmark, score))
                if len(candidates) >= limit:
                    break

            # Fallback: if nothing met the threshold, return best matches anyway
            if not candidates:
                for similar in search_result.similar_bookmarks[:limit]:
                    bookmark = similar.bookmark
                    if (
                        bookmark.source_file
                        and os.path.basename(bookmark.source_file) == target_filename
                    ):
                        continue
                    candidates.append((bookmark, similar.similarity_score))

        return candidates

    def move_bookmarks_to_category(
        self,
        bookmarks_to_move: List[Bookmark],
        target_category: str,
        bookmarks: List[Bookmark],
        base_dir: str,
    ) -> bool:
        """
        Move bookmarks to a target category file.

        Args:
            bookmarks_to_move: List of bookmarks to move
            target_category: Target category filename (e.g., "3d-printing.json")
            bookmarks: Full list of bookmarks (will be modified)
            base_dir: Base directory where category files are stored

        Returns:
            True if successful, False otherwise
        """
        if not bookmarks_to_move:
            return True

        # Ensure target category file has .json extension
        if not target_category.endswith(".json"):
            target_category = f"{target_category}.json"

        target_path = os.path.join(base_dir, target_category)

        try:
            # Load existing bookmarks in target category
            target_bookmarks = []
            if os.path.exists(target_path):
                target_bookmarks = self.loader.load_from_file(target_path)

            # Add new bookmarks to target
            target_bookmarks.extend(bookmarks_to_move)

            # Remove bookmarks from their original files and from the main list
            for bookmark in bookmarks_to_move:
                if bookmark in bookmarks:
                    bookmarks.remove(bookmark)

            # Save target category file
            if not self.loader.save_to_file(target_bookmarks, target_path):
                logger.error(f"Failed to save target category: {target_path}")
                return False

            # Save changes to original files (remove the moved bookmarks)
            if not self.loader.save_by_source_file(bookmarks, base_dir):
                logger.error("Failed to update source files")
                return False

            logger.info(
                f"Successfully moved {len(bookmarks_to_move)} bookmarks to {target_category}"
            )
            return True

        except Exception as e:
            logger.error(f"Error moving bookmarks: {e}")
            return False

    def populate_category_interactive(
        self,
        category_name: str,
        bookmarks: List[Bookmark],
        base_dir: str,
        limit: int = 5,
        threshold: float = 0.85,
    ) -> bool:
        """
        Interactively populate a category with user approval.

        Args:
            category_name: Name of the category to populate
            bookmarks: List of all bookmarks to search through
            base_dir: Base directory where category files are stored
            limit: Maximum candidates to show per session
            threshold: Minimum similarity score to consider

        Returns:
            True if any bookmarks were moved, False otherwise
        """
        candidates = self.find_category_candidates(
            category_name, bookmarks, limit, threshold
        )

        if not candidates:
            print(
                f"No high-confidence candidates found for '{category_name}' category."
            )
            return False

        print(
            f"\nFound {len(candidates)} potential matches for '{category_name}' category:\n"
        )

        for i, (bookmark, score) in enumerate(candidates, 1):
            print(f'{i}. [{score:.2f}] "{bookmark.title}"')
            if bookmark.source_file:
                source_name = os.path.basename(bookmark.source_file)
                print(f"   From: {source_name}")
            print(f"   URL: {bookmark.url}")
            if bookmark.description:
                desc = (
                    bookmark.description[:100] + "..."
                    if len(bookmark.description) > 100
                    else bookmark.description
                )
                print(f"   Description: {desc}")
            print()

        # Get user selection
        while True:
            choice = (
                input("Move bookmarks to category? [y/N/s(elective)]: ").strip().lower()
            )

            if choice in ["n", ""]:
                return False
            elif choice == "y":
                selected_bookmarks = [bookmark for bookmark, _ in candidates]
                break
            elif choice == "s":
                selection = input(
                    f"Select bookmarks to move (1-{len(candidates)}, comma-separated): "
                ).strip()
                try:
                    indices = [int(x.strip()) - 1 for x in selection.split(",")]
                    selected_bookmarks = [
                        candidates[i][0] for i in indices if 0 <= i < len(candidates)
                    ]
                    if not selected_bookmarks:
                        print("No valid selections made.")
                        continue
                    break
                except (ValueError, IndexError):
                    print("Invalid selection. Please use numbers separated by commas.")
                    continue
            else:
                print("Please enter 'y', 'n', or 's'.")
                continue

        # Move the selected bookmarks
        if self.move_bookmarks_to_category(
            selected_bookmarks, category_name, bookmarks, base_dir
        ):
            print(f"✓ Moved {len(selected_bookmarks)} bookmarks to {category_name}")
            return True
        else:
            print(f"✗ Failed to move bookmarks to {category_name}")
            return False

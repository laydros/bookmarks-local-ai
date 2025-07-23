"""Bookmark importing utilities."""

from __future__ import annotations

import json
import os
import re
from typing import List

from .bookmark_loader import BookmarkLoader
from .models import Bookmark
from .web_extractor import WebExtractor
from .intelligence import BookmarkIntelligence


class BookmarkImporter:
    """Import new bookmarks into an existing collection."""

    def __init__(self, collection_path: str):
        """Initialize importer."""
        self.collection_path = collection_path
        self.loader = BookmarkLoader()
        self.web_extractor = WebExtractor()
        self.intelligence = BookmarkIntelligence()
        self.intelligence.load_bookmarks(collection_path)

    def _parse_new_bookmarks(self, file_path: str) -> List[Bookmark]:
        """Parse bookmarks from various supported formats."""
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()

        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return [Bookmark.from_dict(b) for b in data]
        except Exception:  # noqa: BLE001
            pass

        raw_lower = raw.lower()

        if "<a " in raw_lower:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(raw, "html.parser")
            bookmarks = []
            for a in soup.find_all("a"):
                href = a.get("href")
                if not href:
                    continue
                title = a.text.strip()
                tags_attr = a.get("tags") or a.get("data-tags")
                tags = tags_attr.split(",") if tags_attr else []
                bookmarks.append(Bookmark(url=href, title=title, tags=tags))
            if bookmarks:
                return bookmarks

        md_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
        matches = md_pattern.findall(raw)
        if matches:
            return [Bookmark(url=url, title=title) for title, url in matches]

        url_lines = [line.strip() for line in raw.splitlines() if line.strip()]
        if all(line.startswith("http") for line in url_lines):
            return [Bookmark(url=line) for line in url_lines]

        raise ValueError("Unrecognized bookmark format")

    def import_from_file(
        self, new_bookmarks_file: str, check_duplicates: bool = True
    ) -> tuple[List[str], List[str]]:
        """Import bookmarks from JSON, HTML, Markdown, or plain URL files."""
        bookmarks = self._parse_new_bookmarks(new_bookmarks_file)

        dead_links: List[str] = []
        skipped_duplicates: List[str] = []

        for bm in bookmarks:
            if not self.web_extractor.is_valid_url(bm.url):
                dead_links.append(bm.url)
                continue

            if check_duplicates:
                duplicate = self.intelligence.is_duplicate(bm)
                if duplicate:
                    skipped_duplicates.append(
                        f"{bm.url} (duplicate of existing bookmark: {duplicate.title})"
                    )
                    continue

            if not bm.title or not bm.description:
                title, desc = self.web_extractor.extract_content(bm.url)
                if not bm.title:
                    bm.title = title
                if not bm.description:
                    bm.description = desc

            if not bm.tags:
                domain = self.web_extractor.extract_domain(bm.url)
                if domain:
                    bm.tags = [domain]

            suggestions = self.intelligence.suggest_categorization(bm, 1)
            filename = "uncategorized.json"
            if suggestions:
                filename = suggestions[0][0]

            target_path = (
                os.path.join(self.collection_path, filename)
                if os.path.isdir(self.collection_path)
                else self.collection_path
            )

            existing = []
            if os.path.exists(target_path):
                existing = self.loader.load_from_file(target_path)

            bm.source_file = os.path.basename(target_path)
            existing.append(bm)
            self.loader.save_to_file(existing, target_path)

            self.intelligence.bookmarks.append(bm)

        return dead_links, skipped_duplicates

    @staticmethod
    def print_summary(dead_links: List[str], skipped_duplicates: List[str]) -> None:
        """Print summary of import results."""
        print("\nImport Summary")

        if not dead_links and not skipped_duplicates:
            print("All bookmarks were successfully imported.")
        else:
            if dead_links:
                print("The following links were unreachable:")
                for link in dead_links:
                    print(f"- {link}")

            if skipped_duplicates:
                print("\nThe following bookmarks were skipped as duplicates:")
                for duplicate in skipped_duplicates:
                    print(f"- {duplicate}")

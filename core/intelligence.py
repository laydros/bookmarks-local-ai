"""Bookmark intelligence core functionality."""

from __future__ import annotations

import logging
import os
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from .bookmark_loader import BookmarkLoader
from .models import Bookmark, DuplicateGroup, SearchResult
from .vector_store import VectorStore
from .web_extractor import WebExtractor
from .spinner import Spinner
from .category_manager import CategoryManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Disable ChromaDB telemetry noise
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_SERVER_NOFILE"] = "1"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


class BookmarkIntelligence:
    """Smart analysis and search for bookmark collections."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
    ) -> None:
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model

        self.loader = BookmarkLoader()
        self.vector_store = VectorStore(
            collection_name="bookmarks_intelligence",
            ollama_url=ollama_url,
            embedding_model=embedding_model,
        )
        self.category_manager = CategoryManager(self.vector_store, self.loader)

        self.bookmarks: List[Bookmark] = []
        self.indexed = False
        self.input_path: Optional[str] = None

        logger.info(f"Initialized BookmarkIntelligence with {embedding_model}")

    def load_bookmarks(self, path: str) -> bool:
        """Load bookmarks from file or directory."""
        try:
            if os.path.isfile(path):
                self.bookmarks = self.loader.load_from_file(path)
            elif os.path.isdir(path):
                self.bookmarks = self.loader.load_from_directory(path)
            else:
                logger.error(f"Path not found: {path}")
                return False

            self.input_path = path
            logger.info(f"Loaded {len(self.bookmarks)} bookmarks")
            return True

        except Exception as e:  # noqa: BLE001
            logger.error(f"Error loading bookmarks: {e}")
            return False

    def _ensure_indexed(self) -> bool:
        """Ensure bookmarks are indexed in vector store."""
        if not self.indexed and self.bookmarks:
            with Spinner("Indexing bookmarks..."):
                if not self.vector_store.rebuild_from_bookmarks(self.bookmarks):
                    logger.error("Failed to index bookmarks")
                    return False
                self.indexed = True
        return True

    def search(self, query: str, n_results: int = 10) -> SearchResult:
        """Search bookmarks using semantic similarity."""
        if not self._ensure_indexed():
            return SearchResult(query=query, similar_bookmarks=[], total_results=0)

        try:
            with Spinner(f"Searching for '{query}'..."):
                return self.vector_store.search(query, n_results)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Search failed: {e}")
            return SearchResult(query=query, similar_bookmarks=[], total_results=0)

    def find_duplicates(
        self, similarity_threshold: float = 0.85
    ) -> List[DuplicateGroup]:
        """Find potential duplicate bookmarks."""
        with Spinner("Finding duplicates..."):
            duplicates: List[DuplicateGroup] = []

            url_groups: dict[str, list[Bookmark]] = defaultdict(list)
            for bookmark in self.bookmarks:
                if bookmark.url:
                    url_groups[bookmark.url].append(bookmark)

            for url, bookmarks in url_groups.items():
                if len(bookmarks) > 1:
                    duplicates.append(
                        DuplicateGroup(
                            bookmarks=bookmarks,
                            similarity_score=1.0,
                            reason="exact_url",
                        )
                    )

            title_groups: dict[str, list[Bookmark]] = defaultdict(list)
            for bookmark in self.bookmarks:
                if bookmark.title:
                    normalized_title = bookmark.title.lower().strip()
                    title_groups[normalized_title].append(bookmark)

            processed_urls = {b.url for group in duplicates for b in group.bookmarks}
            for title, bookmarks in title_groups.items():
                if len(bookmarks) > 1:
                    unique_bookmarks = [
                        b for b in bookmarks if b.url not in processed_urls
                    ]
                    if len(unique_bookmarks) > 1:
                        duplicates.append(
                            DuplicateGroup(
                                bookmarks=unique_bookmarks,
                                similarity_score=0.9,
                                reason="similar_title",
                            )
                        )

        return duplicates

    def is_duplicate(
        self, new_bookmark: Bookmark, similarity_threshold: float = 0.85
    ) -> Optional[Bookmark]:
        """Check if a single bookmark is a duplicate."""
        for bookmark in self.bookmarks:
            if bookmark.url and new_bookmark.url and bookmark.url == new_bookmark.url:
                return bookmark

        if new_bookmark.title:
            normalized_new_title = new_bookmark.title.lower().strip()
            for bookmark in self.bookmarks:
                if bookmark.title:
                    normalized_title = bookmark.title.lower().strip()
                    if normalized_new_title == normalized_title:
                        return bookmark

        if self._ensure_indexed() and new_bookmark.description:
            try:
                search_content = (
                    f"{new_bookmark.title} {new_bookmark.description}".strip()
                )
                if search_content:
                    results = self.vector_store.search(search_content, n_results=3)

                    for result in results:
                        if result.get("distances") and len(result["distances"][0]) > 0:
                            distance = result["distances"][0][0]
                            similarity = 1.0 - distance

                            if similarity >= similarity_threshold:
                                result_id = result["ids"][0][0]
                                for bookmark in self.bookmarks:
                                    if (
                                        bookmark.url == result_id
                                        or str(hash(bookmark.url)) == result_id
                                    ):
                                        return bookmark
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Vector similarity check failed: {e}")

        return None

    def analyze_collection(self) -> Dict:
        """Analyze the bookmark collection for insights."""
        if not self.bookmarks:
            return {}

        with Spinner("Analyzing collection..."):
            total = len(self.bookmarks)
            enriched = len([b for b in self.bookmarks if b.is_enriched])

            domain_counts: Counter[str] = Counter()
            for bookmark in self.bookmarks:
                domain = bookmark.domain
                if domain:
                    domain_counts[domain] += 1

            tag_counts: Counter[str] = Counter()
            for bookmark in self.bookmarks:
                if bookmark.tags:
                    for tag in bookmark.tags:
                        tag_counts[tag.lower()] += 1

            file_counts: Counter[str] = Counter()
            for bookmark in self.bookmarks:
                if bookmark.source_file:
                    file_counts[bookmark.source_file] += 1

        return {
            "total_bookmarks": total,
            "enriched_bookmarks": enriched,
            "enrichment_percentage": (enriched / total) * 100 if total > 0 else 0,
            "unique_domains": len(domain_counts),
            "top_domains": domain_counts.most_common(10),
            "unique_tags": len(tag_counts),
            "top_tags": tag_counts.most_common(20),
            "files": len(file_counts),
            "file_distribution": dict(file_counts),
        }

    def create_category(
        self, category_name: str, output_dir: str | None = None
    ) -> bool:
        """Create a new empty category file."""
        if not output_dir:
            if self.input_path:
                if os.path.isdir(self.input_path):
                    output_dir = self.input_path
                else:
                    output_dir = os.path.dirname(self.input_path)
            else:
                output_dir = "."

        return self.category_manager.create_category(category_name, output_dir)

    def suggest_categorization(
        self, new_bookmark: Bookmark, n_suggestions: int = 3
    ) -> List[Tuple[str, float]]:
        """Suggest which file/category a new bookmark should belong to."""
        if not self._ensure_indexed():
            return []

        with Spinner("Finding suggestions..."):
            query = f"{new_bookmark.title} {new_bookmark.content_text}"
            search_result = self.vector_store.search(query, n_results=10)

            if not search_result.similar_bookmarks:
                return []

            file_scores: dict[str, float] = defaultdict(float)
            for similar in search_result.similar_bookmarks:
                if similar.bookmark.source_file:
                    file_scores[
                        similar.bookmark.source_file
                    ] += similar.similarity_score

            max_score = max(file_scores.values()) if file_scores else 1.0
            normalized_scores = [
                (f, score / max_score) for f, score in file_scores.items()
            ]

            return sorted(normalized_scores, key=lambda x: x[1], reverse=True)[
                :n_suggestions
            ]

    def _interactive_search(self, query: str) -> None:
        """Handle interactive search command."""
        result = self.search(query)

        if not result.similar_bookmarks:
            print("No results found.")
            return

        print(f"Found {len(result.similar_bookmarks)} results:")
        for i, similar in enumerate(result.similar_bookmarks, 1):
            bookmark = similar.bookmark
            print(f"\n{i}. {bookmark.title}")
            print(f"   URL: {bookmark.url}")
            print(f"   Score: {similar.similarity_score:.3f}")
            if bookmark.tags:
                print(f"   Tags: {', '.join(bookmark.tags)}")
            if bookmark.source_file:
                print(f"   File: {bookmark.source_file}")

    def _interactive_duplicates(self) -> None:
        """Handle interactive duplicates command."""
        duplicates = self.find_duplicates()

        if not duplicates:
            print("No duplicates found.")
            return

        print(f"Found {len(duplicates)} duplicate groups:")
        removed: List[Bookmark] = []
        for i, group in enumerate(duplicates, 1):
            reason = group.reason.replace("_", " ").title()
            print(f"\n{i}. {reason} (score: {group.similarity_score:.3f})")
            for j, bookmark in enumerate(group.bookmarks, 1):
                print(f"   {j}. {bookmark.title}")
                print(f"      URL: {bookmark.url}")
                print(f"      File: {bookmark.source_file}")

            while True:
                choice = input("Select bookmark to delete (0 to skip): ").strip()
                if choice.isdigit():
                    index = int(choice)
                    if 0 <= index <= len(group.bookmarks):
                        break
                print("Please enter a valid number.")

            if index > 0:
                to_remove = group.bookmarks[index - 1]
                if to_remove in self.bookmarks:
                    self.bookmarks.remove(to_remove)
                    removed.append(to_remove)
                    print(f"Removed '{to_remove.title}'")

        if removed:
            print(f"\nRemoved {len(removed)} bookmarks.")
            if self.input_path:
                print("Saving changes...")
                if os.path.isfile(self.input_path):
                    if self.loader.save_to_file(self.bookmarks, self.input_path):
                        print(f"Changes saved to {self.input_path}")
                    else:
                        print(f"Error saving changes to {self.input_path}")
                elif os.path.isdir(self.input_path):
                    if self.loader.save_by_source_file(self.bookmarks, self.input_path):
                        print(f"Changes saved to files in {self.input_path}")
                    else:
                        print(f"Error saving changes to {self.input_path}")
            else:
                print("Warning: No input path stored, changes not saved to disk")
        else:
            print("\nNo bookmarks removed.")

    def _interactive_analyze(self) -> None:
        """Handle interactive analyze command."""
        print("\n📊 Analyzing collection...")
        analysis = self.analyze_collection()

        if not analysis:
            print("No bookmarks to analyze.")
            return

        print(f"Total bookmarks: {analysis['total_bookmarks']}")
        print(
            "Enriched: "
            f"{analysis['enriched_bookmarks']} "
            f"({analysis['enrichment_percentage']:.1f}%)"
        )
        print(f"Unique domains: {analysis['unique_domains']}")
        print(f"Unique tags: {analysis['unique_tags']}")
        print(f"Files: {analysis['files']}")

        print("\nTop domains:")
        for domain, count in analysis["top_domains"]:
            print(f"  {domain}: {count}")

        print("\nTop tags:")
        for tag, count in analysis["top_tags"][:10]:
            print(f"  {tag}: {count}")

    def _interactive_categorize(self, url: str) -> None:
        """Handle interactive categorize command."""
        temp_bookmark = Bookmark(url=url, title="", description="")

        with Spinner(f"Extracting content from {url}..."):
            try:
                web_extractor = WebExtractor()
                title, description = web_extractor.extract_content(url)
                temp_bookmark.title = title
                temp_bookmark.description = description
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not extract content from {url}: {e}")

        suggestions = self.suggest_categorization(temp_bookmark)

        if not suggestions:
            print("No suggestions available.")
            return

        print("\nSuggested categories:")
        for i, (filename, confidence) in enumerate(suggestions, 1):
            print(f"  {i}. {filename} (confidence: {confidence:.3f})")

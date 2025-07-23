#!/usr/bin/env python3
"""
Bookmark Intelligence - Smart search, duplicate detection, and analysis tools
"""

import argparse
import logging
import os
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from core.bookmark_loader import BookmarkLoader
from core.models import Bookmark, DuplicateGroup, SearchResult
from core.vector_store import VectorStore
from core.web_extractor import WebExtractor
from core.spinner import Spinner
from core.category_suggester import CategorySuggester
from core.category_manager import CategoryManager

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
    ):
        """
        Initialize bookmark intelligence.

        Args:
            ollama_url: URL for Ollama API
            embedding_model: Model for embeddings
        """
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model

        # Initialize components
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
        """
        Load bookmarks from file or directory.

        Args:
            path: File path or directory path

        Returns:
            True if successful, False otherwise
        """
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

        except Exception as e:
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
        """
        Search bookmarks using semantic similarity.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            SearchResult object
        """
        if not self._ensure_indexed():
            return SearchResult(query=query, similar_bookmarks=[], total_results=0)

        try:
            with Spinner(f"Searching for '{query}'..."):
                return self.vector_store.search(query, n_results)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return SearchResult(query=query, similar_bookmarks=[], total_results=0)

    def find_duplicates(
        self, similarity_threshold: float = 0.85
    ) -> List[DuplicateGroup]:
        """
        Find potential duplicate bookmarks.

        Args:
            similarity_threshold: Minimum similarity score to consider duplicates

        Returns:
            List of DuplicateGroup objects
        """
        with Spinner("Finding duplicates..."):
            duplicates = []

            # Group by exact URL
            url_groups = defaultdict(list)
            for bookmark in self.bookmarks:
                if bookmark.url:
                    url_groups[bookmark.url].append(bookmark)

            # Add URL duplicates
            for url, bookmarks in url_groups.items():
                if len(bookmarks) > 1:
                    duplicates.append(
                        DuplicateGroup(
                            bookmarks=bookmarks,
                            similarity_score=1.0,
                            reason="exact_url",
                        )
                    )

            # Group by similar titles
            title_groups = defaultdict(list)
            for bookmark in self.bookmarks:
                if bookmark.title:
                    # Simple normalization
                    normalized_title = bookmark.title.lower().strip()
                    title_groups[normalized_title].append(bookmark)

            # Add title duplicates (excluding those already found by URL)
            processed_urls = set()
            for url_group in duplicates:
                for bookmark in url_group.bookmarks:
                    processed_urls.add(bookmark.url)

            for title, bookmarks in title_groups.items():
                if len(bookmarks) > 1:
                    # Filter out already processed URLs
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

            # TODO: Add content similarity detection using vector search
            # This would require comparing embeddings of all bookmarks

        return duplicates

    def is_duplicate(self, new_bookmark: Bookmark, similarity_threshold: float = 0.85) -> Optional[Bookmark]:
        """
        Check if a single bookmark is a duplicate of existing bookmarks.
        
        Args:
            new_bookmark: Bookmark to check for duplicates
            similarity_threshold: Minimum similarity score to consider duplicates
            
        Returns:
            Existing bookmark if duplicate found, None otherwise
        """
        # Check exact URL match first (fastest)
        for bookmark in self.bookmarks:
            if bookmark.url and new_bookmark.url and bookmark.url == new_bookmark.url:
                return bookmark
                
        # Check similar title (fast)
        if new_bookmark.title:
            normalized_new_title = new_bookmark.title.lower().strip()
            for bookmark in self.bookmarks:
                if bookmark.title:
                    normalized_title = bookmark.title.lower().strip()
                    if normalized_new_title == normalized_title:
                        return bookmark
        
        # Check content similarity using vector search (slower but more thorough)
        if self._ensure_indexed() and new_bookmark.description:
            try:
                search_content = f"{new_bookmark.title} {new_bookmark.description}".strip()
                if search_content:
                    results = self.vector_store.search(search_content, n_results=3)
                    
                    for result in results:
                        if result.get('distances') and len(result['distances'][0]) > 0:
                            # ChromaDB uses distance (lower is more similar)
                            # Convert to similarity score
                            distance = result['distances'][0][0]
                            similarity = 1.0 - distance
                            
                            if similarity >= similarity_threshold:
                                # Find the matching bookmark
                                result_id = result['ids'][0][0]
                                for bookmark in self.bookmarks:
                                    if bookmark.url == result_id or str(hash(bookmark.url)) == result_id:
                                        return bookmark
            except Exception as e:
                logger.warning(f"Vector similarity check failed: {e}")
        
        return None

    def analyze_collection(self) -> Dict:
        """
        Analyze the bookmark collection for insights.

        Returns:
            Dictionary with analysis results
        """
        if not self.bookmarks:
            return {}

        with Spinner("Analyzing collection..."):
            # Basic statistics
            total = len(self.bookmarks)
            enriched = len([b for b in self.bookmarks if b.is_enriched])

            # Domain analysis
            domain_counts = Counter()
            for bookmark in self.bookmarks:
                domain = bookmark.domain
                if domain:
                    domain_counts[domain] += 1

            # Tag analysis
            tag_counts = Counter()
            for bookmark in self.bookmarks:
                if bookmark.tags:
                    for tag in bookmark.tags:
                        tag_counts[tag.lower()] += 1

            # File distribution
            file_counts = Counter()
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

    def create_category(self, category_name: str, output_dir: str = None) -> bool:
        """
        Create a new empty category file.
        
        Args:
            category_name: Name of the category (with or without .json extension)
            output_dir: Directory to create the file in (defaults to input_path)
            
        Returns:
            True if successful, False otherwise
        """
        # Use input path as default output directory
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
        """
        Suggest which file/category a new bookmark should belong to.

        Args:
            new_bookmark: Bookmark to categorize
            n_suggestions: Number of suggestions to return

        Returns:
            List of (filename, confidence_score) tuples
        """
        if not self._ensure_indexed():
            return []

        with Spinner("Finding suggestions..."):
            # Search for similar bookmarks
            query = f"{new_bookmark.title} {new_bookmark.content_text}"
            search_result = self.vector_store.search(query, n_results=10)

            if not search_result.similar_bookmarks:
                return []

            # Count file occurrences weighted by similarity
            file_scores = defaultdict(float)
            for similar in search_result.similar_bookmarks:
                if similar.bookmark.source_file:
                    file_scores[
                        similar.bookmark.source_file
                    ] += similar.similarity_score

            # Normalize scores
            max_score = max(file_scores.values()) if file_scores else 1.0
            normalized_scores = [
                (f, score / max_score) for f, score in file_scores.items()
            ]

            # Return top suggestions
            return sorted(normalized_scores, key=lambda x: x[1], reverse=True)[
                :n_suggestions
            ]

    def interactive_mode(self):
        """Run interactive query interface."""
        print("🔍 Bookmark Intelligence - Interactive Mode")
        print("Commands: search <query>, duplicates, analyze, categorize <url>, create <category>, quit")
        print("-" * 60)

        while True:
            try:
                command = input("\n> ").strip()

                if command.lower() in ["quit", "exit", "q"]:
                    break

                elif command.lower() == "analyze":
                    self._interactive_analyze()

                elif command.lower() == "duplicates":
                    self._interactive_duplicates()

                elif command.startswith("search "):
                    query = command[7:].strip()
                    if query:
                        self._interactive_search(query)
                    else:
                        print("Please provide a search query")

                elif command.startswith("categorize "):
                    url = command[11:].strip()
                    if url:
                        self._interactive_categorize(url)
                    else:
                        print("Please provide a URL")

                elif command.startswith("create "):
                    category = command[7:].strip()
                    if category:
                        if self.create_category(category):
                            print(f"✓ Created category: {category}")
                        else:
                            print(f"✗ Failed to create category: {category}")
                    else:
                        print("Please provide a category name")

                elif command.lower() == "help":
                    print("Available commands:")
                    print("  search <query>     - Search bookmarks")
                    print("  duplicates         - Find duplicate bookmarks")
                    print("  analyze           - Analyze collection")
                    print("  categorize <url>  - Suggest category for URL")
                    print("  create <category>  - Create new empty category file")
                    print("  quit              - Exit interactive mode")

                else:
                    print(
                        f"Unknown command: {command}. Type 'help' for available commands."
                    )

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")

        print("\nGoodbye!")

    def _interactive_search(self, query: str):
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

    def _interactive_duplicates(self):
        """Handle interactive duplicates command."""
        duplicates = self.find_duplicates()

        if not duplicates:
            print("No duplicates found.")
            return

        print(f"Found {len(duplicates)} duplicate groups:")
        removed: List[Bookmark] = []
        for i, group in enumerate(duplicates, 1):
            print(
                f"\n{i}. {group.reason.replace('_', ' ').title()} (score: {group.similarity_score:.3f})"
            )
            for j, bookmark in enumerate(group.bookmarks, 1):
                print(f"   {j}. {bookmark.title}")
                print(f"      URL: {bookmark.url}")
                print(f"      File: {bookmark.source_file}")

            # Prompt user to optionally remove one of the duplicates
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
            # Save changes back to files
            if self.input_path:
                print("Saving changes...")
                if os.path.isfile(self.input_path):
                    # Single file - save all bookmarks back to the same file
                    if self.loader.save_to_file(self.bookmarks, self.input_path):
                        print(f"Changes saved to {self.input_path}")
                    else:
                        print(f"Error saving changes to {self.input_path}")
                elif os.path.isdir(self.input_path):
                    # Directory - save bookmarks back to their original files
                    if self.loader.save_by_source_file(self.bookmarks, self.input_path):
                        print(f"Changes saved to files in {self.input_path}")
                    else:
                        print(f"Error saving changes to {self.input_path}")
            else:
                print("Warning: No input path stored, changes not saved to disk")
        else:
            print("\nNo bookmarks removed.")

    def _interactive_analyze(self):
        """Handle interactive analyze command."""
        print("\n📊 Analyzing collection...")
        analysis = self.analyze_collection()

        if not analysis:
            print("No bookmarks to analyze.")
            return

        print(f"Total bookmarks: {analysis['total_bookmarks']}")
        print(
            f"Enriched: {analysis['enriched_bookmarks']} ({analysis['enrichment_percentage']:.1f}%)"
        )
        print(f"Unique domains: {analysis['unique_domains']}")
        print(f"Unique tags: {analysis['unique_tags']}")
        print(f"Files: {analysis['files']}")

        print(f"\nTop domains:")
        for domain, count in analysis["top_domains"]:
            print(f"  {domain}: {count}")

        print(f"\nTop tags:")
        for tag, count in analysis["top_tags"][:10]:
            print(f"  {tag}: {count}")

    def _interactive_categorize(self, url: str):
        """Handle interactive categorize command."""
        # Create a temporary bookmark for categorization
        temp_bookmark = Bookmark(url=url, title="", description="")

        # Try to extract content
        with Spinner(f"Extracting content from {url}..."):
            try:
                web_extractor = WebExtractor()
                title, description = web_extractor.extract_content(url)
                temp_bookmark.title = title
                temp_bookmark.description = description
            except Exception as e:
                logger.warning(f"Could not extract content from {url}: {e}")

        suggestions = self.suggest_categorization(temp_bookmark)

        if not suggestions:
            print("No suggestions available.")
            return

        print("\nSuggested categories:")
        for i, (filename, confidence) in enumerate(suggestions, 1):
            print(f"  {i}. {filename} (confidence: {confidence:.3f})")


def main():
    """Main function to run bookmark intelligence."""
    parser = argparse.ArgumentParser(
        description="Bookmark Intelligence - Smart search and analysis"
    )
    parser.add_argument(
        "input", help="Input JSON file or directory with bookmark files"
    )
    parser.add_argument("--search", "-s", help="Search query")
    parser.add_argument(
        "--duplicates", "-d", action="store_true", help="Find duplicate bookmarks"
    )
    parser.add_argument(
        "--analyze", "-a", action="store_true", help="Analyze bookmark collection"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Interactive mode"
    )
    parser.add_argument("--categorize", "-c", help="Suggest category for URL")
    parser.add_argument(
        "--embedding-model",
        default="nomic-embed-text",
        help="Embedding model for Ollama (default: nomic-embed-text)",
    )
    parser.add_argument(
        "--results",
        "-n",
        type=int,
        default=10,
        help="Number of search results to return (default: 10)",
    )
    parser.add_argument(
        "--suggest-categories",
        action="store_true",
        help="Propose new categories based on bookmark content",
    )
    parser.add_argument(
        "--use-kmeans", type=int, help="Use k-means with the given k value"
    )
    parser.add_argument(
        "--output-dir",
        help="Directory for new category files (defaults to input directory)",
    )
    parser.add_argument(
        "--output-md", help="Write category suggestions to a markdown file"
    )
    parser.add_argument(
        "--create-category", help="Create a new empty category file with the given name"
    )
    parser.add_argument(
        "--populate-category", help="Find and suggest bookmarks for a specific category"
    )
    parser.add_argument(
        "--limit", type=int, default=5, help="Maximum number of suggestions per run (default: 5)"
    )
    parser.add_argument(
        "--threshold", type=float, default=0.85, help="Minimum confidence threshold (default: 0.85)"
    )

    args = parser.parse_args()

    # Check if input exists
    if not os.path.exists(args.input):
        print(f"Error: Input path {args.input} not found")
        return

    # Initialize intelligence system
    try:
        intelligence = BookmarkIntelligence(embedding_model=args.embedding_model)

        if not intelligence.load_bookmarks(args.input):
            print("Failed to load bookmarks")
            return

    except Exception as e:
        logger.error(f"Failed to initialize intelligence system: {e}")
        return

    # Execute commands
    try:
        if args.search:
            result = intelligence.search(args.search, args.results)

            if result.similar_bookmarks:
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
            else:
                print("No results found.")

        elif args.duplicates:
            print("🔍 Finding duplicates...")
            duplicates = intelligence.find_duplicates()

            if duplicates:
                print(f"Found {len(duplicates)} duplicate groups:")
                for i, group in enumerate(duplicates, 1):
                    print(f"\n{i}. {group}")
                    for j, bookmark in enumerate(group.bookmarks, 1):
                        print(f"   {j}. {bookmark.title} ({bookmark.url})")
                        print(f"      File: {bookmark.source_file}")
            else:
                print("No duplicates found.")

        elif args.analyze:
            print("📊 Analyzing collection...")
            analysis = intelligence.analyze_collection()

            if analysis:
                print(f"Total bookmarks: {analysis['total_bookmarks']}")
                print(
                    f"Enriched: {analysis['enriched_bookmarks']} ({analysis['enrichment_percentage']:.1f}%)"
                )
                print(f"Unique domains: {analysis['unique_domains']}")
                print(f"Unique tags: {analysis['unique_tags']}")
                print(f"Files: {analysis['files']}")

                print(f"\nTop domains:")
                for domain, count in analysis["top_domains"]:
                    print(f"  {domain}: {count}")

                print(f"\nTop tags:")
                for tag, count in analysis["top_tags"][:10]:
                    print(f"  {tag}: {count}")
            else:
                print("No bookmarks to analyze.")

        elif args.categorize:
            # Create temporary bookmark
            temp_bookmark = Bookmark(url=args.categorize, title="", description="")

            # Try to extract content
            with Spinner(f"Extracting content from {args.categorize}..."):
                try:
                    web_extractor = WebExtractor()
                    title, description = web_extractor.extract_content(args.categorize)
                    temp_bookmark.title = title
                    temp_bookmark.description = description
                except Exception as e:
                    logger.warning(f"Could not extract content: {e}")

            suggestions = intelligence.suggest_categorization(temp_bookmark)

            if suggestions:
                print("Suggested categories:")
                for i, (filename, confidence) in enumerate(suggestions, 1):
                    print(f"  {i}. {filename} (confidence: {confidence:.3f})")
            else:
                print("No suggestions available.")

        elif args.suggest_categories:
            with Spinner("Analyzing bookmarks and generating category suggestions..."):
                suggester = CategorySuggester(intelligence.vector_store)
                suggestions = suggester.suggest(intelligence.bookmarks, args.use_kmeans)

            if not suggestions:
                print("No category suggestions available.")
            else:
                if args.output_md:
                    with open(args.output_md, "w", encoding="utf-8") as f:
                        f.write("# Suggested Categories\n\n")
                        for s in suggestions:
                            f.write(f"## {s.name}\n\n{s.description}\n\n")
                            for b in s.bookmarks:
                                f.write(f"- [{b.title}]({b.url})\n")
                            if s.source_files:
                                f.write(
                                    "\nFiles: " + ", ".join(s.source_files) + "\n\n"
                                )
                    print(f"Suggestions written to {args.output_md}")
                else:
                    print("\nProposed categories:")
                    for s in suggestions:
                        print(f"\n### {s.name}\n{s.description}")
                        for b in s.bookmarks:
                            print(f"- {b.title} ({b.url})")
                        if s.source_files:
                            print("Files: " + ", ".join(s.source_files))

                choice = (
                    input("Generate empty .json files for these new categories? [y/N] ")
                    .strip()
                    .lower()
                )
                if choice == "y":
                    # Default output directory to input directory if not specified
                    output_dir = args.output_dir
                    if not output_dir:
                        if os.path.isdir(args.input):
                            output_dir = args.input
                        else:
                            output_dir = os.path.dirname(args.input)
                    
                    suggester.create_placeholder_files(suggestions, output_dir)
                    print(f"Created files in {output_dir}")

        elif args.create_category:
            if intelligence.create_category(args.create_category):
                print(f"✓ Created category: {args.create_category}")
            else:
                print(f"✗ Failed to create category: {args.create_category}")

        elif args.populate_category:
            # Determine base directory
            if os.path.isdir(args.input):
                base_dir = args.input
            else:
                base_dir = os.path.dirname(args.input)
            
            moved = intelligence.category_manager.populate_category_interactive(
                args.populate_category,
                intelligence.bookmarks,
                base_dir,
                limit=args.limit,
                threshold=args.threshold
            )
            
            if moved:
                print(f"\n✓ Successfully populated {args.populate_category} category")
                # Re-index after moving bookmarks
                intelligence.indexed = False
                intelligence._ensure_indexed()
            else:
                print(f"\n✗ No bookmarks were moved to {args.populate_category}")

        elif args.interactive:
            intelligence.interactive_mode()

        else:
            print("No command specified. Use --help for available options.")

    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
    except Exception as e:
        logger.error(f"Operation failed: {e}")


if __name__ == "__main__":
    main()

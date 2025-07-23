#!/usr/bin/env python3
"""Bookmark Intelligence command line interface."""

import argparse
import logging
import os

from core.intelligence import BookmarkIntelligence
from core.models import Bookmark
from core.web_extractor import WebExtractor
from core.spinner import Spinner
from core.category_suggester import CategorySuggester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_SERVER_NOFILE"] = "1"
logging.getLogger("chromadb.telemetry.posthog").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)


def main() -> None:
    """Run bookmark intelligence CLI."""
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
        "--create-category",
        help="Create a new empty category file (e.g., '3dprinting' creates '3dprinting.json')",
    )
    parser.add_argument(
        "--populate-category",
        help="Find and suggest bookmarks for a specific category (e.g., '3dprinting' or '3dprinting.json')",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Maximum number of suggestions per run (default: 5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Minimum confidence threshold (default: 0.85)",
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input path {args.input} not found")
        return

    try:
        intelligence = BookmarkIntelligence(embedding_model=args.embedding_model)
        if not intelligence.load_bookmarks(args.input):
            print("Failed to load bookmarks")
            return
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to initialize intelligence system: {e}")
        return

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
                print("\nTop domains:")
                for domain, count in analysis["top_domains"]:
                    print(f"  {domain}: {count}")
                print("\nTop tags:")
                for tag, count in analysis["top_tags"][:10]:
                    print(f"  {tag}: {count}")
            else:
                print("No bookmarks to analyze.")

        elif args.categorize:
            temp_bookmark = Bookmark(url=args.categorize, title="", description="")
            with Spinner(f"Extracting content from {args.categorize}..."):
                try:
                    web_extractor = WebExtractor()
                    title, description = web_extractor.extract_content(args.categorize)
                    temp_bookmark.title = title
                    temp_bookmark.description = description
                except Exception as e:  # noqa: BLE001
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
            if os.path.isdir(args.input):
                base_dir = args.input
            else:
                base_dir = os.path.dirname(args.input)
            if not intelligence._ensure_indexed():
                print("Failed to build search index")
                return
            moved = intelligence.category_manager.populate_category_interactive(
                args.populate_category,
                intelligence.bookmarks,
                base_dir,
                limit=args.limit,
                threshold=args.threshold,
            )
            if moved:
                print(f"\n✓ Successfully populated {args.populate_category} category")
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
    except Exception as e:  # noqa: BLE001
        logger.error(f"Operation failed: {e}")


if __name__ == "__main__":
    main()

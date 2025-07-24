"""Core enrichment classes."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import List, Optional

import ollama
import requests
from bs4 import BeautifulSoup

from .bookmark_loader import BookmarkLoader
from .models import Bookmark
from .vector_store import VectorStore
from .web_extractor import WebExtractor
from .spinner import Spinner

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("ollama").setLevel(logging.WARNING)


class ProcessingSummary:
    """Tracks warnings, errors, and statistics during processing."""

    def __init__(self) -> None:
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.skipped_no_url: List[str] = []
        self.web_extraction_failures: List[str] = []
        self.enrichment_failures: List[str] = []
        self.successful_enrichments: List[str] = []
        self.already_enriched: List[str] = []

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_skipped_no_url(self, title: str) -> None:
        """Track bookmark skipped due to missing URL."""
        self.skipped_no_url.append(title or "Unknown title")

    def add_web_extraction_failure(self, url: str, reason: str) -> None:
        """Track web extraction failure."""
        self.web_extraction_failures.append(f"{url}: {reason}")

    def add_enrichment_failure(self, title: str, url: str, reason: str) -> None:
        """Track enrichment failure."""
        self.enrichment_failures.append(f"{title} ({url}): {reason}")

    def add_successful_enrichment(self, title: str) -> None:
        """Track successful enrichment."""
        self.successful_enrichments.append(title)

    def add_already_enriched(self, title: str) -> None:
        """Track already enriched bookmark."""
        self.already_enriched.append(title)

    def print_summary(self) -> None:
        """Print a comprehensive summary of the processing."""
        print("\n" + "=" * 80)
        print("🏁 PROCESSING SUMMARY")
        print("=" * 80)

        total_processed = (
            len(self.successful_enrichments)
            + len(self.already_enriched)
            + len(self.enrichment_failures)
            + len(self.skipped_no_url)
        )

        print("📊 STATISTICS:")
        print(f"   Total bookmarks processed: {total_processed}")
        print(f"   ✅ Successfully enriched: {len(self.successful_enrichments)}")
        print(f"   ✓  Already enriched: {len(self.already_enriched)}")
        print(f"   ❌ Failed to enrich: {len(self.enrichment_failures)}")
        print(f"   ⚠️  Skipped (no URL): {len(self.skipped_no_url)}")
        print(f"   🌐 Web extraction failures: {len(self.web_extraction_failures)}")

        if self.errors:
            print(f"\n🚨 ERRORS ({len(self.errors)}) - Require immediate attention:")
            for i, error in enumerate(self.errors, 1):
                print(f"   {i}. {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}) - May need attention:")
            for i, warning in enumerate(self.warnings, 1):
                print(f"   {i}. {warning}")

        if self.skipped_no_url:
            print(f"\n🔗 BOOKMARKS SKIPPED (No URL) ({len(self.skipped_no_url)}):")
            for i, title in enumerate(self.skipped_no_url, 1):
                print(f"   {i}. {title}")

        if self.web_extraction_failures:
            print(
                f"\n🌐 WEB EXTRACTION FAILURES ({len(self.web_extraction_failures)}):"
            )
            for i, failure in enumerate(self.web_extraction_failures, 1):
                print(f"   {i}. {failure}")

        if self.enrichment_failures:
            print(f"\n🤖 ENRICHMENT FAILURES ({len(self.enrichment_failures)}):")
            for i, failure in enumerate(self.enrichment_failures, 1):
                print(f"   {i}. {failure}")

        total_issues = (
            len(self.errors)
            + len(self.enrichment_failures)
            + len(self.web_extraction_failures)
            + len(self.skipped_no_url)
        )

        if total_issues == 0:
            print("\n🎉 SUCCESS: All bookmarks processed without issues!")
        elif len(self.successful_enrichments) > 0:
            print(
                f"\n✨ PARTIAL SUCCESS: {len(self.successful_enrichments)} "
                "bookmarks enriched"
            )
            if len(self.web_extraction_failures) > 0:
                print(
                    f"   📝 Note: {len(self.web_extraction_failures)} web extraction"
                    " issues (enrichment still completed using available data)"
                )
        elif total_issues > 0:
            print(f"\n⚠️  COMPLETED WITH ISSUES: {total_issues} items need attention")

        print("=" * 80)


class SummaryAwareWebExtractor(WebExtractor):
    """Web extractor that reports failures to ProcessingSummary."""

    def __init__(self, summary: ProcessingSummary, timeout: int = 10) -> None:
        super().__init__(timeout)
        self.summary = summary

    def extract_content(self, url: str) -> tuple[str, str]:
        """Extract content and track failures in summary."""
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            title = self._extract_title(soup)
            description = self._extract_description(soup)

            return title, description

        except requests.exceptions.Timeout:
            self.summary.add_web_extraction_failure(url, "Request timeout")
            return "", ""
        except requests.exceptions.ConnectionError as e:
            self.summary.add_web_extraction_failure(url, f"Connection error: {str(e)}")
            return "", ""
        except requests.exceptions.HTTPError as e:
            self.summary.add_web_extraction_failure(url, f"HTTP error: {str(e)}")
            return "", ""
        except requests.exceptions.RequestException as e:
            self.summary.add_web_extraction_failure(url, f"Request failed: {str(e)}")
            return "", ""
        except Exception as e:  # noqa: BLE001
            self.summary.add_web_extraction_failure(url, f"Unexpected error: {str(e)}")
            return "", ""


class BookmarkEnricher:
    """Enhanced bookmark enricher using shared modules."""

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
        llm_model: str = "llama3.1:8b",
    ) -> None:
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model
        self.llm_model = llm_model
        self.summary = ProcessingSummary()

        self.loader = BookmarkLoader()
        self.vector_store = VectorStore(
            collection_name="bookmarks_enricher",
            ollama_url=ollama_url,
            embedding_model=embedding_model,
        )
        self.web_extractor = SummaryAwareWebExtractor(self.summary)

        logger.info(f"Initialized enricher with {embedding_model} and {llm_model}")

    def enrich_bookmark(self, bookmark: Bookmark) -> Bookmark:
        """Enrich a single bookmark with description and tags."""
        if not bookmark.url:
            logger.warning(f"Skipping bookmark without URL: {bookmark.title}")
            self.summary.add_skipped_no_url(bookmark.title)
            return bookmark

        if bookmark.is_enriched:
            logger.info(f"Skipping already enriched bookmark: {bookmark.title}")
            self.summary.add_already_enriched(bookmark.title)
            return bookmark

        logger.info(f"Enriching bookmark: {bookmark.title}")

        if not bookmark.title or not bookmark.content_text:
            web_title, web_description = self.web_extractor.extract_content(
                bookmark.url
            )

            if not bookmark.title and web_title:
                bookmark.title = web_title

            if not bookmark.content_text and web_description:
                if bookmark.description:
                    bookmark.description = web_description
                else:
                    bookmark.excerpt = web_description

        query_parts = [bookmark.title, bookmark.content_text]
        query = " ".join(filter(None, query_parts))

        if not query:
            logger.warning(f"No content to query for bookmark: {bookmark.url}")
            self.summary.add_warning(
                f"No content available for bookmark: {bookmark.title} ({bookmark.url})"
            )
            return bookmark

        try:
            search_result = self.vector_store.search(query, n_results=3)
        except Exception as e:  # noqa: BLE001
            self.summary.add_error(
                f"Vector search failed for {bookmark.title}: {str(e)}"
            )
            return bookmark

        context = ""
        if search_result.similar_bookmarks:
            context = "Similar bookmarks in your collection:\n"
            for similar in search_result.similar_bookmarks:
                context += f"- {similar.bookmark.title}: {similar.content}\n"

        enrichment = self._generate_enrichment(bookmark, context)

        if enrichment:
            if not bookmark.content_text and enrichment.get("description"):
                if hasattr(bookmark, "description") and not bookmark.description:
                    bookmark.description = enrichment["description"]
                elif hasattr(bookmark, "excerpt") and not bookmark.excerpt:
                    bookmark.excerpt = enrichment["description"]
                else:
                    bookmark.description = enrichment["description"]

            if not bookmark.tags and enrichment.get("tags"):
                bookmark.tags = enrichment["tags"]

            logger.info(f"Enriched: {bookmark.title}")
            self.summary.add_successful_enrichment(bookmark.title)
        else:
            self.summary.add_enrichment_failure(
                bookmark.title, bookmark.url, "Failed to generate enrichment"
            )

        return bookmark

    def _generate_enrichment(self, bookmark: Bookmark, context: str) -> Optional[dict]:
        """Generate enrichment data using Ollama."""
        prompt = (
            "You are helping to enrich a bookmark collection. "
            "Based on the information provided, generate a concise description "
            "and relevant tags.\n\n"
            f"{context}\n\n"
            "Bookmark to enrich:\n"
            f"Title: {bookmark.title}\n"
            f"URL: {bookmark.url}\n"
            f"Content: {bookmark.content_text}\n\n"
            "Please provide:\n"
            "1. A concise, informative description (1-2 sentences)\n"
            "2. 3-5 relevant tags (single words or short phrases)\n\n"
            "Respond ONLY with valid JSON in this exact format:\n"
            '{"description": "your description here", "tags": ["tag1", "tag2", "tag3"]}'
        )
        with Spinner(f"Generating enrichment for {bookmark.title}..."):
            try:
                response = ollama.generate(
                    model=self.llm_model,
                    prompt=prompt,
                    options={"temperature": 0.3},
                )

                response_text = response["response"].strip()

                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1

                if json_start != -1 and json_end > json_start:
                    json_text = response_text[json_start:json_end]
                    return json.loads(json_text)
                logger.warning(
                    f"Could not parse JSON from response for {bookmark.title}"
                )
                return None
            except Exception as e:  # noqa: BLE001
                logger.error(f"Error generating enrichment for {bookmark.title}: {e}")
                self.summary.add_enrichment_failure(
                    bookmark.title, bookmark.url, f"LLM generation failed: {str(e)}"
                )
                return None

    def process_single_file(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        limit: Optional[int] = None,
        output_format: str = "csv",
    ) -> None:
        """Process bookmarks from a single file."""
        logger.info(f"Processing single file: {input_file}")

        bookmarks = self.loader.load_from_file(input_file)
        if not bookmarks:
            self.summary.add_error("No bookmarks loaded from file")
            self.summary.print_summary()
            return

        self._process_bookmarks(bookmarks, limit=limit)

        if output_file is None:
            base, _ = os.path.splitext(input_file)
            ext = ".csv" if output_format == "csv" else ".json"
            output_file = f"{base}_enriched{ext}"

        if self.loader.save_to_file(bookmarks, output_file):
            logger.info(f"Results saved to {output_file}")
        else:
            self.summary.add_error(f"Failed to save results to {output_file}")

        self.summary.print_summary()

    def process_directory(
        self, directory_path: str, limit: Optional[int] = None
    ) -> None:
        """Process all JSON files in a directory."""
        logger.info(f"Processing directory: {directory_path}")

        all_bookmarks = self.loader.load_from_directory(directory_path)
        if not all_bookmarks:
            self.summary.add_error("No bookmarks loaded from directory")
            self.summary.print_summary()
            return

        stats = self.loader.get_stats(all_bookmarks)
        logger.info(
            f"Loaded {stats['total']} bookmarks ({stats['enriched']} already enriched)"
        )

        self._process_bookmarks(all_bookmarks, limit=limit)

        if self.loader.save_by_source_file(all_bookmarks):
            logger.info("Results saved back to original files")
        else:
            self.summary.add_error("Failed to save results back to original files")

        self.summary.print_summary()

    def _process_bookmarks(
        self, bookmarks: List[Bookmark], limit: Optional[int] = None
    ) -> None:
        """Process a list of bookmarks (shared logic)."""
        enriched_bookmarks = self.loader.filter_enriched(bookmarks)
        if enriched_bookmarks:
            with Spinner(
                f"Building vector store from {len(enriched_bookmarks)} bookmarks..."
            ):
                try:
                    self.vector_store.rebuild_from_bookmarks(enriched_bookmarks)
                except Exception as e:  # noqa: BLE001
                    self.summary.add_error(f"Failed to build vector store: {str(e)}")
                    return

        unenriched_bookmarks = self.loader.filter_unenriched(bookmarks)
        if limit is not None and limit > 0:
            unenriched_bookmarks = unenriched_bookmarks[:limit]
        logger.info(f"Starting enrichment of {len(unenriched_bookmarks)} bookmarks...")

        for i, bookmark in enumerate(unenriched_bookmarks):
            logger.info(
                f"Processing bookmark {i+1}/{len(unenriched_bookmarks)} "
                f"from {bookmark.source_file}"
            )

            try:
                self.enrich_bookmark(bookmark)
            except Exception as e:  # noqa: BLE001
                self.summary.add_error(
                    f"Unexpected error processing {bookmark.title}: {str(e)}"
                )

            time.sleep(0.5)

        success_count = len(self.summary.successful_enrichments)
        logger.info(f"Enrichment complete! Processed {success_count} bookmarks")

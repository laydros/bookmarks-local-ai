"""Category suggestion utilities."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence

import ollama
from .models import Bookmark
from .vector_store import VectorStore
from .progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)


@dataclass
class CategorySuggestion:
    """Represents a proposed bookmark category."""

    name: str
    description: str
    bookmarks: List[Bookmark]
    source_files: Sequence[str]


class CategorySuggester:
    """Analyze bookmarks and suggest new categories."""

    def __init__(self, vector_store: VectorStore, llm_model: str = "llama3.1:8b"):
        self.vector_store = vector_store
        self.llm_model = llm_model

    def _cluster_embeddings(
        self, embeddings: List[List[float]], use_kmeans: Optional[int] = None
    ) -> List[int]:
        """Cluster embedding vectors."""
        if use_kmeans:
            from sklearn.cluster import KMeans

            kmeans = KMeans(n_clusters=use_kmeans, random_state=42)
            labels = kmeans.fit_predict(embeddings)
            return labels.tolist()

        try:
            import hdbscan

            # More reasonable cluster size: 3-15 bookmarks per cluster
            min_size = max(3, min(15, len(embeddings) // 50))
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_size,
                min_samples=max(2, min_size // 2),  # Allow some flexibility
                cluster_selection_epsilon=0.1,  # Allow slightly looser clusters
            )
            labels = clusterer.fit_predict(embeddings)

            # Count actual clusters (excluding noise -1)
            unique_labels = set(labels)
            unique_labels.discard(-1)  # Remove noise label

            logger.info(
                "HDBSCAN: %s clusters found with min_cluster_size=%s",
                len(unique_labels),
                min_size,
            )

            # Fall back to k-means if too few clusters
            if len(unique_labels) < 2:
                logger.info("Too few HDBSCAN clusters, falling back to k-means")
                raise ValueError("Insufficient clusters")

            return labels.tolist()

        except Exception as e:  # pragma: no cover - fallback path
            logger.warning(f"HDBSCAN failed ({e}), falling back to k-means")
            from sklearn.cluster import KMeans

            # Aim for 3-8 clusters for good variety without overwhelming user
            k = max(3, min(8, len(embeddings) // 100))
            if len(embeddings) < 20:
                k = max(2, len(embeddings) // 5)  # For smaller datasets

            logger.info(f"K-means: Creating {k} clusters")
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)
            return labels.tolist()

    def _generate_cluster_summary(self, bookmarks: Sequence[Bookmark]) -> dict:
        """Call LLM to get a name/description for a cluster."""
        sample = list(bookmarks)[:5]
        bullet_lines = [f"- {b.title}: {b.url}" for b in sample]

        # Extract existing category names from source files to learn naming style
        existing_names = set()
        for bookmark in bookmarks:
            if bookmark.source_file:
                # Extract filename without path and extension
                filename = os.path.basename(bookmark.source_file)
                if filename.endswith(".json"):
                    category_name = filename[:-5]  # Remove .json extension
                    existing_names.add(category_name)

        # Create examples of existing naming style
        style_examples = ""
        if existing_names:
            example_names = sorted(list(existing_names))[:5]  # Show up to 5 examples
            style_examples = (
                "Follow the existing naming style from these categories: "
                f"{', '.join(example_names)}. "
                "Match their format, length, and style conventions. "
            )

        prompt = (
            "Suggest a short category name and one sentence description for "
            "the following bookmarks. "
            + style_examples
            + "You MUST respond with ONLY valid JSON "
            + (
                "in this exact format: "
                '{"name":"category-name","description":"description"}\n\n'
            )
            + "Do not include any other text before or after the JSON.\n\n"
            + "\n".join(bullet_lines)
        )
        try:
            response = ollama.generate(
                model=self.llm_model, prompt=prompt, options={"temperature": 0.1}
            )
            text = response["response"].strip()

            # Try to extract JSON more robustly
            start = text.find("{")
            if start == -1:
                logger.warning(f"No JSON found in LLM response: {text[:100]}...")
                return {"name": "Untitled", "description": ""}

            # Find the matching closing brace
            brace_count = 0
            end = start
            for i, char in enumerate(text[start:], start):
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break

            if end <= start:
                logger.warning(f"No matching closing brace found in: {text[:100]}...")
                return {"name": "Untitled", "description": ""}

            json_text = text[start:end]
            logger.debug(f"Extracted JSON: {json_text}")

            try:
                return json.loads(json_text)
            except json.JSONDecodeError as je:
                logger.warning(f"JSON decode error: {je}. Raw JSON: {json_text}")
                # Try to fix common issues
                json_text = json_text.replace("\n", " ").replace("\r", " ")
                try:
                    return json.loads(json_text)
                except json.JSONDecodeError:
                    logger.error(
                        f"Could not parse JSON even after cleanup: {json_text}"
                    )
                    return {"name": "Untitled", "description": ""}

        except Exception as e:  # pragma: no cover - network failures
            logger.error(f"LLM generation failed: {e}")
        return {"name": "Untitled", "description": ""}

    def suggest(
        self,
        bookmarks: List[Bookmark],
        use_kmeans: Optional[int] = None,
    ) -> List[CategorySuggestion]:
        """Generate category suggestions for a list of bookmarks."""
        if not bookmarks:
            return []

        texts = [b.search_text for b in bookmarks]
        tracker = ProgressTracker(
            total=len(texts), description="Embedding bookmarks", show_progress_bar=False
        )
        embeddings: List[List[float]] = []
        for text in texts:
            vector = self.vector_store.get_embeddings([text])[0]
            embeddings.append(vector)
            tracker.update()
        tracker.finish()

        cluster_tracker = ProgressTracker(
            total=1, description="Clustering", show_progress_bar=False
        )
        labels = self._cluster_embeddings(embeddings, use_kmeans)
        cluster_tracker.update()
        cluster_tracker.finish()

        clusters: dict[int, List[int]] = {}
        for idx, label in enumerate(labels):
            if label == -1:
                continue
            clusters.setdefault(label, []).append(idx)

        # Sort clusters by size (largest first) and filter for quality
        sorted_clusters = sorted(
            clusters.items(), key=lambda x: len(x[1]), reverse=True
        )

        suggestions: List[CategorySuggestion] = []
        for cluster_id, indices in sorted_clusters:
            # Skip clusters that are too small to be meaningful
            if len(indices) < 3:
                continue

            group = [bookmarks[i] for i in indices]
            meta = self._generate_cluster_summary(group)
            source_files = sorted({b.source_file for b in group if b.source_file})

            # Skip clusters with generic/poor names
            cluster_name = meta.get("name", "Untitled")
            if cluster_name in ["Untitled", "Various", "Mixed", "General", "Other"]:
                logger.debug(f"Skipping cluster with generic name: {cluster_name}")
                continue

            suggestions.append(
                CategorySuggestion(
                    name=cluster_name,
                    description=meta.get("description", ""),
                    bookmarks=group[:5],  # Show max 5 examples
                    source_files=source_files,
                )
            )

            # Limit to max 10 suggestions to avoid overwhelming user
            if len(suggestions) >= 10:
                break

        logger.info(
            "Generated %d category suggestions from %d clusters",
            len(suggestions),
            len(sorted_clusters),
        )
        return suggestions

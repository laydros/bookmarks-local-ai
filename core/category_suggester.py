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

            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=max(2, len(embeddings) // 10 + 1)
            )
            labels = clusterer.fit_predict(embeddings)
            return labels.tolist()
        except Exception as e:  # pragma: no cover - fallback path
            logger.warning(f"HDBSCAN failed ({e}), falling back to k-means")
            from sklearn.cluster import KMeans

            k = min(5, max(2, len(embeddings) // 10 + 1))
            kmeans = KMeans(n_clusters=k, random_state=42)
            labels = kmeans.fit_predict(embeddings)
            return labels.tolist()

    def _generate_cluster_summary(self, bookmarks: Sequence[Bookmark]) -> dict:
        """Call LLM to get a name/description for a cluster."""
        sample = list(bookmarks)[:5]
        bullet_lines = [f"- {b.title}: {b.url}" for b in sample]
        prompt = (
            "Suggest a short category name and one sentence description for "
            'the following bookmarks. Respond with JSON as {"name":"...",'
            '"description":"..."}\n\n' + "\n".join(bullet_lines)
        )
        try:
            response = ollama.generate(
                model=self.llm_model, prompt=prompt, options={"temperature": 0.3}
            )
            text = response["response"].strip()
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
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

        suggestions: List[CategorySuggestion] = []
        for indices in clusters.values():
            group = [bookmarks[i] for i in indices]
            meta = self._generate_cluster_summary(group)
            source_files = sorted({b.source_file for b in group if b.source_file})
            suggestions.append(
                CategorySuggestion(
                    name=meta.get("name", "Untitled"),
                    description=meta.get("description", ""),
                    bookmarks=group[:5],
                    source_files=source_files,
                )
            )
        return suggestions

    def create_placeholder_files(
        self, suggestions: Sequence[CategorySuggestion], output_dir: str
    ) -> None:
        """Create empty JSON files for suggested categories."""
        os.makedirs(output_dir, exist_ok=True)
        for suggestion in suggestions:
            filename = f"{suggestion.name.lower().replace(' ', '_')}.json"
            path = os.path.join(output_dir, filename)
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2, ensure_ascii=False)

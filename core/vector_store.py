"""
Vector store operations using ChromaDB and Ollama.
"""

import chromadb
import ollama
import logging
from typing import List, Dict
from .models import Bookmark, SimilarBookmark, SearchResult

logger = logging.getLogger(__name__)


class VectorStore:
    """Handles vector database operations for bookmarks."""

    def __init__(
        self,
        collection_name: str = "bookmarks",
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "nomic-embed-text",
    ):
        """
        Initialize vector store.

        Args:
            collection_name: Name of ChromaDB collection
            ollama_url: URL for Ollama API
            embedding_model: Model name for embeddings
        """
        self.collection_name = collection_name
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model

        # Initialize ChromaDB
        self.client = chromadb.Client()
        self.collection = None
        self._initialize_collection()

    def _initialize_collection(self):
        """Initialize or get existing ChromaDB collection."""
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
            logger.info(f"Using existing ChromaDB collection: {self.collection_name}")
        except:
            self.collection = self.client.create_collection(name=self.collection_name)
            logger.info(f"Created new ChromaDB collection: {self.collection_name}")

    def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Get embeddings for texts using Ollama.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []
        for text in texts:
            try:
                response = ollama.embeddings(model=self.embedding_model, prompt=text)
                embeddings.append(response["embedding"])
            except Exception as e:
                logger.error(f"Error getting embedding for text: {e}")
                # Return a zero vector as fallback
                embeddings.append([0.0] * 768)  # Default embedding size
        return embeddings

    def add_bookmarks(self, bookmarks: List[Bookmark]) -> bool:
        """
        Add bookmarks to the vector store.

        Args:
            bookmarks: List of Bookmark objects to add

        Returns:
            True if successful, False otherwise
        """
        if not bookmarks:
            return True

        documents = []
        metadatas = []
        ids = []

        for bookmark in bookmarks:
            if not bookmark.url or not bookmark.search_text:
                continue

            documents.append(bookmark.search_text)
            metadatas.append(
                {
                    "url": bookmark.url,
                    "title": bookmark.title,
                    "domain": bookmark.domain,
                    "source_file": bookmark.source_file,
                    "tags": ",".join(bookmark.tags)
                    if bookmark.tags
                    else "",  # Convert list to string
                }
            )

            # Handle duplicate URLs
            bookmark_id = bookmark.url
            counter = 1
            while bookmark_id in ids:
                bookmark_id = f"{bookmark.url}_{counter}"
                counter += 1
            ids.append(bookmark_id)

        if not documents:
            logger.warning("No valid bookmarks to add to vector store")
            return False

        try:
            # Get embeddings
            embeddings = self.get_embeddings(documents)

            # Add to collection
            self.collection.add(
                documents=documents, metadatas=metadatas, ids=ids, embeddings=embeddings
            )

            logger.info(f"Added {len(documents)} bookmarks to vector store")
            return True

        except Exception as e:
            logger.error(f"Error adding bookmarks to vector store: {e}")
            return False

    def search(self, query: str, n_results: int = 10) -> SearchResult:
        """
        Search for similar bookmarks.

        Args:
            query: Search query
            n_results: Number of results to return

        Returns:
            SearchResult object
        """
        try:
            # Get query embedding
            query_embeddings = self.get_embeddings([query])

            # Search collection
            results = self.collection.query(
                query_embeddings=query_embeddings, n_results=n_results
            )

            similar_bookmarks = []
            if results["documents"] and results["documents"][0]:
                for i, (doc, metadata, distance) in enumerate(
                    zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0]
                        if results.get("distances")
                        else [0] * len(results["documents"][0]),
                    )
                ):
                    # Convert metadata back to Bookmark
                    tags_data = metadata.get("tags", "")
                    if isinstance(tags_data, list):
                        tags = tags_data
                    elif isinstance(tags_data, str):
                        tags = tags_data.split(",") if tags_data else []
                    else:
                        tags = []

                    bookmark = Bookmark(
                        url=metadata["url"],
                        title=metadata["title"],
                        tags=tags,
                        source_file=metadata.get("source_file", ""),
                    )

                    # Calculate similarity score (higher is better)
                    similarity_score = 1.0 - distance if distance else 1.0

                    similar_bookmarks.append(
                        SimilarBookmark(
                            bookmark=bookmark,
                            similarity_score=similarity_score,
                            content=doc,
                        )
                    )

            return SearchResult(
                query=query,
                similar_bookmarks=similar_bookmarks,
                total_results=len(similar_bookmarks),
            )

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return SearchResult(query=query, similar_bookmarks=[], total_results=0)

    def clear(self) -> bool:
        """
        Clear all data from the vector store.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.delete_collection(name=self.collection_name)
            self._initialize_collection()
            logger.info("Cleared vector store")
            return True
        except Exception as e:
            logger.error(f"Error clearing vector store: {e}")
            return False

    def get_stats(self) -> Dict:
        """
        Get statistics about the vector store.

        Returns:
            Dictionary with statistics
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
            }
        except Exception as e:
            logger.error(f"Error getting vector store stats: {e}")
            return {}

    def rebuild_from_bookmarks(self, bookmarks: List[Bookmark]) -> bool:
        """
        Rebuild the vector store from a list of bookmarks.

        Args:
            bookmarks: List of Bookmark objects

        Returns:
            True if successful, False otherwise
        """
        # Clear existing data
        if not self.clear():
            return False

        # Add new bookmarks
        return self.add_bookmarks(bookmarks)

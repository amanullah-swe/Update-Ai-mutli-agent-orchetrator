"""Base interface for vector store adapters."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from rag.core.base import BaseComponent
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk


class BaseVectorStore(BaseComponent):
    """Abstract base class for vector database storage and similarity search."""

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> None:
        """Persist chunks and their vector embeddings."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        """Perform vector similarity search and return top-k scored chunks."""
        pass

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None:
        """Delete all chunks belonging to a specific document."""
        pass

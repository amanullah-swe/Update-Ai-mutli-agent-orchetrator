"""Base interface for reranker strategies."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent
from rag.types.retrieval import RetrievedChunk


class BaseReranker(BaseComponent):
    """Abstract base class for re-ordering retrieved chunks based on relevance."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        """Rerank chunks for the given query and return the top-k highest scoring chunks."""
        pass

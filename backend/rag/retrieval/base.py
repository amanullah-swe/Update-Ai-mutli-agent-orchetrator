"""Base interface for retriever strategies."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from rag.core.base import BaseComponent
from rag.types.retrieval import RetrievalQuery, RetrievedChunk


class BaseRetriever(BaseComponent):
    """Abstract base class for retrieving candidate chunks matching a query."""

    @abstractmethod
    def retrieve(self, query: str | RetrievalQuery, top_k: int = 5, **kwargs: Any) -> list[RetrievedChunk]:
        """Retrieve the top relevant chunks for a user query."""
        pass

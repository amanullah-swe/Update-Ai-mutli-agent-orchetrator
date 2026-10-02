"""Base interface for query transformation strategies."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent


class BaseQueryTransformer(BaseComponent):
    """Abstract base class for transforming user queries prior to retrieval."""

    @abstractmethod
    def transform(self, query: str) -> str:
        """Transform or expand a query string."""
        pass

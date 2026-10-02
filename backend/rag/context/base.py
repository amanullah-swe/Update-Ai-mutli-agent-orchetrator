"""Base interface for context building strategies."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent
from rag.types.retrieval import RetrievedChunk


class BaseContextBuilder(BaseComponent):
    """Abstract base class for constructing context prompts from retrieved chunks."""

    @abstractmethod
    def build_context(self, chunks: list[RetrievedChunk], max_tokens: int | None = None) -> str:
        """Format retrieved chunks into a context string with source citations."""
        pass

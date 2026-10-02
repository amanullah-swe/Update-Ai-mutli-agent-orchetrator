"""Base interface for all chunking strategies."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent
from rag.types.chunk import Chunk
from rag.types.document import Document


class BaseChunker(BaseComponent):
    """Abstract base class that all chunking strategies implement."""

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        """Convert a Document into a list of retrieval-ready Chunk objects."""
        pass

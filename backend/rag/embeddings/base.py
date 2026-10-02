"""Base interface for embedding model strategies."""

from __future__ import annotations

from abc import abstractmethod

from rag.core.base import BaseComponent


class BaseEmbeddingModel(BaseComponent):
    """Abstract base class for text embedding generation."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Vector dimensionality of the generated embeddings."""
        pass

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text string."""
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of text strings."""
        pass

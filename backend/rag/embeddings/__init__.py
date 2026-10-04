"""Embedding models for dense retrieval."""

from rag.embeddings.base import BaseEmbeddingModel
from rag.embeddings.openrouter import OpenRouterEmbeddings

__all__ = [
    "BaseEmbeddingModel",
    "OpenRouterEmbeddings",
]

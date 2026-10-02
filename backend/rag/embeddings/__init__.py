"""Embedding models for dense retrieval."""

from rag.embeddings.base import BaseEmbeddingModel
from rag.embeddings.openrouter import OpenRouterEmbeddings
from rag.embeddings.sentence_transformer import SentenceTransformerEmbeddings

__all__ = [
    "BaseEmbeddingModel",
    "OpenRouterEmbeddings",
    "SentenceTransformerEmbeddings",
]

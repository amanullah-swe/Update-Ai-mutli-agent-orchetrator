"""Canonical domain models for the RAG subsystem."""

from rag.types.chunk import Chunk, ChunkType
from rag.types.document import (
    Document,
    GraphicBlock,
    ImageBlock,
    Page,
    TableBlock,
    TextBlock,
)
from rag.types.evaluation import EvaluationMetric, EvaluationResult
from rag.types.retrieval import RetrievalQuery, RetrievedChunk, SearchResult

__all__ = [
    "Chunk",
    "ChunkType",
    "Document",
    "EvaluationMetric",
    "EvaluationResult",
    "GraphicBlock",
    "ImageBlock",
    "Page",
    "RetrievalQuery",
    "RetrievedChunk",
    "SearchResult",
    "TableBlock",
    "TextBlock",
]

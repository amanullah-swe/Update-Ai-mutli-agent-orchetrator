"""Modular RAG Subsystem: Ingestion, Chunking, Embeddings, Storage, Retrieval, Reranking, and Generation.

Active chunking strategy: OverlapChunker (fixed-size sliding window with overlap).
"""

# Import all modules so their @register decorators execute upon importing `rag`
import rag.chunking        # registers: chunking/overlap, chunking/fixed_size
import rag.context         # registers: context_builder/default
import rag.embeddings      # registers: embedding/sentence_transformer, embedding/openrouter
import rag.generation      # registers: generator/openrouter, generator/llm
import rag.ingestion       # registers: loader/pdf, parser/pdf, cleaner/default
import rag.query           # registers: query_transformation/none, query_transformation/passthrough
import rag.reranking       # registers: reranking/none, reranking/noop, reranking/cross_encoder
import rag.retrieval       # registers: retrieval/dense
import rag.vectorstores    # registers: vectorstore/pgvector
from rag.core.registry import build_component, list_components, register
from rag.pipeline import RAGPipeline

__all__ = [
    "RAGPipeline",
    "build_component",
    "list_components",
    "register",
]

"""Unit tests for the context builder."""

import pytest

from rag.context.builder import DefaultContextBuilder
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk


def _make_retrieved(chunk_id: str, doc_id: str, page: int, content: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id=doc_id,
            content=content,
            page_number=page,
        ),
        score=0.9,
    )


class TestDefaultContextBuilder:
    def test_builds_context_with_sources(self):
        chunks = [
            _make_retrieved("c1", "doc_a", 3, "RAG stands for Retrieval Augmented Generation."),
            _make_retrieved("c2", "doc_b", 7, "Dense retrieval uses vector similarity."),
        ]
        ctx = DefaultContextBuilder().build_context(chunks)
        assert "Source 1" in ctx
        assert "Source 2" in ctx
        assert "doc_a" in ctx
        assert "Page 3" in ctx
        assert "RAG stands for Retrieval" in ctx

    def test_empty_chunks_returns_empty_string(self):
        ctx = DefaultContextBuilder().build_context([])
        assert ctx == ""

    def test_separator_between_sources(self):
        chunks = [
            _make_retrieved("c1", "doc_a", 1, "First content."),
            _make_retrieved("c2", "doc_b", 2, "Second content."),
        ]
        ctx = DefaultContextBuilder(separator="\n---\n").build_context(chunks)
        assert "\n---\n" in ctx

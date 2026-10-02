"""Unit tests for the rerankers."""

import pytest

from rag.reranking.noop import NoOpReranker
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk


def _make_retrieved(chunk_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id=chunk_id,
            document_id="doc1",
            content=f"Content of {chunk_id}",
        ),
        score=score,
    )


class TestNoOpReranker:
    def test_preserves_order(self):
        chunks = [
            _make_retrieved("c1", 0.9),
            _make_retrieved("c2", 0.7),
            _make_retrieved("c3", 0.5),
        ]
        reranker = NoOpReranker()
        result = reranker.rerank("query", chunks)
        assert [r.chunk.id for r in result] == ["c1", "c2", "c3"]

    def test_top_k_slices(self):
        chunks = [
            _make_retrieved("c1", 0.9),
            _make_retrieved("c2", 0.7),
            _make_retrieved("c3", 0.5),
        ]
        reranker = NoOpReranker()
        result = reranker.rerank("query", chunks, top_k=2)
        assert len(result) == 2
        assert result[0].chunk.id == "c1"

    def test_empty_input(self):
        assert NoOpReranker().rerank("query", []) == []

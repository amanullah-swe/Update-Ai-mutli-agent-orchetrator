"""Unit tests for the RAGPipeline component coordinator."""

from __future__ import annotations

import pytest

from rag.context.base import BaseContextBuilder
from rag.generation.base import BaseGenerator
from rag.pipeline import RAGPipeline
from rag.query.base import BaseQueryTransformer
from rag.reranking.base import BaseReranker
from rag.retrieval.base import BaseRetriever
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk


class DummyQueryTransformer(BaseQueryTransformer):
    def transform(self, query: str) -> str:
        return f"transformed: {query}"


class DummyRetriever(BaseRetriever):
    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk=Chunk(id=f"c-{i}", document_id="doc-1", content=f"Chunk {i}"),
                score=0.9 - (i * 0.1),
            )
            for i in range(top_k)
        ]


class DummyReranker(BaseReranker):
    def rerank(
        self, query: str, chunks: list[RetrievedChunk], top_k: int = 5
    ) -> list[RetrievedChunk]:
        # Reverse order for verification
        return list(reversed(chunks))[:top_k]


class DummyContextBuilder(BaseContextBuilder):
    def build_context(self, chunks: list[RetrievedChunk]) -> str:
        return "\n".join(c.chunk.content for c in chunks)


class DummyGenerator(BaseGenerator):
    def generate(self, query: str, context: str) -> str:
        return f"Answer for '{query}' with context length {len(context)}"

    def generate_stream(self, query: str, context: str, **kwargs) -> list[str]:
        return [self.generate(query, context)]


@pytest.mark.unit
class TestRAGPipeline:
    def test_pipeline_query_flow(self) -> None:
        pipeline = RAGPipeline(
            query_transformer=DummyQueryTransformer(),
            retriever=DummyRetriever(),
            reranker=DummyReranker(),
            context_builder=DummyContextBuilder(),
            generator=DummyGenerator(),
        )

        result = pipeline.query("my test query", top_k=3)

        assert result["query"] == "my test query"
        assert result["transformed_query"] == "transformed: my test query"
        assert len(result["sources"]) == 3
        # DummyReranker reverses the chunks
        assert result["sources"][0].chunk.id == "c-5"  # retrieved top_k * 2 = 6, reversed -> c-5 first
        assert "Answer for 'transformed: my test query'" in result["answer"]
        assert len(result["context"]) > 0

    def test_pipeline_from_config(self) -> None:
        config = {
            "query_transformation": {"strategy": "none"},
            "retrieval": {"strategy": "dense"},
            "reranking": {"strategy": "none"},
            "context": {"strategy": "default"},
            "generation": {"strategy": "openrouter"},
        }
        pipeline = RAGPipeline.from_config(config)
        assert pipeline.query_transformer is not None
        assert pipeline.retriever is not None
        assert pipeline.reranker is not None
        assert pipeline.context_builder is not None
        assert pipeline.generator is not None

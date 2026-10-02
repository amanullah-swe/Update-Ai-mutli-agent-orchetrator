"""High-level RAG Pipeline coordinating swappable components."""

from __future__ import annotations

from typing import Any

from rag.context.base import BaseContextBuilder
from rag.context.builder import DefaultContextBuilder
from rag.core.registry import build_component
from rag.generation.base import BaseGenerator
from rag.generation.llm import OpenRouterGenerator
from rag.query.base import BaseQueryTransformer
from rag.query.passthrough import PassThroughQueryTransformer
from rag.reranking.base import BaseReranker
from rag.reranking.noop import NoOpReranker
from rag.retrieval.base import BaseRetriever
from rag.retrieval.dense import DenseRetriever
from rag.types.retrieval import RetrievedChunk


class RAGPipeline:
    """Config-driven RAG pipeline orchestrating Query -> Retrieve -> Rerank -> Context -> Generate."""

    def __init__(
        self,
        query_transformer: BaseQueryTransformer | None = None,
        retriever: BaseRetriever | None = None,
        reranker: BaseReranker | None = None,
        context_builder: BaseContextBuilder | None = None,
        generator: BaseGenerator | None = None,
    ):
        self.query_transformer = query_transformer or PassThroughQueryTransformer()
        self.retriever = retriever or DenseRetriever()
        self.reranker = reranker or NoOpReranker()
        self.context_builder = context_builder or DefaultContextBuilder()
        self.generator = generator or OpenRouterGenerator()

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> RAGPipeline:
        """Instantiate a RAGPipeline using component names from configuration."""
        q_strat = config.get("query_transformation", {}).get("strategy", "none")
        ret_strat = config.get("retrieval", {}).get("strategy", "dense")
        rerank_strat = config.get("reranking", {}).get("strategy", "none")
        ctx_strat = config.get("context", {}).get("strategy", "default")
        gen_strat = config.get("generation", {}).get("strategy", "openrouter")

        return cls(
            query_transformer=build_component("query_transformation", q_strat),
            retriever=build_component("retrieval", ret_strat),
            reranker=build_component("reranking", rerank_strat),
            context_builder=build_component("context_builder", ctx_strat),
            generator=build_component("generator", gen_strat),
        )

    def query(self, user_query: str, top_k: int = 5) -> dict[str, Any]:
        """Execute the end-to-end RAG query flow."""
        # 1. Query Transformation
        transformed_query = self.query_transformer.transform(user_query)

        # 2. Candidate Retrieval
        candidates = self.retriever.retrieve(transformed_query, top_k=top_k * 2)

        # 3. Reranking
        ranked_chunks: list[RetrievedChunk] = self.reranker.rerank(
            transformed_query, candidates, top_k=top_k
        )

        # 4. Context Construction
        context = self.context_builder.build_context(ranked_chunks)

        # 5. Answer Generation
        answer = self.generator.generate(transformed_query, context)

        return {
            "query": user_query,
            "transformed_query": transformed_query,
            "context": context,
            "answer": answer,
            "sources": ranked_chunks,
        }

"""No-op pass-through reranker."""

from __future__ import annotations

from rag.core.registry import register
from rag.reranking.base import BaseReranker
from rag.types.retrieval import RetrievedChunk


@register("reranking", "none")
@register("reranking", "noop")
class NoOpReranker(BaseReranker):
    """Pass-through reranker that preserves existing retrieval ordering."""

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        if top_k is not None:
            return chunks[:top_k]
        return chunks

"""Cross-encoder reranker strategy."""

from __future__ import annotations

from typing import Any

from rag.core.registry import register
from rag.reranking.base import BaseReranker
from rag.types.retrieval import RetrievedChunk


@register("reranking", "cross_encoder")
class CrossEncoderReranker(BaseReranker):
    """Reranks retrieved chunks using a SentenceTransformers CrossEncoder model."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model: Any = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int | None = None,
    ) -> list[RetrievedChunk]:
        if not chunks:
            return []

        pairs = [[query, c.content] for c in chunks]
        scores = self.model.predict(pairs)

        rescored = []
        for chunk, score in zip(chunks, scores):
            rescored.append(
                RetrievedChunk(
                    chunk=chunk.chunk,
                    score=float(score),
                    retriever=f"{chunk.retriever}+cross_encoder",
                )
            )

        rescored.sort(key=lambda x: x.score, reverse=True)
        if top_k is not None:
            return rescored[:top_k]
        return rescored

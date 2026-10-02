"""SentenceTransformer local embedding model."""

from __future__ import annotations

from typing import Any

from rag.core.registry import register
from rag.embeddings.base import BaseEmbeddingModel


@register("embedding", "sentence_transformer")
@register("embedding", "local")
class SentenceTransformerEmbeddings(BaseEmbeddingModel):
    """Generates dense vector embeddings using SentenceTransformers."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        normalize_embeddings: bool = True,
    ):
        self.model_name = model_name
        self.normalize_embeddings = normalize_embeddings
        self._model: Any = None
        self._dimension: int | None = None

    @property
    def model(self) -> Any:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._dimension = (
                self._model.get_embedding_dimension()
                if hasattr(self._model, "get_embedding_dimension")
                else self._model.get_sentence_embedding_dimension()
            )
        return self._model

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            _ = self.model
        return self._dimension or 384

    def embed_text(self, text: str) -> list[float]:
        vector = self.model.encode(
            text,
            normalize_embeddings=self.normalize_embeddings,
        )
        return vector.tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            normalize_embeddings=self.normalize_embeddings,
            show_progress_bar=False,
        )
        return vectors.tolist()

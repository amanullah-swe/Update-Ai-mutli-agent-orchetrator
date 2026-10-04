"""OpenRouter remote embedding model."""

from __future__ import annotations

import os
from typing import Any

import httpx

from rag.core.exceptions import RAGError
from rag.core.registry import register
from rag.embeddings.base import BaseEmbeddingModel

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-minilm-l6-v2"
DEFAULT_EMBEDDING_DIM = 384
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def _resolve_config() -> tuple[str, str, int]:
    """Resolve API key, model name, and dimension from Settings or environment."""
    api_key = ""
    model_name = DEFAULT_EMBEDDING_MODEL
    dimension = DEFAULT_EMBEDDING_DIM

    try:
        from app.core.config import get_settings

        settings = get_settings()
        api_key = (
            getattr(settings, "embedding_api_key", "")
            or getattr(settings, "llm_api_key", "")
        )
        model_name = getattr(settings, "embedding_model", DEFAULT_EMBEDDING_MODEL)
        dimension = getattr(settings, "embedding_dimension", DEFAULT_EMBEDDING_DIM)
    except Exception:
        pass

    if not api_key:
        api_key = (
            os.getenv("RAG_EMBEDDING_API_KEY", "")
            or os.getenv("RAG_LLM_API_KEY", "")
            or os.getenv("OPENROUTER_API_KEY", "")
        )

    env_model = os.getenv("RAG_EMBEDDING_MODEL")
    if env_model:
        model_name = env_model

    return api_key, model_name, dimension


@register("embedding", "openrouter")
@register("embedding", "default")
@register("embedding", "sentence_transformer")
class OpenRouterEmbeddings(BaseEmbeddingModel):
    """Generates embeddings via OpenRouter API."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        dimension: int | None = None,
        base_url: str = DEFAULT_OPENROUTER_BASE_URL,
        client: httpx.Client | None = None,
    ):
        resolved_key, resolved_model, resolved_dim = _resolve_config()

        self.api_key = api_key if api_key is not None else resolved_key
        self.model_name = model_name if model_name is not None else resolved_model
        self._dimension = dimension if dimension is not None else resolved_dim
        self.base_url = base_url.rstrip("/")
        self._client = client

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        results = self.embed_batch([text])
        return results[0] if results else []

    def embed_batch(
        self, texts: list[str], batch_size: int = 64
    ) -> list[list[float]]:
        if not texts:
            return []

        if not self.api_key:
            raise RAGError(
                "OpenRouter API key is missing. Set RAG_LLM_API_KEY in environment or .env."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        all_embeddings: list[list[float]] = []

        # Send in chunks of batch_size to respect provider limits
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            payload = {
                "model": self.model_name,
                "input": chunk,
            }

            try:
                if self._client is not None:
                    response = self._client.post(
                        f"{self.base_url}/embeddings",
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                else:
                    with httpx.Client(timeout=60.0) as client:
                        response = client.post(
                            f"{self.base_url}/embeddings",
                            headers=headers,
                            json=payload,
                        )
                        response.raise_for_status()
                        data = response.json()

                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                all_embeddings.extend(item["embedding"] for item in sorted_data)
            except Exception as exc:
                raise RAGError(f"Failed to generate OpenRouter embeddings: {exc}") from exc

        return all_embeddings

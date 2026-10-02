"""OpenRouter remote embedding model."""

from __future__ import annotations

import httpx

from rag.core.exceptions import RAGError
from rag.core.registry import register
from rag.embeddings.base import BaseEmbeddingModel


@register("embedding", "openrouter")
class OpenRouterEmbeddings(BaseEmbeddingModel):
    """Generates embeddings via OpenRouter API."""

    def __init__(
        self,
        api_key: str = "",
        model_name: str = "sentence-transformers/all-minilm-l6-v2",
        dimension: int = 384,
        base_url: str = "https://openrouter.ai/api/v1",
    ):
        self.api_key = api_key
        self.model_name = model_name
        self._dimension = dimension
        self.base_url = base_url

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_text(self, text: str) -> list[float]:
        results = self.embed_batch([text])
        return results[0] if results else []

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
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
        payload = {
            "model": self.model_name,
            "input": texts,
        }

        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.base_url}/embeddings",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                sorted_data = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in sorted_data]
        except Exception as exc:
            raise RAGError(f"Failed to generate OpenRouter embeddings: {exc}") from exc

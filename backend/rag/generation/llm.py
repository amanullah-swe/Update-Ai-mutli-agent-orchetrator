"""OpenRouter generator implementation."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx

from rag.core.exceptions import RAGError
from rag.core.registry import register
from rag.generation.base import BaseGenerator

DEFAULT_RAG_SYSTEM_PROMPT = (
    "You are a helpful and accurate assistant. Answer the user's question "
    "faithfully using ONLY the provided context. If the answer cannot be found "
    "in the context, state clearly that the information is not available."
)


@register("generator", "openrouter")
@register("generator", "llm")
class OpenRouterGenerator(BaseGenerator):
    """Generates answers using OpenRouter API."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "qwen/qwen3.8-27b:free",
        base_url: str = "https://openrouter.ai/api/v1",
        temperature: float = 0.2,
        system_prompt: str = DEFAULT_RAG_SYSTEM_PROMPT,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.system_prompt = system_prompt

    def _build_messages(self, query: str, context: str) -> list[dict[str, str]]:
        user_content = f"Context:\n{context}\n\nQuestion:\n{query}" if context else query
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

    def generate(self, query: str, context: str, **kwargs: Any) -> str:
        if not self.api_key:
            return f"[Simulated Answer] Based on the context provided, regarding '{query}': {context[:150]}..."

        messages = self._build_messages(query, context)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RAGError(f"OpenRouter generation failed: {exc}") from exc

    def generate_stream(self, query: str, context: str, **kwargs: Any) -> Iterator[str]:
        # Simple non-stream fallback or token chunking
        full_text = self.generate(query, context, **kwargs)
        words = full_text.split(" ")
        for word in words:
            yield word + " "

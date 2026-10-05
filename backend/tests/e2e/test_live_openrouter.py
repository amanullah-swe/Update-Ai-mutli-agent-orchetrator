"""End-to-End Test: Live OpenRouter integration (opt-in via pytest -m live_llm)."""

from __future__ import annotations

import os
import pytest

from orchestrator.llm_client import OpenRouterLLMClient
from orchestrator.events import TokenEvent, SourcesEvent
from rag.embeddings.openrouter import OpenRouterEmbeddings


@pytest.mark.live_llm
class TestLiveOpenRouter:
    @pytest.fixture(autouse=True)
    def check_api_key(self):
        api_key = os.getenv("RAG_LLM_API_KEY")
        if not api_key:
            pytest.skip("RAG_LLM_API_KEY not configured — skipping live LLM test.")

    def test_live_openrouter_streaming(self) -> None:
        api_key = os.environ["RAG_LLM_API_KEY"]
        model = os.getenv("RAG_LLM_MODEL", "qwen/qwen3.8-27b:free")

        client = OpenRouterLLMClient(model=model, api_key=api_key)
        events = list(client.stream("Say 'hello' in one word."))

        tokens = [e for e in events if isinstance(e, TokenEvent)]
        sources = [e for e in events if isinstance(e, SourcesEvent)]

        assert len(tokens) > 0
        full_text = "".join(t.delta for t in tokens)
        assert len(full_text.strip()) > 0
        assert len(sources) == 1

    def test_live_openrouter_embeddings(self) -> None:
        api_key = os.environ["RAG_LLM_API_KEY"]
        model = os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-minilm-l6-v2")

        embedder = OpenRouterEmbeddings(api_key=api_key, model_name=model)
        vector = embedder.embed_text("Test embedding dimensionality")

        assert len(vector) == 384
        assert all(isinstance(v, float) for v in vector)

"""Unit tests: chat orchestrator — no database, no HTTP (pure logic)."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from orchestrator.chat_orchestrator import ChatOrchestrator, build_chat_orchestrator
from orchestrator.llm_client import MockLLMClient, OpenRouterLLMClient, token_deltas
from orchestrator.events import SourcesEvent, TokenEvent


def test_mock_client_emits_tokens_then_sources() -> None:
    orchestrator = ChatOrchestrator(MockLLMClient())
    events = list(orchestrator.stream("swap chunking"))
    assert isinstance(events[0], TokenEvent)
    text = "".join(e.delta for e in events if isinstance(e, TokenEvent))
    assert "mock assistant" in text
    sources_events = [e for e in events if isinstance(e, SourcesEvent)]
    assert len(sources_events) == 1
    assert len(sources_events[0].sources) == 2


def test_mock_client_is_deterministic() -> None:
    orch = ChatOrchestrator(MockLLMClient())
    stream_a = "".join(e.delta for e in orch.stream("q") if isinstance(e, TokenEvent))
    stream_b = "".join(e.delta for e in orch.stream("q") if isinstance(e, TokenEvent))
    assert stream_a == stream_b


def test_build_chat_orchestrator_selects_mock_from_config() -> None:
    orch = build_chat_orchestrator(Settings(chat_provider="mock"))
    assert isinstance(orch, ChatOrchestrator)
    assert isinstance(orch._llm, MockLLMClient)


def test_build_chat_orchestrator_selects_openrouter_from_config() -> None:
    orch = build_chat_orchestrator(
        Settings(chat_provider="openrouter", llm_api_key="sk-x", llm_model="m/x")
    )
    assert isinstance(orch, ChatOrchestrator)
    assert isinstance(orch._llm, OpenRouterLLMClient)


def test_build_chat_orchestrator_openrouter_without_key_raises() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_chat_orchestrator(Settings(chat_provider="openrouter", llm_api_key=""))
    assert "RAG_LLM_API_KEY" in excinfo.value.message


def test_build_chat_orchestrator_unknown_name_lists_known_providers() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_chat_orchestrator(Settings(chat_provider="does-not-exist"))
    assert "mock" in excinfo.value.message and "openrouter" in excinfo.value.message


def test_orchestrator_accepts_history_keyword() -> None:
    orch = ChatOrchestrator(MockLLMClient())
    events = list(orch.stream("q", history=[]))
    assert isinstance(events[0], TokenEvent)
    assert isinstance(events[-1], SourcesEvent)


def test_token_deltas_preserve_unicode() -> None:
    text = "héllo wörld – ünïcode"
    assert "".join(token_deltas(text, size=3)) == text


def test_orchestrator_with_rag_pipeline_injects_context() -> None:
    """When a RAG pipeline is injected and needs_rag() returns True, context
    should reach the LLM client (verified via mock client's context signal)."""

    class FakeRAGPipeline:
        def query(self, user_query: str, top_k: int = 5) -> dict:
            return {"context": "test context", "sources": []}

    orch = ChatOrchestrator(MockLLMClient(), rag_pipeline=FakeRAGPipeline())
    # "find" triggers needs_rag=True
    events = list(orch.stream("find information about chunking"))
    text = "".join(e.delta for e in events if isinstance(e, TokenEvent))
    # MockLLMClient prepends "[Context received]" when context is injected
    assert "[Context received]" in text


def test_orchestrator_without_pipeline_falls_back_to_direct_llm() -> None:
    """needs_rag=True but no pipeline → direct LLM, no crash."""
    orch = ChatOrchestrator(MockLLMClient(), rag_pipeline=None)
    events = list(orch.stream("search the documents"))
    tokens = [e for e in events if isinstance(e, TokenEvent)]
    assert len(tokens) > 0


def test_orchestrator_rag_failure_falls_back_gracefully() -> None:
    """A crashing RAG pipeline must not surface as an unhandled exception."""

    class BrokenRAGPipeline:
        def query(self, user_query: str, top_k: int = 5) -> dict:
            raise RuntimeError("pgvector is down")

    orch = ChatOrchestrator(MockLLMClient(), rag_pipeline=BrokenRAGPipeline())
    events = list(orch.stream("find something"))
    tokens = [e for e in events if isinstance(e, TokenEvent)]
    assert len(tokens) > 0  # still gets a response
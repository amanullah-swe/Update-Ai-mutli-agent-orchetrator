"""Unit tests for the ChatOrchestrator coordination flow."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.features.chats.schemas import Source
from orchestrator.chat_orchestrator import (
    ChatOrchestrator,
    build_chat_orchestrator,
)
from orchestrator.events import SourcesEvent, TokenEvent
from orchestrator.llm_client import MockLLMClient, OpenRouterLLMClient
from rag.types.chunk import Chunk
from rag.types.retrieval import RetrievedChunk


class FakeRAGPipeline:
    def __init__(self, should_fail: bool = False, sources: list | None = None) -> None:
        self.should_fail = should_fail
        self.sources = sources or []

    def query(self, user_query: str, top_k: int = 5) -> dict:
        if self.should_fail:
            raise RuntimeError("Database connection lost")
        return {
            "query": user_query,
            "transformed_query": user_query,
            "context": "Context retrieved from test document.",
            "answer": "Generated answer.",
            "sources": self.sources,
        }


@pytest.mark.unit
class TestChatOrchestrator:
    def test_orchestrator_converts_retrieved_chunks_to_sources(self) -> None:
        retrieved_chunk = RetrievedChunk(
            chunk=Chunk(
                id="c-001",
                document_id="doc-abc",
                content="Architecture details.",
                page_number=1,
                metadata={"title": "Doc ABC"},
            ),
            score=0.92,
            retriever="dense",
        )
        fake_rag = FakeRAGPipeline(sources=[retrieved_chunk])
        orchestrator = ChatOrchestrator(MockLLMClient(), rag_pipeline=fake_rag)

        # "retrieve" signal triggers needs_rag=True
        events = list(orchestrator.stream("retrieve information about architecture"))
        sources_events = [e for e in events if isinstance(e, SourcesEvent)]

        assert len(sources_events) == 1
        sources = sources_events[0].sources
        assert len(sources) == 1
        assert isinstance(sources[0], Source)
        assert sources[0].chunk_id == "c-001"
        assert sources[0].document_id == "doc-abc"
        assert sources[0].snippet == "Architecture details."
        assert sources[0].score == 0.92
        assert sources[0].metadata == {"title": "Doc ABC"}

    def test_orchestrator_falls_back_when_rag_pipeline_fails(self) -> None:
        broken_rag = FakeRAGPipeline(should_fail=True)
        orchestrator = ChatOrchestrator(MockLLMClient(), rag_pipeline=broken_rag)

        # Should log warning, catch exception, and stream tokens directly without crashing
        events = list(orchestrator.stream("retrieve details"))
        tokens = [e for e in events if isinstance(e, TokenEvent)]
        sources = [e for e in events if isinstance(e, SourcesEvent)]

        assert len(tokens) > 0
        assert len(sources) == 1
        # Fallback emits LLM client's own sources
        assert len(sources[0].sources) == 2

    def test_orchestrator_when_rag_not_needed(self) -> None:
        fake_rag = FakeRAGPipeline()
        orchestrator = ChatOrchestrator(MockLLMClient(), rag_pipeline=fake_rag)

        # Smalltalk doesn't need RAG
        events = list(orchestrator.stream("hello"))
        tokens = [e for e in events if isinstance(e, TokenEvent)]
        assert len(tokens) > 0

    def test_build_chat_orchestrator_factory(self) -> None:
        # Mock provider
        orch_mock = build_chat_orchestrator(Settings(chat_provider="mock"))
        assert isinstance(orch_mock._llm, MockLLMClient)

        # OpenRouter provider with key
        orch_or = build_chat_orchestrator(
            Settings(chat_provider="openrouter", llm_api_key="sk-test", llm_model="m/x")
        )
        assert isinstance(orch_or._llm, OpenRouterLLMClient)

        # OpenRouter provider without key raises ValidationError
        with pytest.raises(ValidationError) as exc_info:
            build_chat_orchestrator(Settings(chat_provider="openrouter", llm_api_key=""))
        assert "RAG_LLM_API_KEY" in str(exc_info.value)

        # Unknown provider raises ValidationError
        with pytest.raises(ValidationError) as exc_info_unknown:
            build_chat_orchestrator(Settings(chat_provider="unknown-provider"))
        assert "unknown-provider" in str(exc_info_unknown.value)

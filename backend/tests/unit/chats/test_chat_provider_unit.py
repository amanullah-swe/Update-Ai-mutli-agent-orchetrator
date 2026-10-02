"""Unit tests: chat provider — no database, no HTTP (pure logic)."""

from __future__ import annotations

import pytest

from app.features.chats.provider import (
    MockChatProvider,
    OpenRouterChatProvider,
    SourcesEvent,
    TokenEvent,
    build_chat_provider,
    token_deltas,
)
from app.core.config import Settings
from app.core.exceptions import ValidationError


def test_mock_provider_emits_tokens_then_sources() -> None:
    events = list(MockChatProvider().stream("swap chunking"))
    assert isinstance(events[0], TokenEvent)
    text = "".join(e.delta for e in events if isinstance(e, TokenEvent))
    assert "mock assistant" in text
    sources_events = [e for e in events if isinstance(e, SourcesEvent)]
    assert len(sources_events) == 1
    assert len(sources_events[0].sources) == 2


def test_mock_provider_is_deterministic() -> None:
    stream_a = "".join(e.delta for e in MockChatProvider().stream("q") if isinstance(e, TokenEvent))
    stream_b = "".join(e.delta for e in MockChatProvider().stream("q") if isinstance(e, TokenEvent))
    assert stream_a == stream_b


def test_build_chat_provider_selects_mock_from_config() -> None:
    provider = build_chat_provider(Settings(chat_provider="mock"))
    assert isinstance(provider, MockChatProvider)


def test_build_chat_provider_selects_openrouter_from_config() -> None:
    provider = build_chat_provider(
        Settings(chat_provider="openrouter", llm_api_key="sk-x", llm_model="m/x")
    )
    assert isinstance(provider, OpenRouterChatProvider)


def test_build_chat_provider_openrouter_without_key_raises() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_chat_provider(Settings(chat_provider="openrouter", llm_api_key=""))
    assert "RAG_LLM_API_KEY" in excinfo.value.message


def test_build_chat_provider_unknown_name_lists_known_providers() -> None:
    with pytest.raises(ValidationError) as excinfo:
        build_chat_provider(Settings(chat_provider="does-not-exist"))
    assert "mock" in excinfo.value.message and "openrouter" in excinfo.value.message


def test_mock_provider_accepts_history_keyword() -> None:
    # The protocol grew a history argument; the mock ignores it (no behaviour
    # change) so every existing caller and test stays valid.
    events = list(MockChatProvider().stream("q", history=[]))
    assert isinstance(events[0], TokenEvent)
    assert isinstance(events[-1], SourcesEvent)


def test_token_deltas_preserve_unicode() -> None:
    text = "héllo wörld – ünïcode"
    assert "".join(token_deltas(text, size=3)) == text
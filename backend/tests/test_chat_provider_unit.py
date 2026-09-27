"""Unit tests: chat provider — no database, no HTTP (pure logic)."""

from __future__ import annotations

import pytest

from app.core.config import Settings
from app.core.exceptions import ValidationError
from app.services.chat import (
    MockChatProvider,
    SourcesEvent,
    TokenEvent,
    build_chat_provider,
    token_deltas,
)


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


def test_build_chat_provider_unknown_name_raises() -> None:
    with pytest.raises(ValidationError):
        build_chat_provider(Settings(chat_provider="does-not-exist"))


def test_token_deltas_preserve_unicode() -> None:
    text = "héllo wörld – ünïcode"
    assert "".join(token_deltas(text, size=3)) == text
"""Unit tests: OpenRouterChatProvider — no network (httpx.MockTransport)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.features.chats.provider import (
    LLM_SYSTEM_PROMPT,
    OpenRouterChatProvider,
    SourcesEvent,
    TokenEvent,
    _build_messages,
)
from app.features.chats.schemas import MessageOut
from app.core.exceptions import LLMProviderError


def _msg(
    role: str, content: str, *, error: bool = False, id: str | None = None
) -> MessageOut:
    return MessageOut(
        id=uuid.UUID(id or uuid.uuid4().hex),
        role=role,
        content=content,
        created_at=datetime.now(timezone.utc),
        sources=None,
        error=error,
    )


def _role_chunk(role: str = "assistant") -> str:
    return json.dumps({"choices": [{"delta": {"role": role}}]})


def _content_chunk(content: str) -> str:
    return json.dumps({"choices": [{"delta": {"content": content}}]})


def _provider(handler, *, api_key: str = "sk-test") -> OpenRouterChatProvider:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenRouterChatProvider(model="m/test-model", api_key=api_key, client=client)


def _sss_body() -> bytes:
    """A realistic SSE turn: role chunk, two content chunks, comment, usage-only, [DONE]."""
    return (
        f"data: {_role_chunk()}\n"
        f"data: {_content_chunk('Hel')}\n"
        f": ping\n"
        f"data: {_content_chunk('lo!')}\n"
        f'data: {{"choices": []}}\n'
        "data: [DONE]\n"
    ).encode()


def test_stream_parses_sse_into_tokens_then_empty_sources() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=_sss_body())

    provider = _provider(handler)
    events = list(provider.stream("hi"))

    tokens = [e.delta for e in events if isinstance(e, TokenEvent)]
    assert "".join(tokens) == "Hello!"
    sources = [e for e in events if isinstance(e, SourcesEvent)]
    assert len(sources) == 1 and sources[0].sources == ()


def test_request_carries_history_messages_model_and_auth() -> None:
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = request.headers
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"data: [DONE]\n")

    provider = _provider(handler)
    history = [
        _msg("user", "first"),
        _msg("assistant", "reply"),
        _msg("user", "ignored failed turn", error=True),
    ]
    list(provider.stream("now?", history=history))

    assert captured["headers"]["authorization"] == "Bearer sk-test"
    messages = captured["body"]["messages"]
    assert messages == [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "now?"},
    ]
    assert captured["body"]["model"] == "m/test-model"
    assert captured["body"]["stream"] is True


def test_build_messages_coalesces_adjacent_same_role() -> None:
    messages = _build_messages(
        [_msg("user", "one"), _msg("user", "two")], "three"
    )
    assert messages == [
        {"role": "system", "content": LLM_SYSTEM_PROMPT},
        {"role": "user", "content": "one\ntwo"},
        {"role": "user", "content": "three"},
    ]


def test_non_200_raises_llm_provider_error() -> None:
    provider = _provider(
        lambda req: httpx.Response(
            429, json={"error": {"message": "rate limited"}}
        )
    )
    with pytest.raises(LLMProviderError) as excinfo:
        list(provider.stream("hi"))
    assert excinfo.value.details["status_code"] == 429
    assert "HTTP 429" in str(excinfo.value)


def test_transport_error_wraps_into_llm_provider_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    provider = _provider(handler)
    with pytest.raises(LLMProviderError):
        list(provider.stream("hi"))


def test_token_delay_is_applied_per_delta(monkeypatch) -> None:
    sleeps: list[float] = []
    import time

    monkeypatch.setattr(
        "app.features.chats.provider.time.sleep", lambda s: sleeps.append(s)
    )
    provider = _provider(
        lambda req: httpx.Response(
            200, content=f"data: {_content_chunk('x')}\ndata: [DONE]\n".encode()
        )
    )
    list(provider.stream("hi", token_delay_ms=25))
    assert sleeps == [0.025]


def test_empty_stream_yields_only_empty_sources() -> None:
    provider = _provider(lambda req: httpx.Response(200, content=b"data: [DONE]\n"))
    events = list(provider.stream("hi"))
    assert events == [SourcesEvent(())]
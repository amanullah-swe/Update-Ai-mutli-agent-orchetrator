"""Unit tests for the pure LLM clients (Mock and OpenRouter)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
import uuid
import httpx
import pytest

from app.core.exceptions import LLMProviderError
from app.features.chats.schemas import MessageOut
from orchestrator.events import SourcesEvent, TokenEvent
from orchestrator.llm_client import (
    MockLLMClient,
    OpenRouterLLMClient,
    _build_messages,
    token_deltas,
)


@pytest.mark.unit
class TestLLMClientHelpers:
    def test_token_deltas_empty_and_short(self) -> None:
        assert list(token_deltas("")) == []
        assert list(token_deltas("ab", size=5)) == ["ab"]

    def test_token_deltas_splits_exact_size(self) -> None:
        text = "abcdefghij"
        assert list(token_deltas(text, size=5)) == ["abcde", "fghij"]

    def test_token_deltas_unicode_and_emojis(self) -> None:
        text = "Hello 🚀 world 🌟!"
        reconstructed = "".join(token_deltas(text, size=3))
        assert reconstructed == text

    def test_build_messages_with_and_without_context(self) -> None:
        now = datetime.now(timezone.utc)
        chat_id = uuid.uuid4()
        history = [
            MessageOut(
                id=uuid.uuid4(), conversation_id=chat_id, role="user",
                content="First question", sources=None, error=False, created_at=now
            ),
            MessageOut(
                id=uuid.uuid4(), conversation_id=chat_id, role="assistant",
                content="First answer", sources=None, error=False, created_at=now
            ),
            MessageOut(
                id=uuid.uuid4(), conversation_id=chat_id, role="assistant",
                content="Failed answer", sources=None, error=True, created_at=now
            ),
        ]

        # Without RAG context
        msgs_no_ctx = _build_messages(history, "Second question")
        assert len(msgs_no_ctx) == 4  # system + user + assistant + current user
        assert msgs_no_ctx[0]["role"] == "system"
        assert "Retrieved context" not in msgs_no_ctx[0]["content"]
        assert msgs_no_ctx[1] == {"role": "user", "content": "First question"}
        assert msgs_no_ctx[2] == {"role": "assistant", "content": "First answer"}
        assert msgs_no_ctx[3] == {"role": "user", "content": "Second question"}

        # With RAG context
        msgs_ctx = _build_messages(history, "Second question", context="Important facts.")
        assert "## Retrieved context" in msgs_ctx[0]["content"]
        assert "Important facts." in msgs_ctx[0]["content"]

    def test_build_messages_coalesces_same_role(self) -> None:
        now = datetime.now(timezone.utc)
        chat_id = uuid.uuid4()
        history = [
            MessageOut(
                id=uuid.uuid4(), conversation_id=chat_id, role="user",
                content="Part A", sources=None, error=False, created_at=now
            ),
            MessageOut(
                id=uuid.uuid4(), conversation_id=chat_id, role="user",
                content="Part B", sources=None, error=False, created_at=now
            ),
        ]
        msgs = _build_messages(history, "New turn")
        # system + combined user + current user
        assert len(msgs) == 3
        assert msgs[1]["content"] == "Part A\nPart B"


@pytest.mark.unit
class TestMockLLMClient:
    def test_mock_client_stream_tokens_and_sources(self) -> None:
        client = MockLLMClient()
        events = list(client.stream("hello world"))
        tokens = [e for e in events if isinstance(e, TokenEvent)]
        sources = [e for e in events if isinstance(e, SourcesEvent)]

        assert len(tokens) > 0
        assert len(sources) == 1
        assert len(sources[0].sources) == 2

    def test_mock_client_includes_context_marker_when_provided(self) -> None:
        client = MockLLMClient()
        events = list(client.stream("query", context="Sample context string"))
        text = "".join(e.delta for e in events if isinstance(e, TokenEvent))
        assert "[Context received]" in text


@pytest.mark.unit
class TestOpenRouterLLMClient:
    def test_successful_streaming(self) -> None:
        def sse_handler(request: httpx.Request) -> httpx.Response:
            chunks = [
                ': ping\n\n',
                'data: {"choices":[{"delta":{"content":"Hi"}}]}\n\n',
                'data: {"choices":[{"delta":{"content":" there!"}}]}\n\n',
                'data: [DONE]\n\n',
            ]
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content="".join(chunks).encode("utf-8"),
            )

        http_client = httpx.Client(transport=httpx.MockTransport(sse_handler))
        client = OpenRouterLLMClient(model="test-model", api_key="sk-test", client=http_client)

        events = list(client.stream("hello"))
        tokens = [e for e in events if isinstance(e, TokenEvent)]
        sources = [e for e in events if isinstance(e, SourcesEvent)]

        assert "".join(t.delta for t in tokens) == "Hi there!"
        assert len(sources) == 1
        assert sources[0].sources == ()

    def test_non_200_response_raises_llm_provider_error(self) -> None:
        def error_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "Invalid API key"})

        http_client = httpx.Client(transport=httpx.MockTransport(error_handler))
        client = OpenRouterLLMClient(model="test-model", api_key="sk-test", client=http_client)

        with pytest.raises(LLMProviderError) as exc_info:
            list(client.stream("hello"))
        assert "HTTP 401" in str(exc_info.value)

    def test_network_exception_raises_llm_provider_error(self) -> None:
        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectTimeout("Connection timed out")

        http_client = httpx.Client(transport=httpx.MockTransport(timeout_handler))
        client = OpenRouterLLMClient(model="test-model", api_key="sk-test", client=http_client)

        with pytest.raises(LLMProviderError) as exc_info:
            list(client.stream("hello"))
        assert "ConnectTimeout" in str(exc_info.value)

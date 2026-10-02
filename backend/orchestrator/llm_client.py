"""Pure LLM streaming client — no RAG, no routing logic.

Provides:
- ``token_deltas``          — chunk a string into fixed-size delta tokens
- ``MockLLMClient``         — deterministic canned reply (no network)
- ``OpenRouterLLMClient``   — real SSE streaming via OpenRouter's chat API

Both classes satisfy the same ``stream()`` signature as the old ``ChatProvider``
protocol so existing callers (``ChatOrchestrator``, tests) work unchanged.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator, Sequence
from typing import Literal

import httpx

from app.core.exceptions import LLMProviderError
from app.features.chats.schemas import MessageOut, Source
from orchestrator.events import ProviderEvent, SourcesEvent, TokenEvent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

LLM_SYSTEM_PROMPT = (
    "You are a helpful assistant for the RAG Learning Platform. "
    "Answer the user's question directly and concisely. "
    "When context documents are provided, ground your answer in them and cite "
    "the relevant snippets. If no context is available, answer from general "
    "knowledge and never invent citations."
)

MOCK_SOURCES: tuple[Source, ...] = (
    Source(
        document_id="mock-doc-platform-overview",
        chunk_id="mock-chunk-001",
        snippet=(
            "The platform is specification-first: every RAG strategy lives behind "
            "a common interface and is chosen through configuration."
        ),
        score=0.87,
        metadata={"mock": True, "title": "Platform Overview"},
    ),
    Source(
        document_id="mock-doc-rag-getting-started",
        chunk_id="mock-chunk-003",
        snippet=(
            "Swapping a strategy such as chunking or retrieval only means editing a "
            "value in the config file — the pipeline code is untouched."
        ),
        score=0.74,
        metadata={"mock": True, "title": "RAG Getting Started"},
    ),
)

_MOCK_ANSWER = (
    "I'm the mock assistant — the backend is running, but no model is wired up yet. "
    'Here is how a real reply to "{prompt}" will look once the RAG pipeline lands.\n\n'
    "**How this platform works**\n\n"
    "- Every RAG strategy lives behind a common interface (`Chunker`, `Retriever`, `Reranker`, ...).\n"
    "- Swapping strategies is a config change: `chunking: recursive` → `semantic`.\n"
    "- Each stage is independently testable and every answer traces back to its sources."
)


def token_deltas(text: str, size: int = 5) -> Iterator[str]:
    """Split *text* into fixed-size deltas (never splitting a multi-byte char)."""
    i, n = 0, len(text)
    while i < n:
        yield text[i : i + size]
        i += size


def _build_messages(
    history: Sequence[MessageOut],
    user_message: str,
    *,
    context: str | None = None,
) -> list[dict[str, str]]:
    """Map the persisted transcript + optional RAG context to OpenAI-style messages.

    - Failed turns (``error=True``) are never fed back.
    - Adjacent same-role rows are defensively coalesced.
    - When ``context`` is provided it is prepended to the system prompt so the
      LLM has grounding documents before the question arrives.
    - The current question is always the final ``user`` message.
    """
    system = LLM_SYSTEM_PROMPT
    if context:
        system = (
            f"{system}\n\n"
            "## Retrieved context\n\n"
            f"{context}\n\n"
            "Use the context above to answer the user's question."
        )
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for msg in history:
        if msg.error:
            continue
        role = msg.role if msg.role in ("user", "assistant") else "user"
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + msg.content
        else:
            messages.append({"role": role, "content": msg.content})
    messages.append({"role": "user", "content": user_message})
    return messages


# ---------------------------------------------------------------------------
# Mock client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Deterministic canned reply: text deltas then one citations event.

    Drop-in replacement for ``MockChatProvider`` from the old provider layer.
    """

    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
        context: str | None = None,
    ) -> Iterator[ProviderEvent]:
        prompt = user_message.strip().splitlines()[0][:60] if user_message.strip() else "…"
        answer = _MOCK_ANSWER.replace("{prompt}", prompt)
        if context:
            answer = f"[Context received]\n\n{answer}"
        for delta in token_deltas(answer):
            if token_delay_ms:
                time.sleep(token_delay_ms / 1000.0)
            yield TokenEvent(delta)
        yield SourcesEvent(MOCK_SOURCES)


# ---------------------------------------------------------------------------
# OpenRouter client
# ---------------------------------------------------------------------------


class OpenRouterLLMClient:
    """Real chat answers via OpenRouter's streaming chat completions.

    Emits one ``TokenEvent`` per content delta, then a single ``SourcesEvent``.
    The optional ``context`` argument is injected into the system prompt when
    the RAG pipeline has retrieved relevant documents.

    Tests inject a ``client`` backed by ``httpx.MockTransport`` — no network.
    """

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        client: httpx.Client | None = None,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._client = client

    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
        context: str | None = None,
    ) -> Iterator[ProviderEvent]:
        messages = _build_messages(history or (), user_message, context=context)
        client = self._client or httpx.Client(
            timeout=httpx.Timeout(connect=15.0, read=120.0, write=15.0, pool=15.0)
        )
        try:
            with client.stream(
                "POST",
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": self._model, "messages": messages, "stream": True},
            ) as response:
                # Client.stream() does NOT raise on non-2xx — check explicitly.
                if response.status_code != 200:
                    body = response.read().decode("utf-8", "replace")[:2000]
                    raise LLMProviderError(
                        f"OpenRouter request failed (HTTP {response.status_code}).",
                        details={"status_code": response.status_code, "body": body},
                    )
                for line in response.iter_lines():
                    line = (line or "").strip()
                    if not line or not line.startswith("data:"):
                        continue  # blank / `: ping` comment heartbeat
                    payload = line[len("data:") :].strip()
                    if not payload or payload == "[DONE]":
                        break  # stream ended — fall through to citations event
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue  # malformed keep-alive — drop, never crash
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue  # usage-only / comment chunk
                    content = (choices[0].get("delta") or {}).get("content")
                    if isinstance(content, str) and content:
                        if token_delay_ms:
                            time.sleep(token_delay_ms / 1000.0)
                        yield TokenEvent(content)
                yield SourcesEvent(())
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenRouter connection failed ({exc.__class__.__name__})."
            ) from exc
        finally:
            if self._client is None:
                client.close()

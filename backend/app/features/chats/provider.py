"""Chat provider seam — the Core Architectural Rule at the service scale.

Routes and the chat orchestration depend only on ``ChatProvider``. Which
provider runs is decided by ``chat.provider`` in config — today ``mock``,
tomorrow a RAG-backed provider — with no dispatch chains in route or pipeline
code. A provider emits the assistant's *content* as an ordered stream of
provider events (text deltas, then citations); connectivity/protocol frames
(``ready``, ``message``, ``message_start/end``) are the socket layer's concern.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

from app.core.config import Settings
from app.core.exceptions import LLMProviderError, ValidationError
from app.features.chats.schemas import MessageOut, Source


@dataclass(frozen=True)
class TokenEvent:
    """One text delta of the assistant's reply."""

    delta: str
    kind: Literal["token"] = "token"


@dataclass(frozen=True)
class SourcesEvent:
    """The reply's citations (optional but expected: traceability)."""

    sources: tuple[Source, ...]
    kind: Literal["sources"] = "sources"


ProviderEvent = TokenEvent | SourcesEvent


def token_deltas(text: str, size: int = 5) -> Iterator[str]:
    """Split text into fixed-size deltas (never splitting a multi-byte char)."""
    i, n = 0, len(text)
    while i < n:
        yield text[i : i + size]
        i += size


class ChatProvider(Protocol):
    """Produces the assistant reply for one user message.

    ``history`` carries the *prior* transcript turns (oldest→newest, roles
    alternating ``user``/``assistant``) so a provider can follow the
    conversation. The current question is always ``user_message`` and is not
    part of ``history``.
    """

    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
    ) -> Iterator[ProviderEvent]: ...  # pragma: no cover


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


class MockChatProvider:
    """Deterministic canned reply: text deltas then one citations event."""

    def stream(
        self,
        user_message: str,
        *,
        history: Sequence[MessageOut] | None = None,
        token_delay_ms: int = 0,
    ) -> Iterator[ProviderEvent]:
        prompt = user_message.strip().splitlines()[0][:60] if user_message.strip() else "…"
        answer = _MOCK_ANSWER.replace("{prompt}", prompt)
        for delta in token_deltas(answer):
            if token_delay_ms:
                time.sleep(token_delay_ms / 1000.0)
            yield TokenEvent(delta)
        yield SourcesEvent(MOCK_SOURCES)


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

LLM_SYSTEM_PROMPT = (
    "You are a helpful assistant for the RAG Learning Platform. "
    "Answer the user's question directly and concisely. "
    "No documents are retrievable in this session — never invent citations."
)


def _build_messages(
    history: Sequence[MessageOut], user_message: str
) -> list[dict[str, str]]:
    """Map the persisted transcript + current question to OpenAI-style messages.

    Failed turns (``error=True``) are never fed back; adjacent same-role rows
    are defensively coalesced; the current question is always the final
    ``user`` message.
    """
    messages: list[dict[str, str]] = [
        {"role": "system", "content": LLM_SYSTEM_PROMPT}
    ]
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


class OpenRouterChatProvider:
    """Real chat answers via OpenRouter's streaming chat completions.

    Emits one ``TokenEvent`` per content delta, then a single ``SourcesEvent``
    with no citations (the RAG pipeline does not exist yet). A provider
    instance is built per WS turn; tests inject a client backed by an
    ``httpx.MockTransport`` so no network is touched.
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
    ) -> Iterator[ProviderEvent]:
        messages = _build_messages(history or (), user_message)
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
                        break  # stream ended — fall through to the citations event
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


def build_chat_provider(settings: Settings) -> ChatProvider:
    """Resolve ``chat.provider`` to a concrete provider. Loud on unknown names."""
    name = settings.chat_provider
    if name == "mock":
        return MockChatProvider()
    if name == "openrouter":
        if not settings.llm_api_key:
            raise ValidationError(
                "llm.api_key is not configured — set RAG_LLM_API_KEY "
                "(and backend/.env) to use the OpenRouter chat provider.",
                details={"providers": ["mock", "openrouter"]},
            )
        return OpenRouterChatProvider(
            model=settings.llm_model, api_key=settings.llm_api_key
        )
    raise ValidationError(
        f"Unknown chat provider {name!r}. Known providers: mock, openrouter",
        details={"providers": ["mock", "openrouter"]},
    )

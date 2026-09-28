"""Chat provider seam — the Core Architectural Rule at the service scale.

Routes and the chat orchestration depend only on ``ChatProvider``. Which
provider runs is decided by ``chat.provider`` in config — today ``mock``,
tomorrow a RAG-backed provider — with no dispatch chains in route or pipeline
code. A provider emits the assistant's *content* as an ordered stream of
provider events (text deltas, then citations); connectivity/protocol frames
(``ready``, ``message``, ``message_start/end``) are the socket layer's concern.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Literal, Protocol

from app.modules.chats.schemas import Source
from app.shared.core.config import Settings
from app.shared.core.exceptions import ValidationError


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
    """Produces the assistant reply for one user message."""

    def stream(self, user_message: str, *, token_delay_ms: int = 0) -> Iterator[ProviderEvent]: ...  # pragma: no cover


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

    def stream(self, user_message: str, *, token_delay_ms: int = 0) -> Iterator[ProviderEvent]:
        prompt = user_message.strip().splitlines()[0][:60] if user_message.strip() else "…"
        answer = _MOCK_ANSWER.replace("{prompt}", prompt)
        for delta in token_deltas(answer):
            if token_delay_ms:
                time.sleep(token_delay_ms / 1000.0)
            yield TokenEvent(delta)
        yield SourcesEvent(MOCK_SOURCES)


def build_chat_provider(settings: Settings) -> ChatProvider:
    """Resolve ``chat.provider`` to a concrete provider. Loud on unknown names."""
    name = settings.chat_provider
    if name == "mock":
        return MockChatProvider()
    raise ValidationError(
        f"Unknown chat provider {name!r}. Known providers: mock",
        details={"providers": ["mock"]},
    )
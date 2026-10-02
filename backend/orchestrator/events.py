"""Shared provider event dataclasses.

Moved from ``app.features.chats.provider`` so every layer (ws, orchestrator,
tests) imports from one canonical place — the WebSocket layer never needs to
know which concrete provider ran.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.features.chats.schemas import Source


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

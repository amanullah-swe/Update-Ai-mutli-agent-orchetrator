"""Chat API schemas — HTTP resources and WebSocket frames.

The API surface speaks *chat* (``/api/chats``); the persistence layer keeps
CLAUDE.md's *conversation* names. ``Source`` / ``MessageOut`` keep the shape
the frontend already models in ``frontend/src/types/chat.ts`` so the future RAG
provider needs no contract change.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# --- shared -----------------------------------------------------------------


class Source(BaseModel):
    """A citation pointing back to a source document + chunk (traceability)."""

    model_config = ConfigDict(extra="allow")

    document_id: str
    chunk_id: str
    snippet: str
    score: float | None = None
    metadata: dict[str, Any] | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    sources: list[Source] | None = None
    error: bool = False


# --- HTTP resources ----------------------------------------------------------


class ChatCreate(BaseModel):
    """Body for ``POST /api/chats``. Title optional (null on creation)."""

    title: str | None = Field(default=None, max_length=500)


class ChatRename(BaseModel):
    """Body for ``PATCH /api/chats/{id}``. Title required, non-blank."""

    title: str = Field(min_length=1, max_length=500)


class ChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime


class ChatSummary(ChatOut):
    message_count: int = 0
    last_message_at: datetime | None = None


class ChatListResponse(BaseModel):
    items: list[ChatSummary] = Field(default_factory=list)
    total: int = 0


class ChatDetail(ChatOut):
    messages: list[MessageOut] = Field(default_factory=list)


# --- WebSocket frames --------------------------------------------------------


class UserMessageFrame(BaseModel):
    """Client → server: one user message for a turn."""

    type: Literal["user_message"] = "user_message"
    content: str = Field(min_length=1, max_length=4000)


class ReadyFrame(BaseModel):
    """Server → client: connection accepted, names the chat."""

    type: Literal["ready"] = "ready"
    chat_id: uuid.UUID


class MessageFrame(BaseModel):
    """Server → client: the persisted user message (ack)."""

    type: Literal["message"] = "message"
    message: MessageOut


class MessageStartFrame(BaseModel):
    """Server → client: starts the assistant's reply."""

    type: Literal["message_start"] = "message_start"
    id: str


class TokenFrame(BaseModel):
    """Server → client: one text delta of the assistant's reply."""

    type: Literal["token"] = "token"
    delta: str


class SourcesFrame(BaseModel):
    """Server → client: citations for the reply (optional)."""

    type: Literal["sources"] = "sources"
    sources: list[Source]


class MessageEndFrame(BaseModel):
    """Server → client: final assistant message, persisted before this frame."""

    type: Literal["message_end"] = "message_end"
    id: str
    message: MessageOut


class ErrorFrame(BaseModel):
    """Server → client: in-band error. The socket stays open."""

    type: Literal["error"] = "error"
    code: str
    message: str

"""Chat (conversation) persistence — CRUD + message append, backed by PostgreSQL."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import Conversation, Message
from app.schemas.chat import ChatSummary

TITLE_MAX = 500


def create_chat(db: Session, title: str | None) -> Conversation:
    """Create a chat. ``title`` may be None; a non-None title is stripped/truncated."""
    conversation = Conversation(title=_clean_title(title))
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def _clean_title(title: str | None) -> str | None:
    if title is None:
        return None
    return title.strip()[:TITLE_MAX]


def list_chats(db: Session) -> tuple[list[ChatSummary], int]:
    """All chats, most recently active first (no-message chats sort by created_at)."""
    rows = db.execute(
        select(Conversation, func.count(Message.id), func.max(Message.created_at))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .group_by(Conversation.id)
        .order_by(
            func.max(Message.created_at).is_(None),  # chats with messages first
            func.max(Message.created_at).desc(),
            Conversation.created_at.desc(),
        )
    ).all()
    summaries = [
        ChatSummary(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=message_count,
            last_message_at=last_message_at,
        )
        for conversation, message_count, last_message_at in rows
    ]
    return summaries, len(summaries)


def get_chat(db: Session, chat_id: uuid.UUID) -> Conversation:
    """Chat with its transcript in insertion order. 404 if unknown."""
    conversation = db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == chat_id)
    ).scalar_one_or_none()
    if conversation is None:
        raise NotFoundError("Chat not found.", details={"chat_id": str(chat_id)})
    return conversation


def rename_chat(db: Session, chat_id: uuid.UUID, title: str) -> Conversation:
    """Rename a chat; bumps ``updated_at`` via the model's onupdate trigger."""
    conversation = get_chat(db, chat_id)
    if not title.strip():
        raise ValidationError("Chat title must not be blank.")
    conversation.title = _clean_title(title)
    db.commit()
    db.refresh(conversation)
    return conversation


def delete_chat(db: Session, chat_id: uuid.UUID) -> None:
    """Delete a chat; its messages cascade via the FK. 404 if unknown."""
    conversation = get_chat(db, chat_id)
    db.delete(conversation)
    db.commit()


def append_message(
    db: Session,
    conversation_id: uuid.UUID,
    *,
    role: str,
    content: str,
    sources: Sequence[Any] | None = None,
    error: bool = False,
    message_id: uuid.UUID | None = None,
) -> Message:
    """Append a message row and commit it."""
    message = Message(
        id=message_id,
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources=list(sources) if sources is not None else None,
        error=error,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message
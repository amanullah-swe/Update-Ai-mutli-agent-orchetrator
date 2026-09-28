"""Chat HTTP routes: create / list / get / rename / delete.

The API speaks *chat*; the persistence layer keeps CLAUDE.md's *conversation*
entity names (see ``repository.py``). The per-chat WebSocket frame loop lives
in ``ws.py`` and is wired onto the same router below.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, WebSocket, status
from sqlalchemy.orm import Session

from app.api.deps import get_app_settings, get_db
from app.modules.chats import repository
from app.modules.chats.schemas import (
    ChatCreate,
    ChatDetail,
    ChatListResponse,
    ChatOut,
    ChatRename,
)
from app.modules.chats.ws import chat_ws_handler
from app.shared.core.config import Settings

router = APIRouter(prefix="/chats", tags=["chats"])


# --- HTTP: chat CRUD ---------------------------------------------------------


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(payload: ChatCreate, db: Session = Depends(get_db)) -> ChatOut:
    """Create a chat. ``title`` is optional (null on creation)."""
    return repository.create_chat(db, payload.title)


@router.get("", response_model=ChatListResponse)
def list_chats(db: Session = Depends(get_db)) -> ChatListResponse:
    """Chat summaries, most recently active first."""
    items, total = repository.list_chats(db)
    return ChatListResponse(items=items, total=total)


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: uuid.UUID, db: Session = Depends(get_db)) -> ChatDetail:
    """One chat with its full transcript in order. 404 if unknown."""
    conversation = repository.get_chat(db, chat_id)
    return ChatDetail.model_validate(conversation)


@router.patch("/{chat_id}", response_model=ChatOut)
def rename_chat(
    chat_id: uuid.UUID, payload: ChatRename, db: Session = Depends(get_db)
) -> ChatOut:
    """Rename a chat (bumps ``updated_at``). 404 if unknown."""
    return repository.rename_chat(db, chat_id, payload.title)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    """Delete a chat and its transcript (messages cascade). 404 if unknown."""
    repository.delete_chat(db, chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- WebSocket: message send/receive ------------------------------------------


@router.websocket("/{chat_id}/ws")
async def chat_ws(
    websocket: WebSocket,
    chat_id: uuid.UUID,
    settings: Settings = Depends(get_app_settings),
) -> None:
    """Per-chat WebSocket messaging — the frame loop lives in ``ws.py``."""
    await chat_ws_handler(websocket, chat_id, settings)
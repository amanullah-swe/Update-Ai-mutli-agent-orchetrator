"""Chat routes: HTTP CRUD (create/list/get/rename) + per-chat WebSocket messaging.

The API speaks *chat*; the service layer persists *conversations* (CLAUDE.md
entity names). All database work in the async WebSocket handler is dispatched to
the threadpool so the sync engine never blocks the event loop.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Response, WebSocket, status
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_app_settings, get_db
from app.core.config import Settings
from app.core.database import SessionLocal
from app.core.exceptions import NotFoundError
from app.schemas.chat import (
    ChatCreate,
    ChatDetail,
    ChatListResponse,
    ChatOut,
    ChatRename,
    ErrorFrame,
    MessageEndFrame,
    MessageFrame,
    MessageOut,
    MessageStartFrame,
    ReadyFrame,
    SourcesFrame,
    TokenFrame,
    UserMessageFrame,
)
from app.services import conversation_service
from app.services.chat import (
    SourcesEvent,
    TokenEvent,
    build_chat_provider,
)

log = logging.getLogger("rag.platform.chats")

router = APIRouter(prefix="/chats", tags=["chats"])


# --- HTTP: chat CRUD ---------------------------------------------------------


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(payload: ChatCreate, db: Session = Depends(get_db)) -> ChatOut:
    """Create a chat. ``title`` is optional (null on creation)."""
    return conversation_service.create_chat(db, payload.title)


@router.get("", response_model=ChatListResponse)
def list_chats(db: Session = Depends(get_db)) -> ChatListResponse:
    """Chat summaries, most recently active first."""
    items, total = conversation_service.list_chats(db)
    return ChatListResponse(items=items, total=total)


@router.get("/{chat_id}", response_model=ChatDetail)
def get_chat(chat_id: uuid.UUID, db: Session = Depends(get_db)) -> ChatDetail:
    """One chat with its full transcript in order. 404 if unknown."""
    conversation = conversation_service.get_chat(db, chat_id)
    return ChatDetail.model_validate(conversation)


@router.patch("/{chat_id}", response_model=ChatOut)
def rename_chat(
    chat_id: uuid.UUID, payload: ChatRename, db: Session = Depends(get_db)
) -> ChatOut:
    """Rename a chat (bumps ``updated_at``). 404 if unknown."""
    return conversation_service.rename_chat(db, chat_id, payload.title)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: uuid.UUID, db: Session = Depends(get_db)
) -> Response:
    """Delete a chat and its transcript (messages cascade). 404 if unknown."""
    conversation_service.delete_chat(db, chat_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- WebSocket: message send/receive ------------------------------------------


def _load_chat(chat_id: uuid.UUID) -> None:
    """Raise NotFoundError when the chat does not exist (called in the threadpool)."""
    with SessionLocal() as session:
        conversation_service.get_chat(session, chat_id)


def _append_message(
    conversation_id: uuid.UUID,
    *,
    role: str,
    content: str,
    message_id: uuid.UUID | None,
    sources: list[dict] | None = None,
) -> MessageOut:
    """Persist a message and serialize it in the threadpool (session-scoped)."""
    with SessionLocal() as session:
        message = conversation_service.append_message(
            session,
            conversation_id,
            role=role,
            content=content,
            sources=sources,
            error=False,
            message_id=message_id,
        )
        return MessageOut.model_validate(message)


@router.websocket("/{chat_id}/ws")
async def chat_ws(
    websocket: WebSocket,
    chat_id: uuid.UUID,
    settings: Settings = Depends(get_app_settings),
) -> None:
    await websocket.accept()

    # Validate the chat exists before opening the conversation loop. An unknown id
    # gets an in-band error frame and a 4404 close (the socket was accepted, so the
    # client reliably sees the reason).
    try:
        await run_in_threadpool(_load_chat, chat_id)
    except NotFoundError:
        await websocket.send_json(
            ErrorFrame(code="not_found", message="Chat not found.").model_dump()
        )
        await websocket.close(code=4404)
        return

    await websocket.send_json(ReadyFrame(chat_id=chat_id).model_dump(mode="json"))
    provider = build_chat_provider(settings)

    while True:
        try:
            raw = await websocket.receive_text()
        except Exception:  # WebSocketDisconnect — client left. noqa: BLE001
            return

        try:
            frame = UserMessageFrame.model_validate_json(raw)
        except PydanticValidationError:
            await websocket.send_json(
                ErrorFrame(
                    code="bad_request", message="Malformed message frame."
                ).model_dump()
            )
            continue

        # Persist the user message first — the transcript survives a disconnect.
        user_message = await run_in_threadpool(
            _append_message, chat_id, role="user", content=frame.content,
            message_id=None,
        )
        await websocket.send_json(
            MessageFrame(message=user_message).model_dump(mode="json")
        )

        assistant_id = uuid.uuid4()
        assistant_id_str = str(assistant_id)
        await websocket.send_json(MessageStartFrame(id=assistant_id_str).model_dump())
        parts: list[str] = []
        sources: list[dict] | None = None
        try:
            for event in provider.stream(
                frame.content, token_delay_ms=settings.mock_token_delay_ms
            ):
                if isinstance(event, TokenEvent):
                    parts.append(event.delta)
                    await websocket.send_json(
                        TokenFrame(delta=event.delta).model_dump()
                    )
                elif isinstance(event, SourcesEvent):
                    sources = [source.model_dump() for source in event.sources]
                    await websocket.send_json(
                        SourcesFrame(sources=sources).model_dump(mode="json")
                    )
            assistant_message = await run_in_threadpool(
                _append_message, chat_id, role="assistant",
                content="".join(parts), message_id=assistant_id, sources=sources,
            )
            await websocket.send_json(
                MessageEndFrame(
                    id=assistant_id_str, message=assistant_message
                ).model_dump(mode="json")
            )
        except Exception:  # noqa: BLE001 — never leak internals over the socket
            log.exception("chat turn failed for chat %s", chat_id)
            await websocket.send_json(
                ErrorFrame(
                    code="internal_error", message="Assistant generation failed."
                ).model_dump()
            )
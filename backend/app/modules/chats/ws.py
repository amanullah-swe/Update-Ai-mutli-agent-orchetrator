"""Chat WebSocket messaging — one long-lived connection per chat.

Reads ``user_message`` frames and streams the provider's events back as
``ready`` → ``message`` → ``message_start`` → ``token*`` → ``sources`` →
``message_end`` (+ in-band ``error``), persisting the transcript. All database
work is dispatched to the threadpool via ``run_in_threadpool`` so the sync
engine never blocks the event loop.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import WebSocket
from pydantic import ValidationError as PydanticValidationError
from starlette.concurrency import run_in_threadpool

from app.modules.chats import repository
from app.modules.chats.provider import SourcesEvent, TokenEvent, build_chat_provider
from app.modules.chats.schemas import (
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
from app.shared.core.config import Settings
from app.shared.core.exceptions import NotFoundError
from app.shared.database.session import SessionLocal

log = logging.getLogger("rag.platform.chats.ws")


def _load_chat(chat_id: uuid.UUID) -> None:
    """Raise NotFoundError when the chat does not exist (called in the threadpool)."""
    with SessionLocal() as session:
        repository.get_chat(session, chat_id)


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
        message = repository.append_message(
            session,
            conversation_id,
            role=role,
            content=content,
            sources=sources,
            error=False,
            message_id=message_id,
        )
        return MessageOut.model_validate(message)


async def chat_ws_handler(
    websocket: WebSocket, chat_id: uuid.UUID, settings: Settings
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
"""Chat WebSocket messaging — one long-lived connection per chat.

Reads ``user_message`` frames and streams the provider's events back as
``ready`` → ``message`` → ``message_start`` → ``token*`` → ``sources`` →
``message_end`` (+ in-band ``error``), persisting the transcript. All database
work is dispatched to the threadpool via ``run_in_threadpool`` so the sync
engine never blocks the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Sequence

from fastapi import WebSocket
from pydantic import ValidationError as PydanticValidationError
from starlette.concurrency import run_in_threadpool

from app.core.config import Settings
from app.core.exceptions import (
    LLMProviderError,
    NotFoundError,
    ValidationError as AppValidationError,
)
from app.database.session import SessionLocal
from app.features.chats import repository
from app.features.chats.provider import (
    ChatProvider,
    ProviderEvent,
    SourcesEvent,
    TokenEvent,
    build_chat_provider,
)
from app.features.chats.schemas import (
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


def _load_history(chat_id: uuid.UUID) -> list[MessageOut]:
    """Prior turns (oldest→newest) for the LLM context (threadpool)."""
    with SessionLocal() as session:
        return repository.get_chat_history(session, chat_id)


_STREAM_ENDED = object()


def _next_provider_event(iterator):
    """``next()`` that signals exhaustion instead of raising StopIteration.

    Python >= 3.14 forbids StopIteration crossing the ``run_in_executor``
    Future boundary, so we convert it to a sentinel inside the worker thread.
    """
    try:
        return next(iterator)
    except StopIteration:
        return _STREAM_ENDED


async def _stream_events(
    provider: ChatProvider,
    user_message: str,
    history: Sequence[MessageOut],
    *,
    token_delay_ms: int,
) -> AsyncIterator[ProviderEvent]:
    """Stream a blocking sync provider generator without blocking the loop.

    Each ``next()`` runs on a worker thread (the LLM's HTTP read blocks there,
    not the event loop); events are forwarded one-by-one, never materialized.
    """
    loop = asyncio.get_running_loop()
    iterator = provider.stream(
        user_message, history=history, token_delay_ms=token_delay_ms
    )
    try:
        while True:
            event = await loop.run_in_executor(None, _next_provider_event, iterator)
            if event is _STREAM_ENDED:
                return
            yield event
    finally:
        # Client disconnect / turn aborted: close the generator so its httpx
        # connection is released (a no-op once the stream is exhausted).
        await loop.run_in_executor(None, iterator.close)


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

        # Load the prior transcript BEFORE persisting the current message, so
        # the LLM sees history up to (not including) this turn.
        history = await run_in_threadpool(_load_history, chat_id)

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
            # Built per turn so a config error (e.g. missing API key) surfaces
            # in-band on the offending turn, not as a silent connect close.
            provider = build_chat_provider(settings)
            async for event in _stream_events(
                provider, frame.content, history,
                token_delay_ms=settings.mock_token_delay_ms,
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
        except AppValidationError as exc:
            # Misconfiguration (e.g. missing RAG_LLM_API_KEY) — actionable, not
            # a crash; the error frame carries the config guidance.
            await websocket.send_json(
                ErrorFrame(code=exc.code, message=exc.message).model_dump()
            )
        except LLMProviderError as exc:
            log.warning("llm provider error for chat %s: %s", chat_id, exc)
            await websocket.send_json(
                ErrorFrame(code="llm_error", message=str(exc)).model_dump()
            )
        except Exception:  # noqa: BLE001 — never leak internals over the socket
            log.exception("chat turn failed for chat %s", chat_id)
            await websocket.send_json(
                ErrorFrame(
                    code="internal_error", message="Assistant generation failed."
                ).model_dump()
            )

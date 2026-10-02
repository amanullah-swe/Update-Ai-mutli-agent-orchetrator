"""Integration tests: history helper + WS turns feed the prior transcript
to the orchestrator (real PostgreSQL, fake recording orchestrator — no network)."""

from __future__ import annotations

import uuid

from app.features.chats import repository
from app.features.chats.schemas import MessageOut
from orchestrator.events import SourcesEvent, TokenEvent


def _new_chat(client) -> str:
    return client.post("/api/chats", json={"title": "history"}).json()["id"]


def _run_turn(ws, content: str) -> list[dict]:
    ws.send_json({"type": "user_message", "content": content})
    frames: list[dict] = []
    while True:
        frame = ws.receive_json()
        frames.append(frame)
        if frame["type"] == "message_end":
            return frames


class RecordingOrchestrator:
    """Captures the history each turn was fed; streams a canned reply."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[MessageOut]]] = []

    def stream(self, user_message: str, *, history=None, token_delay_ms: int = 0):
        self.calls.append((user_message, list(history or [])))
        yield TokenEvent("ok")
        yield SourcesEvent(())


def test_get_chat_history_orders_oldest_to_newest_including_error_rows(
    client, db_session
) -> None:
    chat_id = _new_chat(client)
    cid = uuid.UUID(chat_id)
    for i in (1, 2, 3):
        role = "user" if i % 2 == 1 else "assistant"
        repository.append_message(db_session, cid, role=role, content=f"m{i}")
    # A failed turn is a real row — the helper returns it; the orchestrator skips it.
    repository.append_message(
        db_session, cid, role="assistant", content="failed", error=True
    )

    history = repository.get_chat_history(db_session, cid)
    assert [m.role for m in history] == ["user", "assistant", "user", "assistant"]
    assert [m.content for m in history] == ["m1", "m2", "m3", "failed"]
    assert all(isinstance(m, MessageOut) for m in history)


def test_ws_turns_feed_prior_history_to_the_orchestrator(client, monkeypatch) -> None:
    from app.features.chats import ws as ws_module

    recording = RecordingOrchestrator()
    monkeypatch.setattr(ws_module, "build_chat_orchestrator", lambda settings: recording)

    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "ready"
        _run_turn(websocket, "first question")
        _run_turn(websocket, "second question")

    (q1, h1) = recording.calls[0]
    (q2, h2) = recording.calls[1]
    assert q1 == "first question" and h1 == []
    assert q2 == "second question"
    assert [m.content for m in h2] == ["first question", "ok"]
    assert [m.role for m in h2] == ["user", "assistant"]
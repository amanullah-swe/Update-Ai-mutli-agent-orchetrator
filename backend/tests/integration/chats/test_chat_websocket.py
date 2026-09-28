"""Integration tests: WebSocket chat messaging (send / receive / persistence)."""

from __future__ import annotations

import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

from app.modules.chats.models import Message


def _new_chat(client) -> str:
    return client.post("/api/chats", json={"title": "ws"}).json()["id"]


def _run_turn(ws, content: str) -> list[dict]:
    """Send one user message and collect server frames until message_end."""
    ws.send_json({"type": "user_message", "content": content})
    frames: list[dict] = []
    while True:
        frame = ws.receive_json()
        frames.append(frame)
        if frame["type"] == "message_end":
            return frames


def test_websocket_sends_ready_frame(client) -> None:
    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        assert websocket.receive_json() == {"type": "ready", "chat_id": chat_id}


def test_websocket_turn_frame_sequence(client) -> None:
    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        assert websocket.receive_json()["type"] == "ready"
        frames = _run_turn(websocket, "hello there")

    types = [f["type"] for f in frames]
    assert types[0] == "message"
    assert types[1] == "message_start"
    assert "token" in types
    assert "sources" in types
    assert types[-1] == "message_end"

    user_ack = frames[0]["message"]
    assert user_ack["role"] == "user" and user_ack["content"] == "hello there"

    assistant = frames[-1]["message"]
    assert assistant["role"] == "assistant"
    assert len(assistant["sources"]) == 2


def test_websocket_persists_transcript(client, db_session) -> None:
    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        websocket.receive_json()
        _run_turn(websocket, "persist this turn")

    messages = (
        db_session.query(Message).order_by(Message.created_at).all()
    )
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[0].content == "persist this turn"
    assert len(messages[1].sources) == 2


def test_websocket_handles_multiple_turns_on_one_socket(client, db_session) -> None:
    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        websocket.receive_json()
        for i in range(2):
            frames = _run_turn(websocket, f"turn {i}")
            assert frames[-1]["message"]["content"]

    assert db_session.query(Message).count() == 4  # 2 user + 2 assistant


def test_websocket_bad_frame_errors_but_socket_stays_open(client) -> None:
    chat_id = _new_chat(client)
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as websocket:
        websocket.receive_json()
        websocket.send_text("{ this is not valid json !! ")
        error = websocket.receive_json()
        assert error["type"] == "error" and error["code"] == "bad_request"

        # the socket is still usable for a real turn
        frames = _run_turn(websocket, "still alive")
        assert frames[-1]["type"] == "message_end"


def test_websocket_unknown_chat_sends_error_and_closes_4404(client) -> None:
    unknown = str(uuid.uuid4())
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect(f"/api/chats/{unknown}/ws") as websocket:
            error = websocket.receive_json()
            assert error["type"] == "error" and error["code"] == "not_found"
            websocket.receive_json()  # triggers the disconnect
    assert excinfo.value.code == 4404
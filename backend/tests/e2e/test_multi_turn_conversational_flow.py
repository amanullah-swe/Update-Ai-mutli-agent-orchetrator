"""End-to-End Test: Multi-turn conversational flow over a single WebSocket connection."""

from __future__ import annotations

import pytest


def _run_turn(ws, content: str) -> list[dict]:
    ws.send_json({"type": "user_message", "content": content})
    frames = []
    while True:
        frame = ws.receive_json()
        frames.append(frame)
        if frame["type"] == "message_end":
            return frames


@pytest.mark.e2e
class TestMultiTurnFlow:
    def test_multi_turn_conversation_flow(self, e2e_client) -> None:
        # Create chat
        create_resp = e2e_client.post("/api/chats", json={"title": "Multi-Turn Convo"})
        chat_id = create_resp.json()["id"]

        with e2e_client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws:
            assert ws.receive_json()["type"] == "ready"

            # Turn 1
            frames1 = _run_turn(ws, "Turn 1: Initial query")
            assert frames1[-1]["type"] == "message_end"
            assert frames1[-1]["message"]["role"] == "assistant"

            # Turn 2
            frames2 = _run_turn(ws, "Turn 2: Follow up question")
            assert frames2[-1]["type"] == "message_end"
            assert frames2[-1]["message"]["role"] == "assistant"

            # Turn 3
            frames3 = _run_turn(ws, "Turn 3: Thanks for the help!")
            assert frames3[-1]["type"] == "message_end"
            assert frames3[-1]["message"]["role"] == "assistant"

        # Verify all 6 messages are persisted in order
        detail_resp = e2e_client.get(f"/api/chats/{chat_id}")
        assert detail_resp.status_code == 200
        messages = detail_resp.json()["messages"]

        assert len(messages) == 6
        expected_roles = ["user", "assistant", "user", "assistant", "user", "assistant"]
        assert [m["role"] for m in messages] == expected_roles
        assert messages[0]["content"] == "Turn 1: Initial query"
        assert messages[2]["content"] == "Turn 2: Follow up question"
        assert messages[4]["content"] == "Turn 3: Thanks for the help!"

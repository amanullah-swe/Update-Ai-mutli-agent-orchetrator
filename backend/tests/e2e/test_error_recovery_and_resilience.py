"""End-to-End Test: Error recovery, bad frames, disconnects, and resilience."""

from __future__ import annotations

import uuid
import pytest
from starlette.websockets import WebSocketDisconnect


def _run_turn(ws, content: str) -> list[dict]:
    ws.send_json({"type": "user_message", "content": content})
    frames = []
    while True:
        frame = ws.receive_json()
        frames.append(frame)
        if frame["type"] == "message_end":
            return frames


@pytest.mark.e2e
class TestErrorRecoveryAndResilience:
    def test_bad_json_frame_does_not_kill_socket(self, e2e_client) -> None:
        chat_id = e2e_client.post("/api/chats", json={"title": "Error test"}).json()["id"]

        with e2e_client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws:
            assert ws.receive_json()["type"] == "ready"

            # Send malformed JSON string
            ws.send_text("this is completely invalid json {{{")
            error_frame = ws.receive_json()
            assert error_frame["type"] == "error"
            assert error_frame["code"] == "bad_request"

            # Send malformed payload (missing content field)
            ws.send_json({"type": "user_message"})
            error_frame2 = ws.receive_json()
            assert error_frame2["type"] == "error"
            assert error_frame2["code"] == "bad_request"

            # Socket remains fully functional for a valid turn
            valid_frames = _run_turn(ws, "Hello after errors")
            assert valid_frames[-1]["type"] == "message_end"

    def test_unknown_chat_id_disconnects_with_4404(self, e2e_client) -> None:
        unknown_id = str(uuid.uuid4())
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with e2e_client.websocket_connect(f"/api/chats/{unknown_id}/ws") as ws:
                err = ws.receive_json()
                assert err["type"] == "error"
                assert err["code"] == "not_found"
                ws.receive_json()  # wait for close

        assert exc_info.value.code == 4404

    def test_client_disconnect_and_reconnect(self, e2e_client) -> None:
        chat_id = e2e_client.post("/api/chats", json={"title": "Reconnect test"}).json()["id"]

        # First connection: send turn 1, then disconnect
        with e2e_client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws1:
            ws1.receive_json()  # ready
            _run_turn(ws1, "Message on first socket")

        # Second connection: connect to same chat, send turn 2
        with e2e_client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws2:
            ready = ws2.receive_json()
            assert ready["type"] == "ready"
            assert ready["chat_id"] == chat_id
            _run_turn(ws2, "Message on reconnected socket")

        # Verify both messages are saved in database
        detail = e2e_client.get(f"/api/chats/{chat_id}").json()
        assert len(detail["messages"]) == 4  # 2 turns * 2 messages
        assert detail["messages"][0]["content"] == "Message on first socket"
        assert detail["messages"][2]["content"] == "Message on reconnected socket"

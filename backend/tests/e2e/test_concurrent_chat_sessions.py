"""End-to-End Test: Concurrent chat sessions isolation and threadpool safety."""

from __future__ import annotations

import concurrent.futures
import pytest


def _simulate_user_session(client, user_index: int) -> dict:
    # 1. Create chat
    create_resp = client.post("/api/chats", json={"title": f"User {user_index} Chat"})
    assert create_resp.status_code == 201
    chat_id = create_resp.json()["id"]

    # 2. Connect and exchange messages
    with client.websocket_connect(f"/api/chats/{chat_id}/ws") as ws:
        ready = ws.receive_json()
        assert ready["type"] == "ready"

        ws.send_json({"type": "user_message", "content": f"Hello from user {user_index}"})
        frames = []
        while True:
            frame = ws.receive_json()
            frames.append(frame)
            if frame["type"] == "message_end":
                break

    # 3. Check transcript
    transcript = client.get(f"/api/chats/{chat_id}").json()
    return {
        "chat_id": chat_id,
        "user_index": user_index,
        "message_count": len(transcript["messages"]),
        "first_content": transcript["messages"][0]["content"],
    }


@pytest.mark.e2e
class TestConcurrentChatSessions:
    def test_concurrent_independent_chats(self, e2e_client) -> None:
        num_sessions = 5

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_sessions) as executor:
            futures = [
                executor.submit(_simulate_user_session, e2e_client, i)
                for i in range(num_sessions)
            ]
            results = [f.result(timeout=15.0) for f in concurrent.futures.as_completed(futures)]

        assert len(results) == num_sessions
        # Ensure no duplicate chat IDs
        chat_ids = {r["chat_id"] for r in results}
        assert len(chat_ids) == num_sessions

        # Ensure correct message isolation
        for r in results:
            assert r["message_count"] == 2
            assert r["first_content"] == f"Hello from user {r['user_index']}"

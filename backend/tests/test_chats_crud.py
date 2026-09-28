"""Integration tests: chat CRUD over HTTP (create / list / get / rename)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from app.models import Message


def _create(client, title: str | None = None):
    body = {"title": title} if title is not None else {}
    return client.post("/api/chats", json=body)


def test_create_chat_returns_201_with_body(client) -> None:
    response = _create(client, "My chat")
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "My chat"
    uuid.UUID(body["id"])  # valid uuid
    assert "created_at" in body and "updated_at" in body


def test_create_chat_without_title_is_null(client) -> None:
    response = _create(client)
    assert response.status_code == 201
    assert response.json()["title"] is None


def test_get_chat_by_id_with_transcript(client, db_session) -> None:
    chat_id = _create(client, "talk").json()["id"]
    db_session.add(Message(conversation_id=uuid.UUID(chat_id), role="user", content="hello"))
    db_session.add(Message(conversation_id=uuid.UUID(chat_id), role="assistant", content="hi"))
    db_session.commit()

    response = client.get(f"/api/chats/{chat_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == chat_id
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "hello"


def test_get_chat_returns_404(client) -> None:
    assert client.get(f"/api/chats/{uuid.uuid4()}").status_code == 404


def test_rename_chat(client) -> None:
    chat_id = _create(client, "old name").json()["id"]
    response = client.patch(f"/api/chats/{chat_id}", json={"title": "new name"})
    assert response.status_code == 200
    assert response.json()["title"] == "new name"
    assert client.get(f"/api/chats/{chat_id}").json()["title"] == "new name"


def test_rename_missing_chat_returns_404(client) -> None:
    response = client.patch(f"/api/chats/{uuid.uuid4()}", json={"title": "x"})
    assert response.status_code == 404


def test_rename_blank_title_rejected(client) -> None:
    chat_id = _create(client, "a").json()["id"]
    response = client.patch(f"/api/chats/{chat_id}", json={"title": "   "})
    assert response.status_code == 422


def test_delete_chat_returns_204_and_removes_it(client) -> None:
    chat_id = _create(client, "to delete").json()["id"]
    response = client.delete(f"/api/chats/{chat_id}")
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/chats/{chat_id}").status_code == 404


def test_delete_chat_cascades_messages(client, db_session) -> None:
    chat_id = _create(client, "with messages").json()["id"]
    db_session.add(Message(conversation_id=uuid.UUID(chat_id), role="user", content="hello"))
    db_session.add(Message(conversation_id=uuid.UUID(chat_id), role="assistant", content="hi"))
    db_session.commit()

    assert client.delete(f"/api/chats/{chat_id}").status_code == 204
    remaining = (
        db_session.query(Message)
        .filter(Message.conversation_id == uuid.UUID(chat_id))
        .count()
    )
    assert remaining == 0


def test_delete_missing_chat_returns_404(client) -> None:
    assert client.delete(f"/api/chats/{uuid.uuid4()}").status_code == 404


def test_list_chats_orders_by_recent_activity(client, db_session) -> None:
    a = _create(client, "A").json()["id"]
    b = _create(client, "B").json()["id"]
    c = _create(client, "C").json()["id"]

    now = datetime.now(timezone.utc)
    db_session.add(
        Message(conversation_id=uuid.UUID(a), role="user", content="old",
                created_at=now - timedelta(minutes=10))
    )
    db_session.add(
        Message(conversation_id=uuid.UUID(b), role="user", content="new",
                created_at=now - timedelta(minutes=1))
    )
    db_session.commit()

    body = client.get("/api/chats").json()
    assert body["total"] == 3
    ids = [item["id"] for item in body["items"]]
    assert ids == [b, a, c]  # most recent activity first; empty chat last
    assert body["items"][0]["message_count"] == 1
    assert body["items"][2]["message_count"] == 0
    assert body["items"][2]["last_message_at"] is None


def test_list_chats_initial_total_zero(client) -> None:
    assert client.get("/api/chats").json() == {"items": [], "total": 0}
"""Unit tests for repository CRUD functions using in-memory SQLite."""

from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from app.core.exceptions import NotFoundError, ValidationError
from app.features.chats import repository
from app.features.chats.models import Conversation, Message


@pytest.mark.unit
class TestRepositoryUnit:
    def test_create_chat(self, sqlite_session) -> None:
        chat = repository.create_chat(sqlite_session, "My Test Chat")
        assert chat.id is not None
        assert chat.title == "My Test Chat"

        chat_no_title = repository.create_chat(sqlite_session, None)
        assert chat_no_title.title is None

    def test_clean_title_truncates(self, sqlite_session) -> None:
        long_title = "A" * 600
        chat = repository.create_chat(sqlite_session, long_title)
        assert len(chat.title) == repository.TITLE_MAX

    def test_get_chat_success_and_not_found(self, sqlite_session) -> None:
        chat = repository.create_chat(sqlite_session, "Find Me")
        fetched = repository.get_chat(sqlite_session, chat.id)
        assert fetched.id == chat.id
        assert fetched.title == "Find Me"

        with pytest.raises(NotFoundError):
            repository.get_chat(sqlite_session, uuid.uuid4())

    def test_list_chats(self, sqlite_session) -> None:
        items, total = repository.list_chats(sqlite_session)
        assert total == 0
        assert items == []

        c1 = repository.create_chat(sqlite_session, "Chat 1")
        c2 = repository.create_chat(sqlite_session, "Chat 2")

        items, total = repository.list_chats(sqlite_session)
        assert total == 2
        assert {item.id for item in items} == {c1.id, c2.id}

    def test_rename_chat(self, sqlite_session) -> None:
        chat = repository.create_chat(sqlite_session, "Original")
        updated = repository.rename_chat(sqlite_session, chat.id, "Renamed")
        assert updated.title == "Renamed"

        # Blank title raises ValidationError
        with pytest.raises(ValidationError, match="must not be blank"):
            repository.rename_chat(sqlite_session, chat.id, "   ")

    def test_delete_chat_and_cascades(self, sqlite_session) -> None:
        chat = repository.create_chat(sqlite_session, "To Delete")
        msg = repository.append_message(
            sqlite_session, chat.id, role="user", content="Hello in chat"
        )
        assert msg.id is not None

        repository.delete_chat(sqlite_session, chat.id)

        with pytest.raises(NotFoundError):
            repository.get_chat(sqlite_session, chat.id)

        # Verify message is also deleted
        remaining_msgs = sqlite_session.execute(
            select(Message).where(Message.conversation_id == chat.id)
        ).scalars().all()
        assert len(remaining_msgs) == 0

    def test_append_message_and_history(self, sqlite_session) -> None:
        from datetime import datetime, timedelta, timezone

        chat = repository.create_chat(sqlite_session, "Convo")
        m1 = repository.append_message(sqlite_session, chat.id, role="user", content="Msg 1")
        m2 = repository.append_message(
            sqlite_session,
            chat.id,
            role="assistant",
            content="Msg 2",
            sources=[{"document_id": "d1", "chunk_id": "c1", "snippet": "text"}],
        )
        base_time = datetime.now(timezone.utc)
        m1.created_at = base_time - timedelta(seconds=10)
        m2.created_at = base_time
        sqlite_session.commit()

        history = repository.get_chat_history(sqlite_session, chat.id)
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Msg 1"
        assert history[1].role == "assistant"
        assert history[1].content == "Msg 2"
        assert history[1].sources is not None
        assert history[1].sources[0].document_id == "d1"

        # Test limit
        limited = repository.get_chat_history(sqlite_session, chat.id, limit=1)
        assert len(limited) == 1
        assert limited[0].id == m1.id

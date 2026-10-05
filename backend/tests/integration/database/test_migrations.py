"""Integration tests for Alembic database migrations and schema lifecycle."""

from __future__ import annotations

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database.session import engine
from tests.conftest import ALEMBIC_INI


@pytest.mark.integration
class TestDatabaseMigrations:
    def test_migration_lifecycle_and_schema_inspection(self, migrated_database) -> None:
        cfg = Config(str(ALEMBIC_INI))
        cfg.set_main_option("script_location", str(ALEMBIC_INI.parent))

        # Re-run upgrade to head — must be idempotent
        command.upgrade(cfg, "head")

        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())

        assert "conversations" in table_names
        assert "messages" in table_names
        assert "chunks" in table_names
        assert "alembic_version" in table_names

        # Verify chunks columns
        chunk_cols = {col["name"]: col for col in inspector.get_columns("chunks")}
        assert "id" in chunk_cols
        assert "document_id" in chunk_cols
        assert "content" in chunk_cols
        assert "embedding" in chunk_cols
        assert "metadata" in chunk_cols

        # Verify foreign keys for messages
        message_fks = inspector.get_foreign_keys("messages")
        assert len(message_fks) >= 1
        fk = message_fks[0]
        assert fk["referred_table"] == "conversations"
        assert fk["referred_columns"] == ["id"]
        assert fk.get("options", {}).get("ondelete", "").upper() == "CASCADE"

"""Pytest fixtures: test DB env, migrations, per-test isolation, clients, helpers.

The integration suite runs against a real PostgreSQL instance (``rag_learning_test``)
with the schema applied exclusively through Alembic — the same DDL path as production.
The 007 schema is just ``conversations`` + ``messages``.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Point the app at the dedicated test database BEFORE any app import.
TEST_DATABASE_URL = "postgresql+psycopg://rag:rag@localhost:5432/rag_learning_test"
os.environ.setdefault("RAG_ENVIRONMENT", "testing")
os.environ["RAG_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["RAG_MOCK_TOKEN_DELAY_MS"] = "0"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text, create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.shared.database.base import Base  # noqa: E402
from app.shared.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

ALEMBIC_INI = REPO_ROOT / "database" / "migrations" / "alembic.ini"

ALL_TABLES = ("conversations", "messages")


@pytest.fixture(scope="session")
def migrated_database():
    """Rebuild the test schema from Alembic exactly as production does.

    Requested by the DB-backed fixtures only (``client``, ``db_session``) so pure
    unit tests never need PostgreSQL.
    """
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent))
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture()
def clean_tables():
    """Truncate all app tables (isolation + determinism). Requested via ``client``."""
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {', '.join(ALL_TABLES)} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture()
def client(migrated_database, clean_tables):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db_session(migrated_database):
    """A session against the real PostgreSQL test database, for row assertions."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def sqlite_session():
    """In-memory SQLite for pure service unit tests (dialect-agnostic models)."""
    sqlite_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(sqlite_engine)
    session = sessionmaker(bind=sqlite_engine, class_=Session, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        sqlite_engine.dispose()
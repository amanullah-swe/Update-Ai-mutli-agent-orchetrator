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
os.environ["RAG_CHAT_PROVIDER"] = "mock"  # override backend/.env which may set openrouter

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text, create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database.base import Base  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

import psycopg  # noqa: E402

ALEMBIC_INI = REPO_ROOT / "database" / "migrations" / "alembic.ini"

ALL_TABLES = ("conversations", "messages", "chunks")


def _ensure_test_database_exists() -> None:
    """Ensure rag_learning_test exists in PostgreSQL, creating it if absent."""
    for maintenance_db in ("postgres", "rag_learning"):
        try:
            conn_str = f"host=localhost port=5432 user=rag password=rag dbname={maintenance_db}"
            with psycopg.connect(conn_str, autocommit=True) as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_database WHERE datname = 'rag_learning_test'")
                    if not cur.fetchone():
                        cur.execute("CREATE DATABASE rag_learning_test")
            return
        except Exception:
            continue


@pytest.fixture(scope="session")
def migrated_database():
    """Rebuild the test schema from Alembic exactly as production does.

    Requested by the DB-backed fixtures only (``client``, ``db_session``) so pure
    unit tests never need PostgreSQL.
    """
    _ensure_test_database_exists()
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
def db_session(migrated_database, clean_tables):
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


@pytest.fixture()
def synthetic_pdf_bytes() -> bytes:
    """Generate minimal valid 2-page PDF bytes in memory using pymupdf."""
    import pymupdf

    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text(
        (50, 72),
        "RAG Platform Architecture\n\n"
        "The RAG platform uses modular swappable components behind common interfaces. "
        "Retrieval is dense vector search using pgvector."
    )
    p2 = doc.new_page()
    p2.insert_text(
        (50, 72),
        "Chunking and Embeddings\n\n"
        "Chunks are generated using sliding window overlap chunking. "
        "Embeddings are 384-dimensional dense vectors."
    )
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture()
def synthetic_pdf_path(tmp_path, synthetic_pdf_bytes) -> Path:
    """Write synthetic PDF bytes to a temporary file path."""
    pdf_file = tmp_path / "test_sample_document.pdf"
    pdf_file.write_bytes(synthetic_pdf_bytes)
    return pdf_file


@pytest.fixture()
def mock_openrouter_transport():
    """Deterministic mock transport for OpenRouter chat completions and embeddings."""
    import json
    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "/embeddings" in url_str:
            body = json.loads(request.content.decode("utf-8"))
            inputs = body.get("input", [])
            data = []
            for idx, _ in enumerate(inputs):
                vector = [0.05 * (idx + 1)] * 384
                data.append({"index": idx, "embedding": vector})
            return httpx.Response(200, json={"data": data})

        if "/chat/completions" in url_str:
            chunks = [
                'data: {"choices":[{"delta":{"content":"Mocked "}}]}\n\n',
                'data: {"choices":[{"delta":{"content":"OpenRouter "}}]}\n\n',
                'data: {"choices":[{"delta":{"content":"response."}}]}\n\n',
                "data: [DONE]\n\n",
            ]
            content = "".join(chunks).encode("utf-8")
            return httpx.Response(
                200,
                headers={"Content-Type": "text/event-stream"},
                content=content,
            )

        return httpx.Response(404, json={"error": "Not Found"})

    return httpx.MockTransport(handler)


@pytest.fixture()
def sample_chunks() -> list:
    """Pre-built test chunks with 384-dim embeddings."""
    from rag.types.chunk import Chunk, ChunkType

    vec1 = [0.1] * 384
    vec2 = [-0.1] * 384
    return [
        Chunk(
            id="test-chunk-1",
            document_id="doc-test-1",
            content="Modular RAG platform architecture with FastAPI and PostgreSQL.",
            chunk_type=ChunkType.TEXT,
            page_number=1,
            metadata={"source": "test_sample.pdf"},
            embedding=vec1,
        ),
        Chunk(
            id="test-chunk-2",
            document_id="doc-test-1",
            content="Vector embeddings are 384 dimensions matching pgvector schema.",
            chunk_type=ChunkType.TEXT,
            page_number=2,
            metadata={"source": "test_sample.pdf"},
            embedding=vec2,
        ),
    ]
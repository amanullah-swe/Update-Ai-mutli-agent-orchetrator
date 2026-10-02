"""SQLAlchemy engine and session factory.

Sync engine by design: async endpoints that touch the database (the chat
WebSocket) dispatch to the threadpool via ``starlette.concurrency``. The
FastAPI ``get_db`` dependency lives in ``app.api.deps`` so this module stays
framework-agnostic.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(
    get_settings().database_url,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session; closes it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


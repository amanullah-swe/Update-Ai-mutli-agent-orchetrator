"""Shared FastAPI dependencies used across modules."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.shared.core.config import Settings, get_settings
from app.shared.database.session import SessionLocal

__all__ = ["get_app_settings", "get_db"]


def get_app_settings() -> Settings:
    return get_settings()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a session; closes it when the request ends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
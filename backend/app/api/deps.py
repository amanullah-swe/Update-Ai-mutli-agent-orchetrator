"""Shared FastAPI dependencies."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.core.database import get_db

__all__ = ["get_app_settings", "get_db"]


def get_app_settings() -> Settings:
    return get_settings()
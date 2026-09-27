"""The combined API router mounted under /api."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    chats,
    health,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(chats.router)

__all__ = ["api_router"]
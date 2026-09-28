"""The combined API router mounted under /api.

Each module exposes a ``router``; adding a feature means creating its module
and including it here — nothing else changes.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.modules.chats.router import router as chats_router
from app.modules.health.router import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(chats_router)

__all__ = ["api_router"]
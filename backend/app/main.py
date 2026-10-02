"""FastAPI application factory and entrypoint.

Run: ``uv run uvicorn app.main:app --reload --port 8001``
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestIdMiddleware, configure_logging, get_logger
from app.database.session import engine
from app.features.chats.router import router as chats_router
from app.features.health.router import router as health_router

settings = get_settings()
log = get_logger("rag.platform.main")


@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("startup complete (env=%s)", settings.environment)
    yield
    engine.dispose()
    log.info("shutdown complete")


def create_app() -> FastAPI:
    configure_logging(settings.debug)
    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)
    app.include_router(health_router, prefix="/api")
    app.include_router(chats_router, prefix="/api")

    @app.get("/")
    def root() -> dict:
        return {
            "app": settings.app_name,
            "version": settings.version,
            "environment": settings.environment,
            "endpoints": {
                "health": "/api/health",
                "chats": "/api/chats",
                "chat_ws": "/api/chats/{chat_id}/ws",
                "docs": "/docs",
            },
        }

    return app


app = create_app()
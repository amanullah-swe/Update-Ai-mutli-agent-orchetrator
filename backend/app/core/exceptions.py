"""Typed application errors and their mapping to HTTP responses."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, get_request_id, request_id_var

log = get_logger(__name__)


class AppError(Exception):
    """Base class for expected, client-visible failures.

    Subclasses set ``status_code`` and ``code``; message is developer-facing
    detail that may be shown to API clients.
    """

    status_code: int = 500
    code: str = "app_error"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details
        if code is not None:
            self.code = code


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class StorageError(AppError):
    status_code = 500
    code = "storage_error"


def error_body(status_code: int, code: str, message: str, request_id: str) -> dict[str, Any]:
    return {
        "detail": {"code": code, "message": message},
        "request_id": request_id,
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        log.warning("app error %s -> %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(
                exc.status_code, exc.code, exc.message, get_request_id()
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        log.warning("http error %s -> %s", exc.status_code, detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(exc.status_code, "http_error", detail, get_request_id()),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled exception at %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body(
                500, "internal_error", "An unexpected error occurred.", get_request_id()
            ),
        )
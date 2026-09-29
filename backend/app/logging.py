"""Structured logging with request-id propagation (observability, CLAUDE.md)."""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Callable, TypeVar

from starlette.requests import Request
from starlette.responses import Response

T = TypeVar("T")

# ContextVar holding the current request id; read by log formatters and error
# handlers so every trace line and every 5xx/4xx body can be correlated.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    return request_id_var.get()

_LOGGER_NAME = "rag.platform"


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(debug: bool = False) -> None:
    """Idempotent root-logger setup; ``debug`` selects the format level."""
    root = logging.getLogger()
    if root.handlers:  # already configured (tests re-import)
        return
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    root.addHandler(handler)
    root.setLevel(logging.DEBUG if debug else logging.INFO)
    if debug:
        fmt = "%(asctime)s %(levelname)s %(name)s [%(request_id)s] %(message)s"
    else:
        fmt = "%(levelname)s %(name)s [%(request_id)s] %(message)s"
    handler.setFormatter(logging.Formatter(fmt))


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


class RequestIdMiddleware:
    """Assign (or honor) an X-Request-ID and echo it on the response."""

    def __init__(self, app: Callable[[Request], T]) -> None:
        self.app = app

    async def __call__(self, scope: dict, receive: Callable, send: Callable) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid)

        async def send_with_rid(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                headers.append(
                    (b"x-request-id", rid.encode("ascii"))
                )
            await send(message)

        try:
            await self.app(scope, receive, send_with_rid)
        finally:
            request_id_var.reset(token)
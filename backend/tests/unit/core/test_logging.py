"""Unit tests for structured logging and request ID tracking."""

from __future__ import annotations

import asyncio
import logging
import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from app.core.logging import (
    RequestIdFilter,
    RequestIdMiddleware,
    configure_logging,
    get_logger,
    get_request_id,
    request_id_var,
)


@pytest.mark.unit
class TestLogging:
    def test_request_id_filter_attaches_value(self) -> None:
        token = request_id_var.set("test-trace-123")
        try:
            filt = RequestIdFilter()
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg="test message", args=(), exc_info=None
            )
            assert filt.filter(record) is True
            assert getattr(record, "request_id") == "test-trace-123"
        finally:
            request_id_var.reset(token)

    def test_get_request_id_default(self) -> None:
        assert get_request_id() == "-"

    def test_configure_logging_and_get_logger(self) -> None:
        configure_logging(debug=True)
        logger = get_logger("test.subsystem")
        assert logger.name == "test.subsystem"

    @pytest.mark.asyncio
    async def test_request_id_middleware_echoes_existing_header(self) -> None:
        async def dummy_app(scope, receive, send):
            assert get_request_id() == "custom-id-999"
            response = PlainTextResponse("ok")
            await response(scope, receive, send)

        middleware = RequestIdMiddleware(dummy_app)
        headers = [(b"x-request-id", b"custom-id-999")]
        scope = {"type": "http", "headers": headers, "method": "GET", "path": "/"}

        sent_messages = []

        async def dummy_receive():
            return {"type": "http.request"}

        async def dummy_send(message):
            sent_messages.append(message)

        await middleware(scope, dummy_receive, dummy_send)

        start_message = next(m for m in sent_messages if m["type"] == "http.response.start")
        resp_headers = dict(start_message["headers"])
        assert resp_headers[b"x-request-id"] == b"custom-id-999"

    @pytest.mark.asyncio
    async def test_request_id_middleware_generates_new_id_when_missing(self) -> None:
        captured_id = None

        async def dummy_app(scope, receive, send):
            nonlocal captured_id
            captured_id = get_request_id()
            response = PlainTextResponse("ok")
            await response(scope, receive, send)

        middleware = RequestIdMiddleware(dummy_app)
        scope = {"type": "http", "headers": [], "method": "GET", "path": "/"}

        sent_messages = []

        async def dummy_receive():
            return {"type": "http.request"}

        async def dummy_send(message):
            sent_messages.append(message)

        await middleware(scope, dummy_receive, dummy_send)

        assert captured_id is not None
        assert captured_id != "-"
        assert len(captured_id) == 32  # hex uuid4

        start_message = next(m for m in sent_messages if m["type"] == "http.response.start")
        resp_headers = dict(start_message["headers"])
        assert resp_headers[b"x-request-id"].decode("ascii") == captured_id

    @pytest.mark.asyncio
    async def test_request_id_middleware_bypasses_non_http_scope(self) -> None:
        called = False

        async def dummy_app(scope, receive, send):
            nonlocal called
            called = True

        middleware = RequestIdMiddleware(dummy_app)
        scope = {"type": "websocket"}
        await middleware(scope, None, None)
        assert called is True

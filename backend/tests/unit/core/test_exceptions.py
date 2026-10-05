"""Unit tests for domain exceptions and FastAPI exception handlers."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import (
    AppError,
    ConflictError,
    LLMProviderError,
    NotFoundError,
    StorageError,
    ValidationError,
    error_body,
    register_exception_handlers,
)


@pytest.mark.unit
class TestExceptions:
    def test_app_error_defaults(self) -> None:
        err = AppError("Something went wrong")
        assert err.message == "Something went wrong"
        assert err.status_code == 500
        assert err.code == "app_error"
        assert err.details is None

    def test_app_error_custom_code_and_details(self) -> None:
        err = AppError("Failed", code="custom_fail", details={"key": "val"})
        assert err.code == "custom_fail"
        assert err.details == {"key": "val"}

    def test_subclasses_status_and_code(self) -> None:
        assert NotFoundError("not found").status_code == 404
        assert NotFoundError("not found").code == "not_found"

        assert ConflictError("conflict").status_code == 409
        assert ConflictError("conflict").code == "conflict"

        assert ValidationError("invalid").status_code == 422
        assert ValidationError("invalid").code == "validation_error"

        assert StorageError("disk error").status_code == 500
        assert StorageError("disk error").code == "storage_error"

        assert LLMProviderError("timeout").status_code == 502
        assert LLMProviderError("timeout").code == "llm_error"

    def test_error_body_structure(self) -> None:
        body = error_body(404, "not_found", "Chat 123 not found", "req-abc")
        assert body == {
            "detail": {"code": "not_found", "message": "Chat 123 not found"},
            "request_id": "req-abc",
        }

    def test_exception_handlers_in_fastapi(self) -> None:
        app = FastAPI()
        register_exception_handlers(app)

        @app.get("/raise-not-found")
        def route_not_found():
            raise NotFoundError("Resource not located")

        @app.get("/raise-llm-error")
        def route_llm():
            raise LLMProviderError("Provider unavailable")

        @app.get("/raise-unhandled")
        def route_crash():
            raise RuntimeError("Boom!")

        client = TestClient(app, raise_server_exceptions=False)

        resp404 = client.get("/raise-not-found")
        assert resp404.status_code == 404
        assert resp404.json()["detail"]["code"] == "not_found"
        assert resp404.json()["detail"]["message"] == "Resource not located"

        resp502 = client.get("/raise-llm-error")
        assert resp502.status_code == 502
        assert resp502.json()["detail"]["code"] == "llm_error"

        resp500 = client.get("/raise-unhandled")
        assert resp500.status_code == 500
        assert resp500.json()["detail"]["code"] == "internal_error"

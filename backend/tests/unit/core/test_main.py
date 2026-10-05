"""Unit tests for FastAPI main application factory, root endpoint, and middleware."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.mark.unit
class TestMainApp:
    def test_create_app_returns_fastapi_instance(self) -> None:
        app = create_app()
        assert app.title == "rag-learning-platform"
        assert app.version == "0.1.0"

    def test_root_endpoint_metadata(self) -> None:
        app = create_app()
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert body["app"] == "rag-learning-platform"
        assert body["version"] == "0.1.0"
        assert "endpoints" in body
        assert body["endpoints"]["health"] == "/api/health"
        assert body["endpoints"]["chats"] == "/api/chats"
        assert body["endpoints"]["chat_ws"] == "/api/chats/{chat_id}/ws"

    def test_cors_middleware_headers(self) -> None:
        app = create_app()
        client = TestClient(app)
        headers = {
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        }
        response = client.options("/api/chats", headers=headers)
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"

    def test_openapi_docs_available(self) -> None:
        app = create_app()
        client = TestClient(app)
        openapi_resp = client.get("/openapi.json")
        assert openapi_resp.status_code == 200
        assert "openapi" in openapi_resp.json()

        docs_resp = client.get("/docs")
        assert docs_resp.status_code == 200

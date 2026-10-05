"""Integration tests: health endpoint + request-id observability."""

from __future__ import annotations


def test_health_ok(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["environment"] == "testing"
    assert body["database"]["status"] == "ok"


def test_health_echoes_request_id(client) -> None:
    response = client.get("/api/health", headers={"X-Request-ID": "my-trace-id"})
    assert response.headers["x-request-id"] == "my-trace-id"


def test_health_generates_request_id_when_omitted(client) -> None:
    response = client.get("/api/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) == 32


def test_health_reports_unavailable_when_db_down(client, monkeypatch) -> None:
    from sqlalchemy.orm import Session
    from sqlalchemy.exc import OperationalError

    def broken_execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("Connection refused"))

    monkeypatch.setattr(Session, "execute", broken_execute)

    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "unavailable"


def test_root_endpoint_integration(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["app"] == "rag-learning-platform"
    assert body["environment"] == "testing"


def test_unknown_route_returns_error_shape(client) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body and "request_id" in body
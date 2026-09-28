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


def test_unknown_route_returns_error_shape(client) -> None:
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body and "request_id" in body
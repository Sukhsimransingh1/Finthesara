"""Tests for the versioned health endpoint."""

from fastapi.testclient import TestClient


def test_health_check_returns_service_metadata(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "agentic-finance-research",
        "version": "0.1.0",
        "environment": "local",
    }


def test_health_check_is_versioned(client: TestClient) -> None:
    assert client.get("/health").status_code == 404

from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_research_endpoint_exists() -> None:
    response = client.post(
        "/api/v1/research",
        json={
            "question": "Analyze the revenue growth of Apple.",
            "project_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    # The endpoint exists and accepts the request.
    assert response.status_code != 404


def test_research_stream_rejects_empty_question() -> None:
    response = client.post(
        "/api/v1/research/stream",
        json={
            "question": "",
            "project_id": "00000000-0000-0000-0000-000000000001",
        },
    )

    assert response.status_code == 422


def test_research_stream_rejects_invalid_project_id() -> None:
    response = client.post(
        "/api/v1/research/stream",
        json={
            "question": "Analyze Apple's revenue.",
            "project_id": "test-project",
        },
    )

    assert response.status_code == 422
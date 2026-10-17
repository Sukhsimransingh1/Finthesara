
from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_research_endpoint_exists() -> None:
    """Verify the endpoint accepts a request without calling Supabase."""
    with patch(
        "app.api.research.ResearchRepository"
    ) as repository_class:
        repository = repository_class.return_value
        repository.create_run.return_value = (
            "00000000-0000-0000-0000-000000000002"
        )
        repository.finish_run.return_value = None

        with patch(
            "app.api.research._build_runner"
        ) as build_runner:
            runner = MagicMock()
            runner.run.return_value = {
                "status": "completed",
                "final_report": "Test research report.",
                "draft_report": None,
                "human_review_required": False,
            }
            build_runner.return_value = runner

            response = client.post(
                "/api/v1/research",
                json={
                    "question": "Analyze the revenue growth of Apple.",
                    "project_id": (
                        "00000000-0000-0000-0000-000000000001"
                    ),
                },
            )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    repository.create_run.assert_called_once()
    runner.run.assert_called_once()


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

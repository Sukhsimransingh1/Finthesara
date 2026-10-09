from __future__ import annotations

from uuid import uuid4

from app.agents.state import ResearchState
from app.services.research_runner import ResearchRunner


def test_initial_research_state_is_valid() -> None:
    state: ResearchState = {
        "run_id": str(uuid4()),
        "user_id": str(uuid4()),
        "project_id": str(uuid4()),
        "original_question": "Compare revenue growth across two companies.",
        "normalized_question": (
            "Compare revenue growth across two companies."
        ),
        "retry_count": 0,
        "max_retries": 2,
        "agent_results": [],
        "evidence": [],
        "claims": [],
        "calculations": [],
        "contradictions": [],
        "errors": [],
        "status": "started",
    }

    assert state["retry_count"] == 0
    assert state["max_retries"] == 2
    assert state["original_question"]


def test_research_runner_rejects_empty_question() -> None:
    runner = object.__new__(ResearchRunner)

    try:
        runner.run(
            question="   ",
            project_id=str(uuid4()),
        )
    except ValueError as exc:
        assert str(exc) == "Research question cannot be empty."
    else:
        raise AssertionError("Expected ValueError.")
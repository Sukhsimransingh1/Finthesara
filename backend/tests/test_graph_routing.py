from __future__ import annotations

from decimal import Decimal

from app.agents.schemas import VerificationResult, VerificationStatus
from app.agents.state import ResearchState
from app.graph.routing import route_after_verification


def _state(
    *,
    status: VerificationStatus,
    retry_count: int = 0,
    max_retries: int = 2,
) -> ResearchState:
    verification_result = VerificationResult(
        status=status,
        confidence=Decimal("0.90"),
        failed_claims=[],
        unsupported_claims=[],
        contradictions=[],
        issues=[],
    )

    return {
        "run_id": "test-run",
        "user_id": None,
        "project_id": None,
        "original_question": "Analyze Example Corp financial performance.",
        "normalized_question": "Analyze Example Corp financial performance.",
        "companies": ["Example Corp"],
        "time_range_start": None,
        "time_range_end": None,
        "research_plan": None,
        "agent_results": [],
        "financial_results": [],
        "research_output": None,
        "evidence": [],
        "claims": [],
        "calculations": [],
        "contradictions": [],
        "verification_result": verification_result,
        "retry_count": retry_count,
        "max_retries": max_retries,
        "draft_report": None,
        "final_report": None,
        "human_review_required": False,
        "human_review": None,
        "errors": [],
        "status": "verification_complete",
    }


def test_pass_routes_to_synthesis() -> None:
    state = _state(status=VerificationStatus.PASS)

    assert route_after_verification(state) == "synthesis"


def test_fail_routes_to_targeted_research_when_retries_remain() -> None:
    state = _state(
        status=VerificationStatus.FAIL,
        retry_count=0,
        max_retries=2,
    )

    assert route_after_verification(state) == "targeted_research"


def test_insufficient_evidence_routes_to_targeted_research() -> None:
    state = _state(
        status=VerificationStatus.INSUFFICIENT_EVIDENCE,
        retry_count=0,
        max_retries=2,
    )

    assert route_after_verification(state) == "targeted_research"


def test_contradiction_routes_to_targeted_research() -> None:
    state = _state(
        status=VerificationStatus.CONTRADICTION,
        retry_count=0,
        max_retries=2,
    )

    assert route_after_verification(state) == "targeted_research"


def test_failed_verification_stops_after_max_retries() -> None:
    state = _state(
        status=VerificationStatus.FAIL,
        retry_count=2,
        max_retries=2,
    )

    assert route_after_verification(state) == "synthesis"


def test_insufficient_evidence_stops_after_max_retries() -> None:
    state = _state(
        status=VerificationStatus.INSUFFICIENT_EVIDENCE,
        retry_count=2,
        max_retries=2,
    )

    assert route_after_verification(state) == "synthesis"


def test_contradiction_stops_after_max_retries() -> None:
    state = _state(
        status=VerificationStatus.CONTRADICTION,
        retry_count=2,
        max_retries=2,
    )

    assert route_after_verification(state) == "synthesis"


def test_failed_verification_can_retry_at_boundary() -> None:
    state = _state(
        status=VerificationStatus.FAIL,
        retry_count=1,
        max_retries=2,
    )

    assert route_after_verification(state) == "targeted_research"


def test_pass_always_synthesizes_even_after_retries() -> None:
    state = _state(
        status=VerificationStatus.PASS,
        retry_count=2,
        max_retries=2,
    )

    assert route_after_verification(state) == "synthesis"
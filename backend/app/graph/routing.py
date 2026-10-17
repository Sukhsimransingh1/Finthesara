
from __future__ import annotations

from app.agents.schemas import VerificationStatus
from app.agents.state import ResearchState


def route_after_verification(state: ResearchState) -> str:
    """Route verification without allowing unbounded research retries."""
    verification = state.get("verification_result")

    if verification is None:
        retry_count = state.get("retry_count", 0)
        max_retries = state.get("max_retries", 0)
        return (
            "targeted_research"
            if retry_count < max_retries
            else "synthesis"
        )

    if verification.status == VerificationStatus.PASS:
        return "synthesis"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 0)

    if retry_count < max_retries:
        return "targeted_research"

    return "synthesis"

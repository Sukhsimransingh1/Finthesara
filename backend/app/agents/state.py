from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.agents.schemas import (
    AgentResult,
    Claim,
    HumanReview,
    ResearchPlan,
    VerificationResult,
)
from app.retrieval.schemas import EvidenceItem


class ResearchState(TypedDict, total=False):
    run_id: str

    user_id: str | None
    project_id: str | None

    original_question: str
    normalized_question: str

    companies: list[str]

    time_range_start: str | None
    time_range_end: str | None

    research_plan: ResearchPlan | None

    agent_results: Annotated[
        list[AgentResult],
        operator.add,
    ]

    financial_results: list[dict[str, object]]

    research_output: dict[str, object] | None

    evidence: Annotated[
        list[EvidenceItem],
        operator.add,
    ]

    claims: Annotated[
        list[Claim],
        operator.add,
    ]

    calculations: Annotated[
        list[dict[str, object]],
        operator.add,
    ]

    contradictions: Annotated[
        list[str],
        operator.add,
    ]

    verification_result: VerificationResult | None

    retry_count: int
    max_retries: int

    draft_report: str | None
    final_report: str | None

    human_review_required: bool
    human_review: HumanReview | None

    errors: Annotated[
        list[str],
        operator.add,
    ]

    status: str
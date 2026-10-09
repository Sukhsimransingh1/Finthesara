from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Financial research question.",
    )
    project_id: UUID = Field(
        ...,
        description="Supabase project UUID.",
    )
    user_id: UUID | None = Field(
        default=None,
        description="Optional authenticated user UUID.",
    )
    run_id: str | None = Field(
        default=None,
        description="Optional research run identifier.",
    )


class ResearchResponse(BaseModel):
    run_id: str
    status: str
    final_report: str | None = None
    draft_report: str | None = None
    human_review_required: bool = False
    state: dict[str, Any] | None = None


class ResearchStreamEvent(BaseModel):
    event: str
    node: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
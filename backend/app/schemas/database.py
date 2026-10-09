"""Typed internal records mirroring important persisted entities.

These are database-facing boundaries, not public API response models.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]
NonEmptyText = Annotated[str, Field(min_length=1)]


class DatabaseRecord(BaseModel):
    """Common immutable shape for records returned by repositories."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    created_at: datetime


class ProjectRecord(DatabaseRecord):
    owner_id: UUID
    name: NonEmptyText
    description: str | None
    updated_at: datetime


class ResearchRunRecord(DatabaseRecord):
    project_id: UUID
    question: NonEmptyText
    status: Literal[
        "queued", "planning", "researching", "verifying", "awaiting_review", "completed", "failed"
    ]
    updated_at: datetime


class ResearchTaskRecord(DatabaseRecord):
    research_run_id: UUID
    objective: NonEmptyText
    status: Literal["queued", "in_progress", "completed", "failed", "skipped"]


class DocumentRecord(DatabaseRecord):
    project_id: UUID
    title: NonEmptyText
    company: str | None
    document_type: str
    publication_date: date | None
    status: Literal["registered", "processing", "ready", "failed", "archived"]
    updated_at: datetime


class DocumentChunkRecord(DatabaseRecord):
    document_id: UUID
    chunk_index: int = Field(ge=0)
    content: NonEmptyText
    metadata: JsonObject = Field(default_factory=dict)


class SourceRecord(DatabaseRecord):
    project_id: UUID
    document_id: UUID | None
    source_type: Literal["document", "web", "manual", "structured_data"]
    title: str | None
    source_url: str | None


class ClaimRecord(DatabaseRecord):
    research_run_id: UUID
    research_task_id: UUID | None
    claim_text: NonEmptyText
    status: Literal["draft", "supported", "unsupported", "contradicted"]


class CalculationRecord(DatabaseRecord):
    research_run_id: UUID
    calculation_type: NonEmptyText
    inputs: JsonObject
    result: JsonObject
    unit: str | None
    source_reference: str | None
    metadata: JsonObject = Field(default_factory=dict)


class VerificationResultRecord(DatabaseRecord):
    claim_id: UUID
    status: Literal["pass", "fail", "insufficient_evidence", "contradiction"]
    reason: str | None
    evidence_ids: list[UUID] = Field(default_factory=list)

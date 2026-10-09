from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchTaskType(StrEnum):
    FINANCIAL_ANALYSIS = "financial_analysis"
    DOCUMENT_RESEARCH = "document_research"
    EXTERNAL_RESEARCH = "external_research"
    VERIFICATION = "verification"


class ResearchTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    task_type: ResearchTaskType
    description: str = Field(min_length=1)

    company: str | None = None
    metric: str | None = None

    start_date: date | None = None
    end_date: date | None = None

    required_evidence: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)

    completion_criteria: list[str] = Field(default_factory=list)


class ResearchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_question: str = Field(min_length=1)

    companies: list[str] = Field(default_factory=list)

    start_date: date | None = None
    end_date: date | None = None

    tasks: list[ResearchTask] = Field(default_factory=list)

    required_metrics: list[str] = Field(default_factory=list)

    completion_criteria: list[str] = Field(default_factory=list)


class AgentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    status: AgentStatus
    summary: str = ""

    data: dict[str, Any] = Field(default_factory=dict)

    evidence_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PlannerAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_question: str
    research_plan: ResearchPlan
    companies: list[str] = Field(default_factory=list)
    agent_results: list[AgentResult] = Field(default_factory=list)
    status: str


class FinancialAnalysisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str

    findings: list[str] = Field(default_factory=list)

    calculations: list[dict[str, Any]] = Field(default_factory=list)

    anomalies: list[str] = Field(default_factory=list)

    source_ids: list[str] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[str] = Field(default_factory=list)

    evidence_ids: list[str] = Field(default_factory=list)

    source_urls: list[str] = Field(default_factory=list)

    contradictions: list[str] = Field(default_factory=list)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)

    statement: str = Field(min_length=1)

    evidence_ids: list[str] = Field(default_factory=list)

    calculation_ids: list[str] = Field(default_factory=list)


class VerificationStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    CONTRADICTION = "contradiction"


class VerificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: VerificationStatus

    verified_claims: list[str] = Field(default_factory=list)
    failed_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)

    contradictions: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)

    confidence: Decimal = Field(
        ge=Decimal("0"),
        le=Decimal("1"),
    )


class FinancialAnalystOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    findings: list[str] = Field(default_factory=list)
    calculations: list[dict[str, Any]] = Field(default_factory=list)
    anomalies: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)


class ResearchAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)


class VerificationAgentOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result: VerificationResult
    agent_result: AgentResult


class SynthesisOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: str
    claims: list[Claim] = Field(default_factory=list)


class HumanReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class HumanReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    required: bool = False
    decision: HumanReviewDecision | None = None
    reviewer_id: str | None = None
    feedback: str | None = None
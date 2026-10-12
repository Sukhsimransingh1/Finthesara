from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LLMUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    model: str
    usage: LLMUsage
    finish_reason: str | None = None


class PlannerLLMTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1)
    task_type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    company: str | None = None
    metric: str | None = None
    required_evidence: list[str] = Field(default_factory=list)
    required_tools: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)
    @field_validator("metric", mode="before")
    @classmethod
    def normalize_metric(cls, value: object) -> object:
        """Normalize a list of metrics into a single readable string."""
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return value

class PlannerLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_question: str = Field(min_length=1)
    companies: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    required_metrics: list[str] = Field(default_factory=list)
    tasks: list[PlannerLLMTask] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)


class ResearchLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    findings: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    
    @field_validator("limitations", mode="before")
    @classmethod
    def normalize_limitations(cls, value: object) -> object:
        """Normalize a single limitation string into a list."""
        if isinstance(value, str):
            return [value] if value.strip() else []
        return value


class VerificationLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(min_length=1)
    verified_claims: list[str] = Field(default_factory=list)
    failed_claims: list[str] = Field(default_factory=list)
    unsupported_claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)


class SynthesisClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    evidence_ids: list[str] = Field(default_factory=list)
    calculation_ids: list[str] = Field(default_factory=list)


class SynthesisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: str = Field(min_length=1)
    claims: list[SynthesisClaim] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
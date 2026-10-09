from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EmbeddingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    embedding: list[float] = Field(min_length=1)
    dimension: int = Field(ge=1)


class BatchEmbeddingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    embeddings: list[list[float]] = Field(min_length=1)
    dimension: int = Field(ge=1)


class VectorSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, object]
    similarity: float = Field(ge=-1.0, le=1.0)


class VectorSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[VectorSearchResult]
    result_count: int = Field(ge=0)
class SparseSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, object]
    rank: float = Field(ge=0.0)


class SparseSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[SparseSearchResult]
    result_count: int = Field(ge=0)

class FusedSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, object]

    vector_rank: int | None = None
    sparse_rank: int | None = None

    vector_score: float | None = None
    sparse_score: float | None = None

    rrf_score: float = Field(ge=0.0)


class FusedSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    results: list[FusedSearchResult]
    result_count: int = Field(ge=0)

class RetrievalFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str | None = None
    document_type: str | None = None
    publication_date_from: date | None = None
    publication_date_to: date | None = None

    def validate_range(self) -> None:
        if (
            self.publication_date_from is not None
            and self.publication_date_to is not None
            and self.publication_date_from > self.publication_date_to
        ):
            raise ValueError(
                "publication_date_from cannot be after "
                "publication_date_to."
            )
class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str
    chunk_id: str
    document_id: str
    content: str

    company: str | None = None
    document_type: str | None = None
    publication_date: date | None = None
    page_number: int | None = None
    source_url: str | None = None

    vector_rank: int | None = None
    sparse_rank: int | None = None
    vector_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float = Field(ge=0.0)

    retrieval_methods: list[str] = Field(default_factory=list)


class EvidencePackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    project_id: UUID
    filters: RetrievalFilters | None = None

    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_count: int = Field(ge=0)

    retrieval_config: dict[str, object] = Field(default_factory=dict)
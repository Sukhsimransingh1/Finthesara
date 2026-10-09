from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """Structured metadata associated with an ingested document."""

    model_config = ConfigDict(extra="forbid")

    filename: str
    file_path: str
    document_type: str = Field(default="unknown")
    company: str | None = None
    publication_date: date | None = None
    source_url: str | None = None


class IngestedPage(BaseModel):
    """A cleaned document page."""

    model_config = ConfigDict(extra="forbid")

    page_number: int
    text: str


class IngestedChunk(BaseModel):
    """A cleaned retrieval chunk with provenance."""

    model_config = ConfigDict(extra="forbid")

    chunk_index: int
    text: str
    page_number: int
    start_char: int
    end_char: int


class IngestionResult(BaseModel):
    """Complete deterministic result of document ingestion."""

    model_config = ConfigDict(extra="forbid")

    metadata: DocumentMetadata
    pages: list[IngestedPage]
    chunks: list[IngestedChunk]

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)
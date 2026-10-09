from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PersistedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    title: str
    company: str | None = None
    document_type: str
    publication_date: str | None = None
    source_url: str | None = None
    status: str


class PersistedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    page_number: int
    start_char: int
    end_char: int
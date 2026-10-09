from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import UUID

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.retrieval.embeddings import EmbeddingService
from app.schemas.ingestion import IngestionResult
from app.schemas.persistence import PersistedChunk, PersistedDocument

EXPECTED_EMBEDDING_DIMENSION = 768


def _content_hash(result: IngestionResult) -> str:
    content = "\n".join(page.text for page in result.pages)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _row_as_dict(row: Any) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise RuntimeError(
            "Supabase returned an unexpected row format."
        )

    return row


def _format_pgvector(vector: list[float]) -> str:
    """Convert a Python vector into PostgreSQL pgvector input format."""

    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"expected {EXPECTED_EMBEDDING_DIMENSION}, "
            f"got {len(vector)}."
        )

    return "[" + ",".join(str(value) for value in vector) + "]"


class DocumentPersistenceService:
    """Persist ingested documents, chunks, and semantic embeddings."""

    def __init__(
        self,
        *,
        client: Client | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.client = client or get_supabase_client()
        self.embedding_service = embedding_service or EmbeddingService()

    def persist(
        self,
        result: IngestionResult,
        *,
        project_id: UUID,
    ) -> tuple[PersistedDocument, list[PersistedChunk]]:
        if not result.chunks:
            raise ValueError(
                "Cannot persist a document without chunks."
            )

        # ---------------------------------------------------------
        # Step 1: Generate all embeddings BEFORE touching the DB.
        # ---------------------------------------------------------
        chunk_texts = [chunk.text for chunk in result.chunks]

        embedding_result = self.embedding_service.embed_documents(
            chunk_texts
        )

        if embedding_result.dimension != EXPECTED_EMBEDDING_DIMENSION:
            raise RuntimeError(
                "Embedding service returned an unexpected dimension: "
                f"{embedding_result.dimension}."
            )

        if len(embedding_result.embeddings) != len(result.chunks):
            raise RuntimeError(
                "Number of embeddings does not match number of chunks."
            )

        # ---------------------------------------------------------
        # Step 2: Build document payload.
        # ---------------------------------------------------------
        document_payload: dict[str, Any] = {
            "project_id": str(project_id),
            "title": result.metadata.filename,
            "company": result.metadata.company,
            "document_type": result.metadata.document_type,
            "publication_date": (
                result.metadata.publication_date.isoformat()
                if result.metadata.publication_date
                else None
            ),
            "source_url": result.metadata.source_url,
            "storage_path": str(Path(result.metadata.file_path)),
            "content_hash": _content_hash(result),
            "status": "ready",
            "metadata": {
                "filename": result.metadata.filename,
                "page_count": result.page_count,
                "chunk_count": result.chunk_count,
                "embedding_model": "BAAI/bge-base-en-v1.5",
                "embedding_dimension": EXPECTED_EMBEDDING_DIMENSION,
            },
        }

        # ---------------------------------------------------------
        # Step 3: Persist document.
        # ---------------------------------------------------------
        document_response = (
            self.client
            .table("documents")
            .insert(document_payload)
            .execute()
        )

        if not document_response.data:
            raise RuntimeError(
                "Failed to persist document."
            )

        document_row = _row_as_dict(
            document_response.data[0]
        )

        document_id = UUID(str(document_row["id"]))

        # ---------------------------------------------------------
        # Step 4: Build chunk payloads with embeddings.
        # ---------------------------------------------------------
        chunk_payloads: list[dict[str, Any]] = []

        for chunk, embedding in zip(
            result.chunks,
            embedding_result.embeddings,
            strict=True,
        ):
            chunk_payloads.append(
                {
                    "document_id": str(document_id),
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.text,
                    "embedding": _format_pgvector(embedding),
                    "metadata": {
                        "page_number": chunk.page_number,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "embedding_model": (
                            "BAAI/bge-base-en-v1.5"
                        ),
                        "embedding_dimension": (
                            EXPECTED_EMBEDDING_DIMENSION
                        ),
                    },
                }
            )

        # ---------------------------------------------------------
        # Step 5: Persist chunks.
        # ---------------------------------------------------------
        try:
            chunk_response = (
                self.client
                .table("document_chunks")
                .insert(chunk_payloads)
                .execute()
            )
        except Exception:
            # The document exists but its chunks failed.
            # Remove the orphan document so the DB does not contain
            # an incomplete ingestion result.
            try:
                (
                    self.client
                    .table("documents")
                    .delete()
                    .eq("id", str(document_id))
                    .execute()
                )
            except Exception:
                # Preserve the original persistence error.
                pass

            raise

        if not chunk_response.data:
            try:
                (
                    self.client
                    .table("documents")
                    .delete()
                    .eq("id", str(document_id))
                    .execute()
                )
            except Exception:
                pass

            raise RuntimeError(
                "Document was persisted, but chunks failed to persist."
            )

        # ---------------------------------------------------------
        # Step 6: Build persisted chunk schemas.
        # ---------------------------------------------------------
        persisted_chunks: list[PersistedChunk] = []

        for raw_row in chunk_response.data:
            row = _row_as_dict(raw_row)

            metadata = row.get("metadata")

            if not isinstance(metadata, dict):
                raise RuntimeError(
                    "Persisted chunk metadata is invalid."
                )

            persisted_chunks.append(
                PersistedChunk(
                    id=UUID(str(row["id"])),
                    document_id=UUID(
                        str(row["document_id"])
                    ),
                    chunk_index=int(row["chunk_index"]),
                    content=str(row["content"]),
                    page_number=int(
                        metadata["page_number"]
                    ),
                    start_char=int(
                        metadata["start_char"]
                    ),
                    end_char=int(
                        metadata["end_char"]
                    ),
                )
            )

        # ---------------------------------------------------------
        # Step 7: Build persisted document schema.
        # ---------------------------------------------------------
        persisted_document = PersistedDocument(
            id=document_id,
            project_id=UUID(
                str(document_row["project_id"])
            ),
            title=str(document_row["title"]),
            company=(
                str(document_row["company"])
                if document_row.get("company") is not None
                else None
            ),
            document_type=str(
                document_row["document_type"]
            ),
            publication_date=(
                str(document_row["publication_date"])
                if document_row.get("publication_date")
                else None
            ),
            source_url=(
                str(document_row["source_url"])
                if document_row.get("source_url") is not None
                else None
            ),
            status=str(document_row["status"]),
        )

        return persisted_document, persisted_chunks
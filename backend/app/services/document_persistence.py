
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from postgrest.exceptions import APIError
from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.retrieval.embeddings import EmbeddingService
from app.schemas.ingestion import IngestionResult
from app.schemas.persistence import PersistedChunk, PersistedDocument

logger = logging.getLogger(__name__)

EXPECTED_EMBEDDING_DIMENSION = 768
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"


def _content_hash(result: IngestionResult) -> str:
    """Return a stable hash of the extracted document text."""
    content = "\n".join(page.text for page in result.pages)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _row_as_dict(row: Any) -> dict[str, Any]:
    """Validate a row returned by Supabase."""
    if not isinstance(row, dict):
        raise RuntimeError("Supabase returned an unexpected row format.")
    return row


def _format_pgvector(vector: list[float]) -> str:
    """Convert a Python vector into PostgreSQL pgvector input format."""
    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"expected {EXPECTED_EMBEDDING_DIMENSION}, got {len(vector)}."
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
            raise ValueError("Cannot persist a document without chunks.")

        content_hash = _content_hash(result)

        # Step 1: Detect identical content already indexed in this project.
        # This check improves the error message but is not an atomic
        # uniqueness guarantee; database constraints remain authoritative.
        if not result.chunks:
            raise ValueError("Cannot persist a document without chunks.")

        content_hash = _content_hash(result)
        
        
        # Step 1: Generate embeddings before inserting database records.
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
        ##step 2
        try:
            existing_response = (
                self.client.table("documents")
                .select("id,title,status")
                .eq("project_id", str(project_id))
                .eq("content_hash", content_hash)
                .limit(1)
                .execute()
            )
        except APIError:
            logger.exception(
                "Failed to check existing documents. project_id=%s",
                project_id,
            )
            raise RuntimeError(
                "Could not check whether this document already exists."
            ) from None

        existing_rows = getattr(existing_response, "data", None)

        if isinstance(existing_rows, list) and existing_rows:
            existing = existing_rows[0]

            if isinstance(existing, dict):
                existing_title = existing.get(
                    "title", "existing document"
                )
                existing_status = existing.get("status", "unknown")

                raise ValueError(
                    "This document's content is already registered in "
                    f"this project as '{existing_title}' "
                    f"(status: {existing_status})."
                )
        # Step 3: Build the document payload.
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
            "content_hash": content_hash,
            "status": "processing",
            "metadata": {
                "filename": result.metadata.filename,
                "page_count": result.page_count,
                "chunk_count": result.chunk_count,
                "embedding_model": EMBEDDING_MODEL,
                "embedding_dimension": EXPECTED_EMBEDDING_DIMENSION,
            },
        }

        # Step 4: Insert the document record.
        try:
            document_response = (
                self.client.table("documents")
                .insert(document_payload)
                .execute()
            )
        except APIError as exc:
            error_code = getattr(exc, "code", None)

            if error_code == "23505":
                raise ValueError(
                    "This document conflicts with an existing database "
                    "record. It may already be indexed."
                ) from None

            logger.exception(
                "Failed to insert document. project_id=%s filename=%s",
                project_id,
                result.metadata.filename,
            )
            raise RuntimeError(
                "Failed to save the document record. "
                "Check backend logs for details."
            ) from None

        if not document_response.data:
            raise RuntimeError("Failed to persist document.")

        document_row = _row_as_dict(document_response.data[0])
        document_id = UUID(str(document_row["id"]))

        # Step 5: Prepare chunk payloads.
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
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding_dimension": (
                            EXPECTED_EMBEDDING_DIMENSION
                        ),
                    },
                }
            )

        # Step 6: Insert chunks and remove the incomplete document
        # if chunk persistence fails.
        try:
            chunk_response = (
                self.client.table("document_chunks")
                .insert(chunk_payloads)
                .execute()
            )

            if not chunk_response.data:
                raise RuntimeError(
                    "Document was created, but no chunks were persisted."
                )

        except Exception as exc:
            logger.exception(
                "Chunk persistence failed. document_id=%s",
                document_id,
            )

            try:
                (
                    self.client.table("documents")
                    .delete()
                    .eq("id", str(document_id))
                    .eq("project_id", str(project_id))
                    .execute()
                )
            except Exception:
                logger.exception(
                    "Failed to clean up incomplete document. "
                    "document_id=%s",
                    document_id,
                )

            if isinstance(exc, RuntimeError):
                raise

            raise RuntimeError(
                "Document chunks could not be saved. "
                "The incomplete document cleanup was attempted."
            ) from None

        # Step 7: Validate persisted chunks.
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
                    document_id=UUID(str(row["document_id"])),
                    chunk_index=int(row["chunk_index"]),
                    content=str(row["content"]),
                    page_number=int(metadata["page_number"]),
                    start_char=int(metadata["start_char"]),
                    end_char=int(metadata["end_char"]),
                )
            )

        # Step 8: Mark the document ready after chunks are persisted.
        try:
            (
                self.client.table("documents")
                .update({"status": "ready"})
                .eq("id", str(document_id))
                .eq("project_id", str(project_id))
                .execute()
            )
        except Exception as exc:
            logger.exception(
                "Failed to mark document ready. document_id=%s",
                document_id,
            )
            raise RuntimeError(
                "Document content was saved, but its final status "
                "could not be confirmed. Check backend logs."
            ) from exc

        persisted_document = PersistedDocument(
            id=document_id,
            project_id=UUID(str(document_row["project_id"])),
            title=str(document_row["title"]),
            company=document_row.get("company"),
            document_type=str(document_row["document_type"]),
            publication_date=document_row.get("publication_date"),
            source_url=document_row.get("source_url"),
            status="ready",
        )

        return persisted_document, persisted_chunks
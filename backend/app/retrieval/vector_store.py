from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.retrieval.embeddings import EmbeddingService
from app.retrieval.schemas import (
    RetrievalFilters,
    VectorSearchResponse,
    VectorSearchResult,
)

EXPECTED_EMBEDDING_DIMENSION = 768


def _format_pgvector(vector: list[float]) -> str:
    """Convert a Python embedding into pgvector input format."""

    if len(vector) != EXPECTED_EMBEDDING_DIMENSION:
        raise ValueError(
            "Embedding dimension mismatch: "
            f"expected {EXPECTED_EMBEDDING_DIMENSION}, "
            f"got {len(vector)}."
        )

    return "[" + ",".join(str(value) for value in vector) + "]"


def _row_as_dict(row: Any) -> dict[str, Any]:
    """Validate and normalize a Supabase response row."""

    if not isinstance(row, dict):
        raise RuntimeError(
            "Supabase returned an unexpected vector search row."
        )

    return cast(dict[str, Any], row)


def _response_rows(data: Any) -> list[Any]:
    """Normalize Supabase RPC response data into a list of rows."""

    if data is None:
        return []

    if not isinstance(data, list):
        raise RuntimeError(
            "Supabase returned an unexpected vector search response."
        )

    return data


def _normalize_metadata(value: Any) -> dict[str, object]:
    """Normalize Supabase JSON metadata into application metadata."""

    if not isinstance(value, dict):
        return {}

    return cast(dict[str, object], value)


class VectorRetriever:
    """Retrieve semantically similar document chunks using pgvector."""

    def __init__(
        self,
        *,
        client: Client | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self.client = client or get_supabase_client()
        self.embedding_service = embedding_service or EmbeddingService()

    def search(
        self,
        query: str,
        *,
        project_id: UUID,
        top_k: int = 8,
        similarity_threshold: float = 0.0,
        filters: RetrievalFilters | None = None,
    ) -> VectorSearchResponse:
        """Search project-scoped document chunks by semantic similarity."""

        if not query.strip():
            raise ValueError(
                "Vector search query cannot be empty."
            )

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than or equal to 1."
            )

        if top_k > 100:
            raise ValueError(
                "top_k cannot exceed 100."
            )

        if not 0.0 <= similarity_threshold <= 1.0:
            raise ValueError(
                "similarity_threshold must be between 0.0 and 1.0."
            )

        if filters is not None:
            filters.validate_range()

        embedding_result = self.embedding_service.embed_text(query)

        if embedding_result.dimension != EXPECTED_EMBEDDING_DIMENSION:
            raise RuntimeError(
                "Query embedding has an unexpected dimension: "
                f"{embedding_result.dimension}."
            )

        query_embedding = _format_pgvector(
            embedding_result.embedding
        )

        rpc_params: dict[str, object] = {
            "query_embedding": query_embedding,
            "match_count": top_k,
            "match_threshold": similarity_threshold,
            "filter_project_id": str(project_id),
            "filter_company": (
                filters.company
                if filters is not None
                else None
            ),
            "filter_document_type": (
                filters.document_type
                if filters is not None
                else None
            ),
            "filter_publication_date_from": (
                filters.publication_date_from.isoformat()
                if filters is not None
                and filters.publication_date_from is not None
                else None
            ),
            "filter_publication_date_to": (
                filters.publication_date_to.isoformat()
                if filters is not None
                and filters.publication_date_to is not None
                else None
            ),
        }

        response = self.client.rpc(
            "match_document_chunks",
            rpc_params,
        ).execute()

        rows = _response_rows(response.data)

        results: list[VectorSearchResult] = []

        for raw_row in rows:
            row = _row_as_dict(raw_row)

            metadata = _normalize_metadata(
                row.get("metadata")
            )

            similarity = float(row["similarity"])

            if not -1.0 <= similarity <= 1.0:
                raise RuntimeError(
                    "Vector search returned an invalid similarity score."
                )

            results.append(
                VectorSearchResult(
                    chunk_id=str(row["id"]),
                    document_id=str(row["document_id"]),
                    chunk_index=int(row["chunk_index"]),
                    content=str(row["content"]),
                    metadata=metadata,
                    similarity=similarity,
                )
            )

        return VectorSearchResponse(
            query=query,
            results=results,
            result_count=len(results),
        )
from __future__ import annotations

from typing import Any, Protocol, cast
from uuid import UUID

from app.db.supabase_client import get_supabase_client
from app.retrieval.schemas import (
    RetrievalFilters,
    SparseSearchResponse,
    SparseSearchResult,
)


class SparseSearchClient(Protocol):
    """Minimal client interface required by SparseRetriever."""

    def rpc(
        self,
        function_name: str,
        params: dict[str, object],
    ) -> Any:
        ...


def _row_as_dict(row: Any) -> dict[str, Any]:
    """Validate and normalize a Supabase response row."""

    if not isinstance(row, dict):
        raise RuntimeError(
            "Supabase returned an unexpected sparse search row."
        )

    return cast(dict[str, Any], row)


def _response_rows(data: Any) -> list[Any]:
    """Normalize Supabase RPC response data into a list of rows."""

    if data is None:
        return []

    if not isinstance(data, list):
        raise RuntimeError(
            "Supabase returned an unexpected sparse search response."
        )

    return data


def _normalize_metadata(value: Any) -> dict[str, object]:
    """Normalize Supabase JSON metadata into application metadata."""

    if not isinstance(value, dict):
        return {}

    return cast(dict[str, object], value)


class SparseRetriever:
    """Retrieve document chunks using PostgreSQL full-text search."""

    def __init__(
        self,
        *,
        client: SparseSearchClient | None = None,
    ) -> None:
        self.client = client or get_supabase_client()

    def search(
        self,
        query: str,
        *,
        project_id: UUID,
        top_k: int = 8,
        filters: RetrievalFilters | None = None,
    ) -> SparseSearchResponse:
        """Search project-scoped document chunks using PostgreSQL FTS."""

        if not query.strip():
            raise ValueError("Sparse search query cannot be empty.")

        if top_k < 1:
            raise ValueError(
                "top_k must be greater than or equal to 1."
            )

        if top_k > 100:
            raise ValueError("top_k cannot exceed 100.")

        if filters is not None:
            filters.validate_range()

        response = self.client.rpc(
            "search_document_chunks",
            {
                "search_query": query,
                "match_count": top_k,
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
            },
        ).execute()

        rows = _response_rows(response.data)

        results: list[SparseSearchResult] = []

        for raw_row in rows:
            row = _row_as_dict(raw_row)

            rank = float(row["rank"])

            if rank < 0.0:
                raise RuntimeError(
                    "Sparse search returned an invalid rank."
                )

            results.append(
                SparseSearchResult(
                    chunk_id=str(row["id"]),
                    document_id=str(row["document_id"]),
                    chunk_index=int(row["chunk_index"]),
                    content=str(row["content"]),
                    metadata=_normalize_metadata(
                        row.get("metadata")
                    ),
                    rank=rank,
                )
            )

        return SparseSearchResponse(
            query=query,
            results=results,
            result_count=len(results),
        )
from __future__ import annotations

from dataclasses import dataclass

from app.retrieval.schemas import (
    FusedSearchResponse,
    FusedSearchResult,
    SparseSearchResponse,
    VectorSearchResponse,
)

DEFAULT_RRF_K = 60


@dataclass
class _FusedItem:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, object]
    vector_rank: int | None = None
    sparse_rank: int | None = None
    vector_score: float | None = None
    sparse_score: float | None = None
    rrf_score: float = 0.0


def reciprocal_rank_fusion(
    vector_response: VectorSearchResponse,
    sparse_response: SparseSearchResponse,
    *,
    top_k: int = 10,
    k: int = DEFAULT_RRF_K,
    vector_weight: float = 1.0,
    sparse_weight: float = 1.0,
) -> FusedSearchResponse:
    """Fuse vector and sparse retrieval results using weighted RRF."""

    if top_k < 1:
        raise ValueError("top_k must be greater than or equal to 1.")

    if top_k > 100:
        raise ValueError("top_k cannot exceed 100.")

    if k <= 0:
        raise ValueError("k must be greater than 0.")

    if vector_weight < 0:
        raise ValueError("vector_weight cannot be negative.")

    if sparse_weight < 0:
        raise ValueError("sparse_weight cannot be negative.")

    items: dict[str, _FusedItem] = {}

    # ------------------------------------------------------------------
    # Vector results
    # ------------------------------------------------------------------
    for vector_rank, vector_result in enumerate(
        vector_response.results,
        start=1,
    ):
        item = items.get(vector_result.chunk_id)

        if item is None:
            item = _FusedItem(
                chunk_id=vector_result.chunk_id,
                document_id=vector_result.document_id,
                chunk_index=vector_result.chunk_index,
                content=vector_result.content,
                metadata=vector_result.metadata,
            )
            items[vector_result.chunk_id] = item

        item.vector_rank = vector_rank
        item.vector_score = vector_result.similarity
        item.rrf_score += vector_weight / (k + vector_rank)

    # ------------------------------------------------------------------
    # Sparse / lexical results
    # ------------------------------------------------------------------
    for sparse_rank, sparse_result in enumerate(
        sparse_response.results,
        start=1,
    ):
        item = items.get(sparse_result.chunk_id)

        if item is None:
            item = _FusedItem(
                chunk_id=sparse_result.chunk_id,
                document_id=sparse_result.document_id,
                chunk_index=sparse_result.chunk_index,
                content=sparse_result.content,
                metadata=sparse_result.metadata,
            )
            items[sparse_result.chunk_id] = item

        item.sparse_rank = sparse_rank
        item.sparse_score = sparse_result.rank
        item.rrf_score += sparse_weight / (k + sparse_rank)

    # ------------------------------------------------------------------
    # Sort by RRF score.
    #
    # chunk_id is used as a deterministic tie-breaker so that
    # identical scores always produce the same ordering.
    # ------------------------------------------------------------------
    ordered_items = sorted(
        items.values(),
        key=lambda item: (-item.rrf_score, item.chunk_id),
    )[:top_k]

    results = [
        FusedSearchResult(
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            chunk_index=item.chunk_index,
            content=item.content,
            metadata=item.metadata,
            vector_rank=item.vector_rank,
            sparse_rank=item.sparse_rank,
            vector_score=item.vector_score,
            sparse_score=item.sparse_score,
            rrf_score=item.rrf_score,
        )
        for item in ordered_items
    ]

    return FusedSearchResponse(
        query=vector_response.query,
        results=results,
        result_count=len(results),
    )
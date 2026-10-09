from __future__ import annotations

import pytest
from app.retrieval.rrf import reciprocal_rank_fusion
from app.retrieval.schemas import (
    SparseSearchResponse,
    SparseSearchResult,
    VectorSearchResponse,
    VectorSearchResult,
)


def _vector(
    chunk_id: str,
    similarity: float,
) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        chunk_index=0,
        content=f"content-{chunk_id}",
        metadata={},
        similarity=similarity,
    )


def _sparse(
    chunk_id: str,
    rank: float,
) -> SparseSearchResult:
    return SparseSearchResult(
        chunk_id=chunk_id,
        document_id=f"doc-{chunk_id}",
        chunk_index=0,
        content=f"content-{chunk_id}",
        metadata={},
        rank=rank,
    )


def test_rrf_fuses_results() -> None:
    vector = VectorSearchResponse(
        query="revenue",
        results=[
            _vector("a", 0.95),
            _vector("b", 0.90),
        ],
        result_count=2,
    )

    sparse = SparseSearchResponse(
        query="revenue",
        results=[
            _sparse("b", 1.2),
            _sparse("c", 0.8),
        ],
        result_count=2,
    )

    response = reciprocal_rank_fusion(
        vector,
        sparse,
        top_k=3,
    )

    assert response.result_count == 3

    by_id = {
        result.chunk_id: result
        for result in response.results
    }

    assert by_id["b"].vector_rank == 2
    assert by_id["b"].sparse_rank == 1
    assert by_id["a"].vector_rank == 1
    assert by_id["c"].sparse_rank == 2


def test_rrf_rewards_results_present_in_both_lists() -> None:
    vector = VectorSearchResponse(
        query="revenue",
        results=[
            _vector("shared", 0.9),
            _vector("vector-only", 0.8),
        ],
        result_count=2,
    )

    sparse = SparseSearchResponse(
        query="revenue",
        results=[
            _sparse("shared", 1.0),
            _sparse("sparse-only", 0.7),
        ],
        result_count=2,
    )

    response = reciprocal_rank_fusion(
        vector,
        sparse,
    )

    assert response.results[0].chunk_id == "shared"


def test_rrf_respects_top_k() -> None:
    vector = VectorSearchResponse(
        query="revenue",
        results=[
            _vector("a", 0.9),
            _vector("b", 0.8),
            _vector("c", 0.7),
        ],
        result_count=3,
    )

    sparse = SparseSearchResponse(
        query="revenue",
        results=[],
        result_count=0,
    )

    response = reciprocal_rank_fusion(
        vector,
        sparse,
        top_k=2,
    )

    assert response.result_count == 2


def test_rrf_rejects_invalid_parameters() -> None:
    vector = VectorSearchResponse(
        query="revenue",
        results=[],
        result_count=0,
    )

    sparse = SparseSearchResponse(
        query="revenue",
        results=[],
        result_count=0,
    )

    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            vector,
            sparse,
            top_k=0,
        )

    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            vector,
            sparse,
            k=0,
        )

    with pytest.raises(ValueError):
        reciprocal_rank_fusion(
            vector,
            sparse,
            vector_weight=-1,
        )
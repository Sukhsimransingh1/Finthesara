from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from app.retrieval.schemas import SparseSearchResponse
from app.retrieval.sparse_store import SparseRetriever

PROJECT_ID = UUID("bc8d4f9e-15d5-44f9-a896-c131421d8d4a")


class FakeResponse:
    def __init__(self, data: Any) -> None:
        self.data = data


class FakeQuery:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    def execute(self) -> FakeResponse:
        return self.response


class FakeClient:
    def __init__(self, data: list[dict[str, Any]]) -> None:
        self.data = data
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def rpc(
        self,
        function_name: str,
        params: dict[str, Any],
    ) -> FakeQuery:
        self.calls.append((function_name, params))
        return FakeQuery(FakeResponse(self.data))


def _sample_row(rank: float = 0.91) -> dict[str, Any]:
    return {
        "id": str(uuid4()),
        "document_id": str(uuid4()),
        "chunk_index": 2,
        "content": "Revenue increased by 18 percent.",
        "metadata": {
            "page_number": 12,
            "company": "Example Corp",
        },
        "rank": rank,
    }


def test_sparse_search_returns_ranked_results() -> None:
    client = FakeClient(
        [
            _sample_row(0.92),
            _sample_row(0.71),
        ]
    )

    retriever = SparseRetriever(client=client)

    response = retriever.search(
        "revenue growth",
        project_id=PROJECT_ID,
        top_k=5,
    )

    assert isinstance(response, SparseSearchResponse)
    assert response.result_count == 2
    assert response.results[0].rank == 0.92


def test_sparse_search_passes_project_filter() -> None:
    client = FakeClient([_sample_row()])

    retriever = SparseRetriever(client=client)

    retriever.search(
        "revenue",
        project_id=PROJECT_ID,
        top_k=5,
    )

    function_name, params = client.calls[0]

    assert function_name == "search_document_chunks"
    assert params["filter_project_id"] == str(PROJECT_ID)
    assert params["match_count"] == 5


def test_sparse_search_rejects_empty_query() -> None:
    retriever = SparseRetriever(
        client=FakeClient([])
    )

    with pytest.raises(ValueError):
        retriever.search(
            "   ",
            project_id=PROJECT_ID,
        )


def test_sparse_search_rejects_invalid_top_k() -> None:
    retriever = SparseRetriever(
        client=FakeClient([])
    )

    with pytest.raises(ValueError):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            top_k=0,
        )

    with pytest.raises(ValueError):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            top_k=101,
        )


def test_sparse_search_rejects_invalid_rank() -> None:
    client = FakeClient([_sample_row(-0.1)])

    retriever = SparseRetriever(client=client)

    with pytest.raises(RuntimeError):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
        )


def test_sparse_search_handles_no_results() -> None:
    retriever = SparseRetriever(
        client=FakeClient([])
    )

    response = retriever.search(
        "nonexistent financial concept",
        project_id=PROJECT_ID,
    )

    assert response.result_count == 0
    assert response.results == []
from __future__ import annotations

from datetime import date
from unittest.mock import Mock
from uuid import UUID

import pytest
from app.retrieval.embeddings import EXPECTED_DIMENSION
from app.retrieval.schemas import RetrievalFilters
from app.retrieval.vector_store import VectorRetriever

PROJECT_ID = UUID(
    "bc8d4f9e-15d5-44f9-a896-c131421d8d4a"
)


def create_embedding_service() -> Mock:
    service = Mock()

    service.embed_text.return_value = Mock(
        text="What was revenue growth?",
        embedding=[0.1] * EXPECTED_DIMENSION,
        dimension=EXPECTED_DIMENSION,
    )

    return service


def create_supabase_client() -> Mock:
    client = Mock()

    response = Mock()
    response.data = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "document_id": (
                "22222222-2222-2222-2222-222222222222"
            ),
            "chunk_index": 3,
            "content": (
                "Revenue increased by 14.2% year over year."
            ),
            "metadata": {
                "page_number": 12,
                "document_type": "10-K",
                "company": "Apple",
            },
            "similarity": 0.91,
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "document_id": (
                "44444444-4444-4444-4444-444444444444"
            ),
            "chunk_index": 7,
            "content": (
                "Operating margin increased to 18.7%."
            ),
            "metadata": {
                "page_number": 18,
                "document_type": "10-K",
                "company": "Apple",
            },
            "similarity": 0.84,
        },
    ]

    client.rpc.return_value.execute.return_value = response

    return client


def test_vector_search_returns_ranked_results() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    response = retriever.search(
        "What was revenue growth?",
        project_id=PROJECT_ID,
        top_k=5,
        similarity_threshold=0.7,
    )

    assert response.query == "What was revenue growth?"
    assert response.result_count == 2
    assert len(response.results) == 2

    assert response.results[0].similarity == 0.91
    assert response.results[0].chunk_index == 3
    assert "14.2%" in response.results[0].content


def test_vector_search_uses_project_filter() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    retriever.search(
        "revenue growth",
        project_id=PROJECT_ID,
        top_k=8,
        similarity_threshold=0.75,
    )

    client.rpc.assert_called_once()

    args = client.rpc.call_args

    assert args.args[0] == "match_document_chunks"

    payload = args.args[1]

    assert payload["filter_project_id"] == str(PROJECT_ID)
    assert payload["match_count"] == 8
    assert payload["match_threshold"] == 0.75


def test_vector_search_embeds_query() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    retriever.search(
        "revenue growth",
        project_id=PROJECT_ID,
    )

    embedding_service.embed_text.assert_called_once_with(
        "revenue growth"
    )


def test_empty_query_is_rejected() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        retriever.search(
            "   ",
            project_id=PROJECT_ID,
        )

    client.rpc.assert_not_called()
    embedding_service.embed_text.assert_not_called()


def test_invalid_top_k_is_rejected() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            top_k=0,
        )

    with pytest.raises(
        ValueError,
        match="top_k",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            top_k=101,
        )

    client.rpc.assert_not_called()


def test_invalid_similarity_threshold_is_rejected() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    with pytest.raises(
        ValueError,
        match="similarity_threshold",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            similarity_threshold=-0.1,
        )

    with pytest.raises(
        ValueError,
        match="similarity_threshold",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
            similarity_threshold=1.1,
        )

    client.rpc.assert_not_called()


def test_wrong_query_embedding_dimension_is_rejected() -> None:
    client = create_supabase_client()

    embedding_service = Mock()

    embedding_service.embed_text.return_value = Mock(
        text="revenue",
        embedding=[0.1] * 1536,
        dimension=1536,
    )

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected dimension",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
        )

    client.rpc.assert_not_called()


def test_no_results_returns_empty_response() -> None:
    client = Mock()

    response = Mock()
    response.data = []

    client.rpc.return_value.execute.return_value = response

    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    result = retriever.search(
        "revenue",
        project_id=PROJECT_ID,
    )

    assert result.result_count == 0
    assert result.results == []
def test_invalid_similarity_score_is_rejected() -> None:
    client = Mock()

    response = Mock()
    response.data = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "document_id": (
                "22222222-2222-2222-2222-222222222222"
            ),
            "chunk_index": 0,
            "content": "Revenue increased.",
            "metadata": {},
            "similarity": 1.5,
        }
    ]

    client.rpc.return_value.execute.return_value = response

    embedding_service = create_embedding_service()

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    with pytest.raises(
        RuntimeError,
        match="invalid similarity",
    ):
        retriever.search(
            "revenue",
            project_id=PROJECT_ID,
        )
def test_vector_search_passes_metadata_filters() -> None:
    filters = RetrievalFilters(
        company="Example Corp",
        document_type="annual_report",
        publication_date_from=date(2024, 1, 1),
        publication_date_to=date(2025, 12, 31),
    )

    response = Mock()
    response.data = [
        {
            "id": "chunk-1",
            "document_id": "doc-1",
            "chunk_index": 0,
            "content": "Revenue increased.",
            "metadata": {},
            "similarity": 0.91,
        }
    ]

    client = Mock()
    client.rpc.return_value.execute.return_value = response

    embedding_service = Mock()
    embedding_service.embed_text.return_value.dimension = EXPECTED_DIMENSION
    embedding_service.embed_text.return_value.embedding = [
        0.1
    ] * EXPECTED_DIMENSION

    retriever = VectorRetriever(
        client=client,
        embedding_service=embedding_service,
    )

    retriever.search(
        "revenue",
        project_id=PROJECT_ID,
        filters=filters,
    )

    client.rpc.assert_called_once_with(
        "match_document_chunks",
        {
            "query_embedding": (
                "["
                + ",".join(["0.1"] * EXPECTED_DIMENSION)
                + "]"
            ),
            "match_count": 8,
            "match_threshold": 0.0,
            "filter_project_id": str(PROJECT_ID),
            "filter_company": "Example Corp",
            "filter_document_type": "annual_report",
            "filter_publication_date_from": "2024-01-01",
            "filter_publication_date_to": "2025-12-31",
        },
    )
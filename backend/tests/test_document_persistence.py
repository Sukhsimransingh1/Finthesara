from __future__ import annotations

from datetime import date
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from app.retrieval.embeddings import EXPECTED_DIMENSION
from app.schemas.ingestion import (
    DocumentMetadata,
    IngestedChunk,
    IngestedPage,
    IngestionResult,
)
from app.services.document_persistence import (
    DocumentPersistenceService,
)

PROJECT_ID = UUID(
    "bc8d4f9e-15d5-44f9-a896-c131421d8d4a"
)


def create_ingestion_result() -> IngestionResult:
    return IngestionResult(
        metadata=DocumentMetadata(
            filename="apple_2025-10-31_10k.pdf",
            file_path="data/apple_2025-10-31_10k.pdf",
            document_type="10-K",
            company="Apple",
            publication_date=date(
                2025,
                10,
                31,
            ),
            source_url="https://example.com/report.pdf",
        ),
        pages=[
            IngestedPage(
                page_number=1,
                text="Revenue increased by 14.2%.",
            ),
            IngestedPage(
                page_number=2,
                text="Operating margin was 18.7%.",
            ),
        ],
        chunks=[
            IngestedChunk(
                chunk_index=0,
                text="Revenue increased by 14.2%.",
                page_number=1,
                start_char=0,
                end_char=29,
            ),
            IngestedChunk(
                chunk_index=1,
                text="Operating margin was 18.7%.",
                page_number=2,
                start_char=0,
                end_char=29,
            ),
        ],
    )


def create_embedding_service() -> Mock:
    service = Mock()

    service.embed_documents.return_value = Mock(
        embeddings=[
            [0.1] * EXPECTED_DIMENSION,
            [0.2] * EXPECTED_DIMENSION,
        ],
        dimension=EXPECTED_DIMENSION,
    )

    return service


def create_supabase_client() -> Mock:
    client = Mock()

    document_response = Mock()
    document_response.data = [
        {
            "id": str(uuid4()),
            "project_id": str(PROJECT_ID),
            "title": "apple_2025-10-31_10k.pdf",
            "company": "Apple",
            "document_type": "10-K",
            "publication_date": "2025-10-31",
            "source_url": "https://example.com/report.pdf",
            "status": "ready",
        }
    ]

    chunk_response = Mock()
    chunk_response.data = [
        {
            "id": str(uuid4()),
            "document_id": document_response.data[0]["id"],
            "chunk_index": 0,
            "content": "Revenue increased by 14.2%.",
            "metadata": {
                "page_number": 1,
                "start_char": 0,
                "end_char": 29,
            },
        },
        {
            "id": str(uuid4()),
            "document_id": document_response.data[0]["id"],
            "chunk_index": 1,
            "content": "Operating margin was 18.7%.",
            "metadata": {
                "page_number": 2,
                "start_char": 0,
                "end_char": 29,
            },
        },
    ]

    document_table = Mock()
    document_table.insert.return_value.execute.return_value = (
        document_response
    )

    chunk_table = Mock()
    chunk_table.insert.return_value.execute.return_value = (
        chunk_response
    )

    client.table.side_effect = (
        lambda table_name: (
            document_table
            if table_name == "documents"
            else chunk_table
        )
    )

    return client


def test_persistence_generates_embeddings_before_db_insert() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    service = DocumentPersistenceService(
        client=client,
        embedding_service=embedding_service,
    )

    result = create_ingestion_result()

    service.persist(
        result,
        project_id=PROJECT_ID,
    )

    embedding_service.embed_documents.assert_called_once_with(
        [
            "Revenue increased by 14.2%.",
            "Operating margin was 18.7%.",
        ]
    )

    client.table.assert_any_call("documents")
    client.table.assert_any_call("document_chunks")


def test_persistence_returns_document_and_chunks() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    service = DocumentPersistenceService(
        client=client,
        embedding_service=embedding_service,
    )

    result = create_ingestion_result()

    persisted_document, persisted_chunks = service.persist(
        result,
        project_id=PROJECT_ID,
    )

    assert persisted_document.title == (
        "apple_2025-10-31_10k.pdf"
    )

    assert persisted_document.status == "ready"

    assert len(persisted_chunks) == 2

    assert persisted_chunks[0].chunk_index == 0
    assert persisted_chunks[1].chunk_index == 1


def test_embedding_failure_prevents_database_write() -> None:
    client = create_supabase_client()

    embedding_service = Mock()
    embedding_service.embed_documents.side_effect = RuntimeError(
        "Embedding model unavailable."
    )

    service = DocumentPersistenceService(
        client=client,
        embedding_service=embedding_service,
    )

    result = create_ingestion_result()

    with pytest.raises(
        RuntimeError,
        match="Embedding model unavailable",
    ):
        service.persist(
            result,
            project_id=PROJECT_ID,
        )

    client.table.assert_not_called()


def test_empty_chunks_are_rejected() -> None:
    client = create_supabase_client()
    embedding_service = create_embedding_service()

    service = DocumentPersistenceService(
        client=client,
        embedding_service=embedding_service,
    )

    result = create_ingestion_result()
    result.chunks = []

    with pytest.raises(
        ValueError,
        match="without chunks",
    ):
        service.persist(
            result,
            project_id=PROJECT_ID,
        )

    client.table.assert_not_called()
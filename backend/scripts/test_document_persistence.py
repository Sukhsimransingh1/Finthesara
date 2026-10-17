from __future__ import annotations

import sys
from datetime import date
from uuid import UUID

from app.schemas.ingestion import (
    DocumentMetadata,
    IngestedChunk,
    IngestedPage,
    IngestionResult,
)
from app.services.document_persistence import DocumentPersistenceService


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python scripts/test_document_persistence.py <project_uuid>"
        )

    project_id = UUID(sys.argv[1])

    result = IngestionResult(
        metadata=DocumentMetadata(
            filename="integration_test_2025-10-31_10k.pdf",
            file_path="data/integration_test_2025-10-31_10k.pdf",
            document_type="10-K",
            company="Integration Test Corp",
            publication_date=date(2025, 10, 31),
            source_url="https://example.com/integration-test.pdf",
        ),
        pages=[
            IngestedPage(
                page_number=1,
                text="Revenue increased by 14.2% during the fiscal year.",
            ),
            IngestedPage(
                page_number=2,
                text="Operating margin was 18.7% during the fiscal year.",
            ),
        ],
        chunks=[
            IngestedChunk(
                chunk_index=0,
                text="Revenue increased by 14.2% during the fiscal year.",
                page_number=1,
                start_char=0,
                end_char=51,
            ),
            IngestedChunk(
                chunk_index=1,
                text="Operating margin was 18.7% during the fiscal year.",
                page_number=2,
                start_char=0,
                end_char=51,
            ),
        ],
    )

    service = DocumentPersistenceService()

    document, chunks = service.persist(
        result,
        project_id=project_id,
    )

    print("\nPersistence successful!")
    print(f"Document ID : {document.id}")
    print(f"Project ID  : {document.project_id}")
    print(f"Title       : {document.title}")
    print(f"Company     : {document.company}")
    print(f"Status      : {document.status}")
    print(f"Chunks      : {len(chunks)}")

    for chunk in chunks:
        print(
            f"  Chunk {chunk.chunk_index}: "
            f"page={chunk.page_number}, "
            f"id={chunk.id}"
        )


if __name__ == "__main__":
    main()
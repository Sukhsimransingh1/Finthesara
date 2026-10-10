
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from app.api.auth import get_current_user_id
from app.services.document_persistence import (
    DocumentPersistenceService,
)
from app.services.document_service import DocumentIngestionService
from app.services.research_repository import ResearchRepository

router = APIRouter(prefix="/documents", tags=["documents"])

CurrentUser = Annotated[
    UUID,
    Depends(get_current_user_id),
]

MAX_PDF_BYTES = 20 * 1024 * 1024


@router.post("/upload", status_code=201)
async def upload_document(
    user_id: CurrentUser,
    project_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
    document_type: Annotated[str, Form()] = "unknown",
    company: Annotated[str | None, Form()] = None,
) -> dict[str, object]:
    """Parse and index an uploaded PDF into the project's RAG corpus."""
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=415,
            detail="Only PDF files are supported.",
        )

    try:
        ResearchRepository().assert_project_owner(
            project_id,
            user_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Project storage is unavailable.",
        ) from exc

    contents = await file.read(MAX_PDF_BYTES + 1)

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded PDF is empty.",
        )

    if len(contents) > MAX_PDF_BYTES:
        raise HTTPException(
            status_code=413,
            detail="PDF exceeds the 20 MB upload limit.",
        )

    if not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=415,
            detail="The uploaded file is not a valid PDF.",
        )

    temp_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            delete=False,
        ) as temporary:
            temporary.write(contents)
            temp_path = Path(temporary.name)

        ingestion = DocumentIngestionService().ingest(
            temp_path,
            document_type=document_type.strip() or "unknown",
            company=(
                company.strip()
                if company and company.strip()
                else None
            ),
        )

        # Keep the client's filename, not the temporary path.
        ingestion.metadata.filename = Path(file.filename).name

        # The current implementation indexes the PDF but does not
        # retain the original bytes in Supabase Storage.
        ingestion.metadata.file_path = ""

        document, chunks = DocumentPersistenceService().persist(
            ingestion,
            project_id=project_id,
        )

        return {
            "document": document.model_dump(mode="json"),
            "chunk_count": len(chunks),
            "message": "PDF parsed and indexed for retrieval.",
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Document ingestion failed.",
        ) from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

        await file.close()

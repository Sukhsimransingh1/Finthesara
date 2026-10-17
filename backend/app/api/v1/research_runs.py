
from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user_id
from app.services.research_repository import ResearchRepository

router = APIRouter(
    prefix="/research-runs",
    tags=["research-runs"],
)

CurrentUser = Annotated[UUID, Depends(get_current_user_id)]


def _repository() -> ResearchRepository:
    return ResearchRepository()


@router.get("")
def list_research_runs(
    project_id: UUID,
    user_id: CurrentUser,
    limit: int = Query(default=25, ge=1, le=100),
) -> dict[str, list[dict[str, Any]]]:
    try:
        items = _repository().list_runs(
            project_id=project_id,
            user_id=user_id,
            limit=limit,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Research storage is unavailable.",
        ) from exc

    return {"items": items}


@router.get("/{run_id}")
def get_research_run(
    run_id: UUID,
    user_id: CurrentUser,
) -> dict[str, Any]:
    try:
        item = _repository().get_run(
            run_id=run_id,
            user_id=user_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Research storage is unavailable.",
        ) from exc

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found.",
        )

    return item

@router.delete("/{run_id}")
def delete_research_run(
    run_id: UUID,
    user_id: CurrentUser,
) -> dict[str, str]:
    try:
        deleted = _repository().delete_run(
            run_id=run_id,
            user_id=user_id,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail="Research run not found or access denied.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Research storage is unavailable.",
        ) from exc

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Research run not found.",
        )

    return {"message": "Research run deleted successfully."}

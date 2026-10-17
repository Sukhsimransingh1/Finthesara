
"""Read persisted evaluation runs for the configured local user."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user_id
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

CurrentUser = Annotated[UUID, Depends(get_current_user_id)]


@router.get("")
def list_evaluations(
    user_id: CurrentUser,
    limit: int = Query(default=50, ge=1, le=100),
) -> dict[str, object]:
    """Return saved evaluation runs belonging to the local user."""
    try:
        client = get_supabase_client()

        response = (
            client.table("evaluation_runs")
            .select(
                "id,evaluation_dataset_id,initiated_by,status,"
                "configuration,results,created_at,completed_at,"
                "evaluation_datasets(name,description,project_id)"
            )
            .eq("initiated_by", str(user_id))
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        items = response.data or []

        return {
            "items": items,
            "count": len(items),
            "message": (
                "Saved evaluation runs loaded."
                if items
                else "No saved evaluation runs were found for this user."
            ),
        }

    except Exception as exc:
        logger.exception("Could not load saved evaluation runs.")
        raise HTTPException(
            status_code=503,
            detail=(
                "Evaluation records are temporarily unavailable. "
                "Check the Supabase connection and evaluation_runs schema."
            ),
        ) from exc

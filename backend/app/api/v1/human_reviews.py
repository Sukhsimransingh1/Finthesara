
from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from postgrest.types import JSON
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import get_current_user_id
from app.db.supabase_client import get_supabase_client
from app.services.research_repository import ResearchRepository

router = APIRouter(
    prefix="/human-reviews",
    tags=["human-reviews"],
)

CurrentUser = Annotated[
    UUID,
    Depends(get_current_user_id),
]


class ReviewRequest(BaseModel):
    """Input schema for a human review decision."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal[
        "approve",
        "reject",
        "request_research",
    ]
    comment: str | None = Field(
        default=None,
        max_length=5000,
    )


@router.post("/{run_id}", status_code=201)
def submit_review(
    run_id: UUID,
    request: ReviewRequest,
    user_id: CurrentUser,
) -> dict[str, object]:
    """Record a review for a research run owned by the user."""
    client = get_supabase_client()

    try:
        run_response = (
            client.table("research_runs")
            .select("id,project_id,status,metadata")
            .eq("id", str(run_id))
            .limit(1)
            .execute()
        )

        rows = run_response.data

        if not isinstance(rows, list) or not rows:
            raise HTTPException(
                status_code=404,
                detail="Research run not found.",
            )

        run = rows[0]

        if not isinstance(run, Mapping):
            raise HTTPException(
                status_code=500,
                detail="Invalid research-run record.",
            )

        raw_project_id = run.get("project_id")
        raw_status = run.get("status")
        raw_metadata = run.get("metadata")

        if not isinstance(raw_project_id, str):
            raise HTTPException(
                status_code=500,
                detail="Research run has no valid project ID.",
            )

        if not isinstance(raw_status, str):
            raise HTTPException(
                status_code=500,
                detail="Research run has no valid status.",
            )

        project_id = UUID(raw_project_id)

        ResearchRepository(client).assert_project_owner(
            project_id,
            user_id,
        )

        if raw_status not in {"awaiting_review", "completed"}:
            raise HTTPException(
                status_code=409,
                detail="This research run is not awaiting review.",
            )

        # Preserve existing report and workflow metadata.
        metadata: dict[str, JSON] = {}

        if isinstance(raw_metadata, Mapping):
            metadata.update(raw_metadata)

        comment = (
            request.comment.strip()
            if request.comment and request.comment.strip()
            else None
        )

        review_record: dict[str, JSON] = {
            "decision": request.decision,
            "reviewer_id": str(user_id),
            "comment": comment,
        }

        review_response = (
            client.table("human_reviews")
            .insert(
                {
                    "research_run_id": str(run_id),
                    "reviewer_id": str(user_id),
                    "status": "completed",
                    "decision": request.decision,
                    "comment": comment,
                }
            )
            .execute()
        )

        review_rows = review_response.data

        if not isinstance(review_rows, list) or not review_rows:
            raise RuntimeError(
                "Review record was not returned after insertion."
            )

        review_row = review_rows[0]

        if not isinstance(review_row, Mapping):
            raise RuntimeError(
                "Invalid review record returned by database."
            )

        metadata["latest_review"] = review_record

        next_status = {
            "approve": "completed",
            "reject": "failed",
            "request_research": "awaiting_review",
        }[request.decision]

        updated_response = (
            client.table("research_runs")
            .update(
                {
                    "status": next_status,
                    "metadata": metadata,
                }
            )
            .eq("id", str(run_id))
            .eq("project_id", str(project_id))
            .select("id,status")
            .execute()
        )

        updated_rows = updated_response.data

        if not isinstance(updated_rows, list) or not updated_rows:
            raise RuntimeError(
                "Research run status could not be updated."
            )

        return {
            "review": dict(review_row),
            "research_run_id": str(run_id),
            "status": next_status,
            "decision": request.decision,
        }

    except HTTPException:
        raise

    except PermissionError as exc:
        raise HTTPException(
            status_code=404,
            detail="Research run not found or access denied.",
        ) from exc

    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Research run contains invalid data.",
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Could not save the review.",
        ) from exc

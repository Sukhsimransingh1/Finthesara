
"""Project management endpoints for the configured local user."""

from __future__ import annotations

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.auth import get_current_user_id
from app.db.supabase_client import get_supabase_client
from app.services.research_repository import ResearchRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["projects"])

CurrentUser = Annotated[UUID, Depends(get_current_user_id)]


class ProjectCreate(BaseModel):
    """Validated project creation payload."""

    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Project name cannot be empty.")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class ProjectResponse(BaseModel):
    """Public project fields returned to the frontend."""

    model_config = ConfigDict(extra="ignore")

    id: UUID
    owner_id: UUID
    name: str
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _rows(response: Any) -> list[dict[str, Any]]:
    data = getattr(response, "data", None)
    if not isinstance(data, list):
        return []
    return [row for row in data if isinstance(row, dict)]


def _ensure_profile(client: Any, user_id: UUID) -> None:
    """Create the local user's profile only when it does not exist."""

    existing = (
        client.table("profiles")
        .select("id")
        .eq("id", str(user_id))
        .limit(1)
        .execute()
    )

    if _rows(existing):
        return

    client.table("profiles").insert({"id": str(user_id)}).execute()


@router.get("", response_model=list[ProjectResponse])
def list_projects(user_id: CurrentUser) -> list[dict[str, Any]]:
    """List projects belonging to the configured local user."""

    try:
        client = get_supabase_client()
        response = (
            client.table("projects")
            .select("id,owner_id,name,description,created_at,updated_at")
            .eq("owner_id", str(user_id))
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )
        return _rows(response)
    except Exception as exc:
        logger.exception("Failed to list projects for local user.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Projects are temporarily unavailable.",
        ) from exc


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    user_id: CurrentUser,
) -> dict[str, Any]:
    """Create a project owned by the configured local user."""

    try:
        client = get_supabase_client()
        _ensure_profile(client, user_id)

        response = (
            client.table("projects")
            .insert(
                {
                    "owner_id": str(user_id),
                    "name": payload.name,
                    "description": payload.description,
                }
            )
            .select(
                "id,owner_id,name,description,created_at,updated_at"
            )
            .execute()
        )

        rows = _rows(response)
        if not rows:
            raise RuntimeError("Supabase returned no project row.")

        return rows[0]

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create project.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Could not create the project. Check that the configured "
                "local user has a valid profiles row and that the database "
                "schema is up to date."
            ),
        ) from exc


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    user_id: CurrentUser,
) -> dict[str, Any]:
    """Get one project after verifying ownership."""

    try:
        ResearchRepository().assert_project_owner(project_id, user_id)

        client = get_supabase_client()
        response = (
            client.table("projects")
            .select("id,owner_id,name,description,created_at,updated_at")
            .eq("id", str(project_id))
            .eq("owner_id", str(user_id))
            .limit(1)
            .execute()
        )
        rows = _rows(response)

        if not rows:
            raise HTTPException(status_code=404, detail="Project not found.")

        return rows[0]

    except PermissionError as exc:
        raise HTTPException(status_code=404, detail="Project not found.") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve project.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project details are temporarily unavailable.",
        ) from exc

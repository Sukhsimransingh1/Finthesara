
"""Local single-user identity for development without login."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from app.config import get_settings


def get_current_user_id() -> UUID:
    """Return the configured local owner ID without requiring a token."""
    raw_user_id = get_settings().local_user_id.strip()

    if not raw_user_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Local mode is not configured. Set LOCAL_USER_ID "
                "in the backend .env file."
            ),
        )

    try:
        return UUID(raw_user_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LOCAL_USER_ID must be a valid UUID.",
        ) from exc

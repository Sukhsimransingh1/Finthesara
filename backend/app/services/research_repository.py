
from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client

from app.db.supabase_client import get_supabase_client


class ResearchRepository:
    """Persist research runs and enforce project ownership."""

    def __init__(self, client: Client | None = None) -> None:
        self.client = client or get_supabase_client()

    @staticmethod
    def _first_row(response: Any, message: str) -> dict[str, Any]:
        rows = getattr(response, "data", None)

        if (
            not isinstance(rows, list)
            or not rows
            or not isinstance(rows[0], dict)
        ):
            raise RuntimeError(message)

        return rows[0]

    def assert_project_owner(
        self,
        project_id: UUID,
        user_id: UUID,
    ) -> None:
        response = (
            self.client.table("projects")
            .select("id,owner_id")
            .eq("id", str(project_id))
            .eq("owner_id", str(user_id))
            .limit(1)
            .execute()
        )

        if not getattr(response, "data", None):
            # Avoid revealing whether another user's project exists.
            raise PermissionError(
                "Project not found or access denied."
            )

    def create_run(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        question: str,
        run_id: UUID | None = None,
    ) -> UUID:
        self.assert_project_owner(project_id, user_id)

        payload: dict[str, Any] = {
            "project_id": str(project_id),
            "question": question,
            "status": "queued",
            "metadata": {"requested_by": str(user_id)},
        }

        if run_id is not None:
            payload["id"] = str(run_id)

        response = (
            self.client.table("research_runs")
            .insert(payload)
            .execute()
        )

        row = self._first_row(
            response,
            "Research run could not be created.",
        )
        return UUID(str(row["id"]))

    def finish_run(
        self,
        *,
        run_id: UUID,
        project_id: UUID,
        user_id: UUID,
        state: dict[str, Any],
        status: str,
    ) -> dict[str, Any]:
        self.assert_project_owner(project_id, user_id)

        allowed_statuses = {
            "queued",
            "planning",
            "researching",
            "verifying",
            "awaiting_review",
            "completed",
            "failed",
        }

        if status not in allowed_statuses:
            status = "failed"

        metadata = {
            "requested_by": str(user_id),
            "final_report": state.get("final_report"),
            "draft_report": state.get("draft_report"),
            "human_review_required": bool(
                state.get("human_review_required", False)
            ),
            "state": state,
        }

        response = (
            self.client.table("research_runs")
            .update({
                "status": status,
                "metadata": metadata,
            })
            .eq("id", str(run_id))
            .eq("project_id", str(project_id))
            .select(
                "id,project_id,question,status,metadata,"
                "created_at,updated_at"
            )
            .execute()
        )

        return self._first_row(
            response,
            "Research run could not be updated.",
        )

    def get_run(
        self,
        *,
        run_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any] | None:
        response = (
            self.client.table("research_runs")
            .select(
                "id,project_id,question,status,metadata,"
                "created_at,updated_at"
            )
            .eq("id", str(run_id))
            .limit(1)
            .execute()
        )

        rows = getattr(response, "data", None)

        if not isinstance(rows, list) or not rows:
            return None

        row = rows[0]

        if not isinstance(row, dict):
            return None

        project_id = UUID(str(row["project_id"]))
        self.assert_project_owner(project_id, user_id)

        return row

    def list_runs(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        self.assert_project_owner(project_id, user_id)

        response = (
            self.client.table("research_runs")
            .select(
                "id,project_id,question,status,metadata,"
                "created_at,updated_at"
            )
            .eq("project_id", str(project_id))
            .order("created_at", desc=True)
            .limit(max(1, min(limit, 100)))
            .execute()
        )

        rows = getattr(response, "data", None)

        if not isinstance(rows, list):
            return []

        return [
            row for row in rows
            if isinstance(row, dict)
        ]

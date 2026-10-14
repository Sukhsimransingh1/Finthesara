
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.auth import get_current_user_id
from app.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchStreamEvent,
)
from app.services.research_runner import ResearchRunner
from app.tools.sec_data_source import SECFinancialDataSource
from app.services.research_repository import ResearchRepository

logger = logging.getLogger(__name__)
CurrentUser = Annotated[UUID, Depends(get_current_user_id)]
router = APIRouter(
    prefix="/api/v1/research",
    tags=["research"],
)


def _build_runner() -> ResearchRunner:
    """Build the production research runner with SEC financial data."""
    return ResearchRunner(
        data_source=SECFinancialDataSource(),
        production=True,
    )


def _serialize(value: Any) -> Any:
    """Convert Pydantic/state values into JSON-serializable data."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_serialize(item) for item in value]

    if isinstance(value, tuple):
        return [_serialize(item) for item in value]

    return value


@router.post("", response_model=ResearchResponse)
def run_research(
    request: ResearchRequest,
    user_id: CurrentUser,
) -> ResearchResponse:
    """Execute research once and persist the run for the authenticated owner."""
    repository = ResearchRepository()

    try:
        requested_run_id = UUID(request.run_id) if request.run_id else uuid4()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="run_id must be a valid UUID when supplied.",
        ) from exc

    try:
        run_id = repository.create_run(
            project_id=request.project_id,
            user_id=user_id,
            question=request.question,
            run_id=requested_run_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Research storage is unavailable.",
        ) from exc

    runner = _build_runner()

    try:
        result = runner.run(
            question=request.question,
            project_id=request.project_id,
            user_id=str(user_id),
            run_id=str(run_id),
        )
        state = _serialize(result)
        raw_status = str(result.get("status") or "completed").lower()

        if (
            bool(result.get("human_review_required", False))
            or raw_status
            in {
                "awaiting_review",
                "awaiting_human_review",
                "pending_review",
            }
        ):
            persisted_status = "awaiting_review"
        elif raw_status in {"failed", "error"} or result.get("errors"):
            persisted_status = "failed"
        else:
            persisted_status = "completed"

        repository.finish_run(
            run_id=run_id,
            project_id=request.project_id,
            user_id=user_id,
            state=state,
            status=persisted_status,
        )

    except ValueError as exc:
        failure_state = {
            "run_id": str(run_id),
            "original_question": request.question,
            "errors": [str(exc)],
            "status": "failed",
        }

        try:
            repository.finish_run(
                run_id=run_id,
                project_id=request.project_id,
                user_id=user_id,
                state=failure_state,
                status="failed",
            )
        except Exception:
            logger.exception(
                "Could not persist failed research run %s",
                run_id,
            )

        raise HTTPException(status_code=400, detail=str(exc)) from exc

    except Exception as exc:
        logger.exception("Research workflow failed for run %s", run_id)

        failure_state = {
            "run_id": str(run_id),
            "original_question": request.question,
            "errors": ["Research workflow failed."],
            "status": "failed",
        }

        try:
            repository.finish_run(
                run_id=run_id,
                project_id=request.project_id,
                user_id=user_id,
                state=failure_state,
                status="failed",
            )
        except Exception:
            logger.exception(
                "Could not persist failed research run %s",
                run_id,
            )

        raise HTTPException(
            status_code=500,
            detail="Research workflow failed.",
        ) from exc

    return ResearchResponse(
        run_id=str(run_id),
        status=persisted_status,
        final_report=result.get("final_report"),
        draft_report=result.get("draft_report"),
        human_review_required=bool(
            result.get("human_review_required", False)
        ),
        state=state,
    )


def _format_sse_event(
    *,
    event: str,
    node: str | None = None,
    data: Any = None,
) -> str:
    """Format a server-sent event."""
    payload = ResearchStreamEvent(
        event=event,
        node=node,
        data=_serialize(data) if data is not None else {},
    )

    return (
        f"event: {event}\n"
        f"data: {json.dumps(payload.model_dump(mode='json'))}\n\n"
    )


async def _stream_research(
    request: ResearchRequest,
) -> AsyncIterator[str]:
    """Stream LangGraph execution updates as SSE events."""
    runner = _build_runner()

    try:
        yield _format_sse_event(
            event="research_started",
            data={
                "question": request.question,
                "project_id": str(request.project_id),
            },
        )

        for update in runner.stream(
            question=request.question,
            project_id=request.project_id,
            user_id=str(request.user_id) if request.user_id else None,
            run_id=request.run_id,
        ):
            if not isinstance(update, dict):
                continue

            for node, node_state in update.items():
                yield _format_sse_event(
                    event="node_update",
                    node=str(node),
                    data=node_state,
                )

        yield _format_sse_event(
            event="research_completed",
            data={
                "run_id": request.run_id or "",
            },
        )

    except ValueError as exc:
        yield _format_sse_event(
            event="research_error",
            data={"error": str(exc)},
        )

    except Exception as exc:
        logger.exception("Research workflow failed during streaming")
        yield _format_sse_event(
            event="research_error",
            data={
                "error": "Research workflow failed.",
                "error_type": type(exc).__name__,
            },
        )


@router.post("/stream")
async def stream_research(
    request: ResearchRequest,
) -> StreamingResponse:
    """Stream research workflow events using Server-Sent Events."""
    return StreamingResponse(
        _stream_research(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
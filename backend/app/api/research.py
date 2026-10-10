from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.api.schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchStreamEvent,
)
from app.services.research_runner import ResearchRunner
from app.tools.mock_data_source import InMemoryFinancialDataSource

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/research",
    tags=["research"],
)


def _build_runner() -> ResearchRunner:
    """Build the production research runner."""
    data_source = InMemoryFinancialDataSource(metrics=[])
    return ResearchRunner(
        data_source=data_source,
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
def run_research(request: ResearchRequest) -> ResearchResponse:
    """Execute a financial research workflow."""
    runner = _build_runner()

    try:
        result = runner.run(
            question=request.question,
            project_id=request.project_id,
            user_id=str(request.user_id) if request.user_id else None,
            run_id=request.run_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Research workflow failed.",
        ) from exc

    return ResearchResponse(
        run_id=str(result.get("run_id") or request.run_id or ""),
        status=str(result.get("status") or "unknown"),
        final_report=result.get("final_report"),
        draft_report=result.get("draft_report"),
        human_review_required=bool(
            result.get("human_review_required", False)
        ),
        state=_serialize(result),
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

    return f"event: {event}\ndata: {json.dumps(payload.model_dump(mode='json'))}\n\n"


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
            data={
                "error": str(exc),
            },
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
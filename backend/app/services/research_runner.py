from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from uuid import UUID, uuid4

from app.agents.state import ResearchState
from app.graph.workflow import (
    build_production_research_graph,
    build_research_graph,
)
from app.tools.data_source import FinancialDataSource


class ResearchRunner:
    """Application service responsible for executing the research graph.

    The runner validates user input, builds the initial LangGraph state,
    and exposes both synchronous and streaming execution.
    """

    def __init__(
        self,
        *,
        data_source: FinancialDataSource,
        production: bool = False,
    ) -> None:
        self.data_source = data_source
        self.production = production

    @staticmethod
    def _normalize_project_id(project_id: str | UUID) -> str:
        return str(project_id)

    @staticmethod
    def _build_initial_state(
        *,
        question: str,
        project_id: str,
        user_id: str | None = None,
        run_id: str | None = None,
    ) -> ResearchState:
        state: ResearchState = {
            "run_id": run_id or str(uuid4()),
            "user_id": user_id,
            "project_id": project_id,
            "original_question": question,
            "normalized_question": question,
            "companies": [],
            "time_range_start": None,
            "time_range_end": None,
            "research_plan": None,
            "agent_results": [],
            "financial_results": [],
            "research_output": None,
            "evidence": [],
            "claims": [],
            "calculations": [],
            "contradictions": [],
            "verification_result": None,
            "retry_count": 0,
            "max_retries": 2,
            "draft_report": None,
            "final_report": None,
            "human_review_required": False,
            "human_review": None,
            "errors": [],
            "status": "initialized",
        }
        return state

    def _build_graph(self) -> Any:
        """Build the appropriate research graph."""
        if self.production:
            return build_production_research_graph(
                data_source=self.data_source,
            )

        return build_research_graph(
            data_source=self.data_source,
        )

    def run(
        self,
        *,
        question: str,
        project_id: str | UUID,
        user_id: str | None = None,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute the research workflow synchronously."""
        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError("Research question cannot be empty.")

        normalized_project_id = self._normalize_project_id(project_id)

        state = self._build_initial_state(
            question=normalized_question,
            project_id=normalized_project_id,
            user_id=user_id,
            run_id=run_id,
        )

        graph = self._build_graph()
        result = graph.invoke(state)

        if not isinstance(result, dict):
            raise TypeError("Research graph returned an invalid state.")

        return dict(result)

    def stream(
        self,
        *,
        question: str,
        project_id: str | UUID,
        user_id: str | None = None,
        run_id: str | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Stream research workflow updates."""
        normalized_question = question.strip()

        if not normalized_question:
            raise ValueError("Research question cannot be empty.")

        normalized_project_id = self._normalize_project_id(project_id)

        state = self._build_initial_state(
            question=normalized_question,
            project_id=normalized_project_id,
            user_id=user_id,
            run_id=run_id,
        )

        graph = self._build_graph()

        for update in graph.stream(
            state,
            stream_mode="updates",
        ):
            if isinstance(update, dict):
                yield dict(update)

from __future__ import annotations

from datetime import date
from uuid import uuid4

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    PlannerAgentOutput,
    ResearchPlan,
    ResearchTask,
    ResearchTaskType,
)
from app.agents.state import ResearchState


class ResearchPlannerAgent:
    """
    Convert a research question into a structured execution plan.

    The planner determines downstream work but does not perform
    calculations or document retrieval.
    """

    name = "research_planner"

    def run(self, state: ResearchState) -> PlannerAgentOutput:
        question = state["original_question"].strip()

        if not question:
            raise ValueError("Research question cannot be empty.")

        initial_plan = self._build_initial_plan(question)

        # Use the last five completed calendar years as the default range.
        # For example, in 2026 this resolves to 2021-01-01 through 2025-12-31.
        today = date.today()
        latest_completed_year = today.year - 1
        start_date = date(latest_completed_year - 4, 1, 1)
        end_date = date(latest_completed_year, 12, 31)

        # Propagate the date range to the plan and every research task.
        plan = initial_plan.model_copy(
            update={
                "start_date": start_date,
                "end_date": end_date,
                "tasks": [
                    task.model_copy(
                        update={
                            "start_date": start_date,
                            "end_date": end_date,
                        }
                    )
                    for task in initial_plan.tasks
                ],
            }
        )

        # Preserve companies identified earlier in the workflow.
        existing_companies = list(state.get("companies", []))

        if existing_companies:
            plan = plan.model_copy(
                update={
                    "companies": existing_companies,
                }
            )

        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary="Created initial research plan.",
            data={
                "task_count": len(plan.tasks),
                "companies": plan.companies,
                "required_metrics": plan.required_metrics,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        )

        return PlannerAgentOutput(
            normalized_question=plan.normalized_question,
            research_plan=plan,
            companies=plan.companies,
            agent_results=[result],
            status="planned",
        )

    @staticmethod
    def _build_initial_plan(question: str) -> ResearchPlan:
        tasks = [
            ResearchTask(
                task_id=str(uuid4()),
                task_type=ResearchTaskType.FINANCIAL_ANALYSIS,
                description=(
                    "Identify and analyze the financial metrics required "
                    "to answer the research question."
                ),
                required_tools=[
                    "financial_data_query",
                    "period_comparison",
                    "financial_calculator",
                    "revenue_analysis",
                    "expense_trend_analysis",
                    "anomaly_detection",
                ],
                completion_criteria=[
                    "Required financial metrics are identified.",
                    "Relevant period comparisons are calculated.",
                    "Important anomalies are evaluated.",
                ],
            ),
            ResearchTask(
                task_id=str(uuid4()),
                task_type=ResearchTaskType.DOCUMENT_RESEARCH,
                description=(
                    "Retrieve supporting evidence from the project's "
                    "financial document corpus."
                ),
                required_tools=[
                    "document_search",
                ],
                required_evidence=[
                    "Relevant financial statements or filings.",
                    "Evidence supporting material claims.",
                ],
                completion_criteria=[
                    "Claims have supporting evidence.",
                    "Evidence is traceable to source documents.",
                ],
            ),
            ResearchTask(
                task_id=str(uuid4()),
                task_type=ResearchTaskType.EXTERNAL_RESEARCH,
                description=(
                    "Identify external sources required to resolve "
                    "information gaps."
                ),
                required_tools=[
                    "web_source_search",
                    "document_fetch",
                ],
                completion_criteria=[
                    "External claims have identifiable sources.",
                    "Unresolved information gaps are documented.",
                ],
            ),
        ]

        return ResearchPlan(
            normalized_question=question,
            tasks=tasks,
            completion_criteria=[
                "All major parts of the question are addressed.",
                "Financial calculations are reproducible.",
                "Important claims have supporting evidence.",
                "Uncertainty and contradictions are explicitly identified.",
            ],
        )

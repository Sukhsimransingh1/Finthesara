from __future__ import annotations

from datetime import date

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    PlannerAgentOutput,
    ResearchPlan,
    ResearchTask,
    ResearchTaskType,
)
from app.agents.state import ResearchState
from app.llm.prompts import PLANNER_SYSTEM_PROMPT
from app.llm.protocol import StructuredLLM
from app.llm.schemas import PlannerLLMOutput


class LLMResearchPlannerAgent:
    """Create a structured financial research plan using an LLM."""

    name = "llm_research_planner"

    def __init__(self, *, llm: StructuredLLM) -> None:
        self.llm = llm

    def run(self, state: ResearchState) -> PlannerAgentOutput:
        question = state["original_question"].strip()

        if not question:
            raise ValueError("Research question cannot be empty.")

        prompt = f"""
User research question:

{question}

Create a structured financial research plan.

Identify:
- companies/entities
- relevant financial metrics
- requested time period
- research tasks
- required evidence
- required tools
- completion criteria

Do not answer the research question.
Do not invent financial facts.
"""

        parsed, _ = self.llm.invoke_structured(
            system_prompt=PLANNER_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=PlannerLLMOutput,
        )

        plan_start = self._parse_date(parsed.start_date)
        plan_end = self._parse_date(parsed.end_date)

        if plan_start is not None and plan_end is not None:
            if plan_start > plan_end:
                raise ValueError(
                    "LLM returned a start date after the end date."
                )

        
        tasks: list[ResearchTask] = []

        for task in parsed.tasks:
            raw_task_type = task.task_type.strip().lower()

            # Synthesis is handled by a separate workflow node.
            if raw_task_type == "synthesis":
                continue

            try:
                task_type = ResearchTaskType(raw_task_type)
            except ValueError as exc:
                supported = ", ".join(
                    item.value for item in ResearchTaskType
                )
                raise ValueError(
                    "LLM returned unsupported research task type: "
                    f"{task.task_type}. Supported types: {supported}"
                ) from exc

            tasks.append(
                ResearchTask(
                    task_id=task.task_id,
                    task_type=task_type,
                    description=task.description,
                    company=task.company,
                    metric=task.metric,
                    start_date=plan_start,
                    end_date=plan_end,
                    required_evidence=task.required_evidence,
                    required_tools=task.required_tools,
                    completion_criteria=task.completion_criteria,
                )
            )

        plan = ResearchPlan(
            normalized_question=parsed.normalized_question,
            companies=parsed.companies,
            start_date=plan_start,
            end_date=plan_end,
            tasks=tasks,
            required_metrics=parsed.required_metrics,
            completion_criteria=parsed.completion_criteria,
        )

        result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary="LLM generated a structured research plan.",
            data={
                "task_count": len(tasks),
                "companies": plan.companies,
                "required_metrics": plan.required_metrics,
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
    def _parse_date(value: str | None) -> date | None:
        if value is None:
            return None

        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"LLM returned an invalid date: {value}"
            ) from exc
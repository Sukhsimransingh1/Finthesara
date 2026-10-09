from __future__ import annotations

from decimal import Decimal

from app.agents.financial_analyst import FinancialAnalystAgent
from app.agents.schemas import ResearchPlan, ResearchTask, ResearchTaskType
from app.agents.state import ResearchState
from app.tools.financial_analysis import FinancialAnalysisTools
from app.tools.schemas import (
    FinancialDataQuery,
    FinancialDataResult,
    FinancialMetric,
)


class FakeFinancialDataSource:
    def query(
        self,
        query: FinancialDataQuery,
    ) -> FinancialDataResult:
        periods = query.periods

        values = [
            FinancialMetric(
                company=query.company,
                metric=query.metric,
                period=period,
                value=(
                    Decimal("100")
                    if index == 0
                    else Decimal("120")
                ),
                currency="USD",
                unit="million",
                source_id=f"source-{index}",
            )
            for index, period in enumerate(periods)
        ]

        return FinancialDataResult(
            company=query.company,
            metric=query.metric,
            values=values,
            source_count=len(values),
        )


def make_state() -> ResearchState:
    plan = ResearchPlan(
        normalized_question="How did Example Corp revenue change?",
        companies=["Example Corp"],
        required_metrics=["revenue"],
        tasks=[
            ResearchTask(
                task_id="financial-task",
                task_type=ResearchTaskType.FINANCIAL_ANALYSIS,
                description="Analyze revenue.",
            )
        ],
    )

    return {
        "original_question": "How did Example Corp revenue change?",
        "normalized_question": "How did Example Corp revenue change?",
        "companies": ["Example Corp"],
        "time_range_start": "2024-01-01",
        "time_range_end": "2025-12-31",
        "research_plan": plan,
    }


def test_financial_analyst_uses_typed_tools() -> None:
    agent = FinancialAnalystAgent(
        data_source=FakeFinancialDataSource(),
        analysis_tools=FinancialAnalysisTools(),
    )

    result = agent.run(make_state())

    financial_results = result["financial_results"]

    assert isinstance(financial_results, list)
    assert len(financial_results) == 1

    company_result = financial_results[0]

    assert company_result["company"] == "Example Corp"
    assert company_result["findings"]


def test_financial_analyst_does_not_invent_company() -> None:
    state = make_state()

    state["companies"] = []

    plan = state.get("research_plan")
    assert plan is not None

    plan.companies = []

    agent = FinancialAnalystAgent(
        data_source=FakeFinancialDataSource(),
    )

    result = agent.run(state)

    agent_results = result["agent_results"]

    assert isinstance(agent_results, list)
    assert agent_results[0].status.value == "failed"
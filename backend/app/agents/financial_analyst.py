from __future__ import annotations

from datetime import date
from typing import Any

from app.agents.schemas import (
    AgentResult,
    AgentStatus,
    FinancialAnalystOutput,
    ResearchTaskType,
)
from app.agents.state import ResearchState
from app.tools.data_source import FinancialDataSource
from app.tools.financial_analysis import FinancialAnalysisTools
from app.tools.schemas import (
    ExpenseTrendInput,
    FinancialDataQuery,
    FinancialPeriod,
    MetricType,
    RevenueAnalysisInput,
)


class FinancialAnalystAgent:
    """Run deterministic financial analysis using typed financial tools."""

    name = "financial_analyst"

    def __init__(
        self,
        *,
        data_source: FinancialDataSource,
        analysis_tools: FinancialAnalysisTools | None = None,
    ) -> None:
        self.data_source = data_source
        self.analysis_tools = analysis_tools or FinancialAnalysisTools()

    def run(self, state: ResearchState) -> dict[str, object]:
        plan = state.get("research_plan")

        if plan is None:
            return {
                "financial_results": [],
                "calculations": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary=(
                            "Financial analysis could not start "
                            "without a research plan."
                        ),
                        errors=["research_plan is missing from research state."],
                    )
                ],
            }

        financial_tasks = [
            task
            for task in plan.tasks
            if task.task_type == ResearchTaskType.FINANCIAL_ANALYSIS
        ]

        if not financial_tasks:
            return {
                "financial_results": [],
                "calculations": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.COMPLETED,
                        summary="No financial analysis task was required.",
                    )
                ],
            }

        companies = plan.companies or self._infer_companies(state)

        if not companies:
            return {
                "financial_results": [],
                "calculations": [],
                "agent_results": [
                    AgentResult(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        summary=(
                            "No company could be identified "
                            "for financial analysis."
                        ),
                        errors=[
                            "No company was provided in the research state."
                        ],
                    )
                ],
            }

        financial_results: list[dict[str, object]] = []
        financial_evidence: list[dict[str, object]] = []
        calculations: list[dict[str, object]] = []

        for company in companies:
            result = self._analyze_company(
                company=company,
                state=state,
            )

            result_data = result.model_dump()
            financial_results.append(result_data)
            financial_evidence.extend(
                item
                for item in result_data.get("financial_evidence", [])
                if isinstance(item, dict)
            )
            calculations.extend(result.calculations)

        agent_result = AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            summary=(
                "Completed deterministic financial analysis "
                f"for {len(companies)} company(s)."
            ),
            data={
                "companies_analyzed": companies,
                "calculation_count": len(calculations),
            },
        )

        return {
            "financial_results": financial_results,
            "financial_evidence": financial_evidence,
            "calculations": calculations,
            "agent_results": [agent_result],
        }

    def _analyze_company(
        self,
        *,
        company: str,
        state: ResearchState,
    ) -> FinancialAnalystOutput:
        findings: list[str] = []
        calculations: list[dict[str, Any]] = []
        anomalies: list[str] = []
        source_ids: list[str] = []
        financial_evidence: list[dict[str, Any]] = []

        metrics = self._required_metrics(state)
        periods = self._periods_from_state(state)

        for metric in metrics:
            query = FinancialDataQuery(
                company=company,
                metric=metric,
                periods=periods,
            )

            data_result = self.data_source.query(query)

            if not data_result.values:
                continue

            values = data_result.values

            source_ids.extend(
                value.source_id
                for value in values
                if value.source_id is not None
            )
            
            for value in values:
                source = (
                    value.source_url
                    or value.source_id
                    or "source unavailable"
                )
                findings.append(
                    f"Reported {metric.value.replace('_', ' ')} for "
                    f"{company}: {value.value} {value.unit or ''}; "
                    f"period {value.period.label} "
                    f"({value.period.start_date} to "
                    f"{value.period.end_date}). "
                    f"Source: {source}"
                )
                if value.source_id and value.source_url:
                    financial_evidence.append(
                        {
                            "evidence_id": f"financial:{value.source_id}",
                            "evidence_type": "sec_xbrl_fact",
                            "company": value.company,
                            "metric": metric.value,
                            "value": str(value.value),
                            "unit": value.unit,
                            "currency": value.currency,
                            "period_label": value.period.label,
                            "period_start": value.period.start_date.isoformat(),
                            "period_end": value.period.end_date.isoformat(),
                            "source_id": value.source_id,
                            "source_url": value.source_url,
                            "statement": findings[-1],
                        }
                    )

            durations = [
                (value.period.end_date - value.period.start_date).days
                for value in values
            ]
            comparable_periods = (
                len(values) >= 2
                and max(durations) - min(durations) <= 35
            )

            if (
                metric == MetricType.REVENUE
                and comparable_periods
            ):
                revenue_result = self.analysis_tools.analyze_revenue(
                    RevenueAnalysisInput(
                        company=company,
                        periods=values,
                    )
                )

                calculations.extend(
                    item.model_dump()
                    for item in revenue_result.calculations
                )

                findings.append(
                    f"Revenue analysis for {company}: "
                    f"{revenue_result.trend} trend."
                )

            elif (
                metric == MetricType.OPERATING_EXPENSE
                and comparable_periods
            ):
                expense_result = self.analysis_tools.analyze_expense_trend(
                    ExpenseTrendInput(
                        company=company,
                        periods=values,
                    )
                )

                calculations.extend(
                    item.model_dump()
                    for item in expense_result.calculations
                )

                findings.append(
                    f"Operating expense analysis for {company}: "
                    f"{expense_result.trend} trend."
                )

                if expense_result.anomaly_detected:
                    anomalies.append(
                        f"Operating expense anomaly detected for {company}."
                    )

        return FinancialAnalystOutput(
            company=company,
            findings=findings,
            calculations=calculations,
            anomalies=anomalies,
            source_ids=source_ids,
            financial_evidence=financial_evidence,
        )

    @staticmethod
    def _required_metrics(
        state: ResearchState,
    ) -> list[MetricType]:
        plan = state.get("research_plan")

        if plan is None:
            return [
                MetricType.REVENUE,
                MetricType.OPERATING_EXPENSE,
            ]

        if plan.required_metrics:
            metrics: list[MetricType] = []

            for value in plan.required_metrics:
                try:
                    metrics.append(MetricType(value))
                except ValueError:
                    continue

            if metrics:
                return metrics

        return [
            MetricType.REVENUE,
            MetricType.OPERATING_EXPENSE,
        ]

    @staticmethod
    def _periods_from_state(
        state: ResearchState,
    ) -> list[FinancialPeriod]:
        start_value = state.get("time_range_start")
        end_value = state.get("time_range_end")

        if start_value is None or end_value is None:
            today = date.today()

            return [
                FinancialPeriod(
                    label=str(today.year),
                    start_date=date(today.year, 1, 1),
                    end_date=today,
                )
            ]

        start_date = date.fromisoformat(start_value)
        end_date = date.fromisoformat(end_value)

        if start_date > end_date:
            raise ValueError(
                "time_range_start cannot be after time_range_end."
            )

        total_days = (end_date - start_date).days + 1

        # Keep a single fiscal-year request intact (e.g. Apple's FY2024:
        # 2023-10-01 through 2024-09-30). Splitting it at Jan 1 can mix
        # a quarter with an annual fact.
        if 250 <= total_days <= 400:
            return [
                FinancialPeriod(
                    label=f"{start_date.year}-{end_date.year}",
                    start_date=start_date,
                    end_date=end_date,
                )
            ]

        periods: list[FinancialPeriod] = []

        for year in range(start_date.year, end_date.year + 1):
            period_start = max(
                start_date,
                date(year, 1, 1),
            )

            period_end = min(
                end_date,
                date(year, 12, 31),
            )

            if period_start <= period_end:
                periods.append(
                    FinancialPeriod(
                        label=str(year),
                        start_date=period_start,
                        end_date=period_end,
                    )
                )

        return periods

    @staticmethod
    def _infer_companies(
        state: ResearchState,
    ) -> list[str]:
        companies = state.get("companies", [])

        return list(companies)
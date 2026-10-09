from __future__ import annotations

from app.tools.schemas import (
    FinancialDataQuery,
    FinancialDataResult,
    FinancialMetric,
)


class InMemoryFinancialDataSource:
    """Small deterministic provider used for development and tests."""

    def __init__(
        self,
        metrics: list[FinancialMetric],
    ) -> None:
        self.metrics = metrics

    def query(
        self,
        request: FinancialDataQuery,
    ) -> FinancialDataResult:
        requested_periods = {
            (
                period.start_date,
                period.end_date,
            )
            for period in request.periods
        }

        values = [
            metric
            for metric in self.metrics
            if metric.company == request.company
            and metric.metric == request.metric
            and (
                metric.period.start_date,
                metric.period.end_date,
            ) in requested_periods
        ]

        return FinancialDataResult(
            company=request.company,
            metric=request.metric,
            values=values,
            source_count=sum(
                1
                for value in values
                if value.source_id is not None
            ),
        )
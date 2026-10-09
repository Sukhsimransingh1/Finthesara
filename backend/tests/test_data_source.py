from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.tools.mock_data_source import (
    InMemoryFinancialDataSource,
)
from app.tools.schemas import (
    FinancialDataQuery,
    FinancialMetric,
    FinancialPeriod,
    MetricType,
)


def test_in_memory_financial_data_source() -> None:
    period = FinancialPeriod(
        label="FY2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
    )

    metric = FinancialMetric(
        company="Example Corp",
        metric=MetricType.REVENUE,
        period=period,
        value=Decimal("1250"),
        currency="USD",
        unit="millions",
        source_id="source-1",
    )

    provider = InMemoryFinancialDataSource(
        metrics=[metric]
    )

    result = provider.query(
        FinancialDataQuery(
            company="Example Corp",
            metric=MetricType.REVENUE,
            periods=[period],
        )
    )

    assert result.company == "Example Corp"
    assert result.metric == MetricType.REVENUE
    assert len(result.values) == 1
    assert result.values[0].value == Decimal("1250")
    assert result.source_count == 1
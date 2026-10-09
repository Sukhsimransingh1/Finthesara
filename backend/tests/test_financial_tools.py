from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from app.tools.anomaly import FinancialAnomalyDetector
from app.tools.calculator import FinancialCalculator
from app.tools.financial_analysis import FinancialAnalysisTools
from app.tools.schemas import (
    AnomalyDetectionInput,
    CAGRCalculationInput,
    ExpenseTrendInput,
    FinancialMetric,
    FinancialPeriod,
    MarginCalculationInput,
    MetricType,
    PeriodComparisonInput,
    RevenueAnalysisInput,
)


def make_period(
    label: str,
    year: int,
) -> FinancialPeriod:
    return FinancialPeriod(
        label=label,
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
    )


def make_metric(
    company: str,
    value: str,
    year: int,
    metric: MetricType,
) -> FinancialMetric:
    return FinancialMetric(
        company=company,
        metric=metric,
        period=make_period(
            str(year),
            year,
        ),
        value=Decimal(value),
        currency="USD",
        unit="millions",
        source_id=f"source-{year}",
    )


def test_period_comparison() -> None:
    result = FinancialCalculator.period_comparison(
        PeriodComparisonInput(
            metric_name="revenue",
            current_value=Decimal("120"),
            previous_value=Decimal("100"),
            current_period="FY2025",
            previous_period="FY2024",
        )
    )

    assert result.absolute_change == Decimal("20")
    assert result.percentage_change == Decimal("20")
    assert result.direction == "increase"


def test_period_comparison_handles_zero_previous_value() -> None:
    result = FinancialCalculator.period_comparison(
        PeriodComparisonInput(
            metric_name="revenue",
            current_value=Decimal("100"),
            previous_value=Decimal("0"),
            current_period="FY2025",
            previous_period="FY2024",
        )
    )

    assert result.absolute_change == Decimal("100")
    assert result.percentage_change is None
    assert result.direction == "increase"


def test_margin_calculation() -> None:
    result = FinancialCalculator.margin(
        MarginCalculationInput(
            numerator_name="operating_income",
            numerator_value=Decimal("25"),
            denominator_name="revenue",
            denominator_value=Decimal("100"),
        )
    )

    assert result.margin_percentage == Decimal("25")


def test_margin_rejects_zero_denominator() -> None:
    with pytest.raises(
        ValueError,
        match="zero denominator",
    ):
        FinancialCalculator.margin(
            MarginCalculationInput(
                numerator_name="operating_income",
                numerator_value=Decimal("25"),
                denominator_name="revenue",
                denominator_value=Decimal("0"),
            )
        )


def test_cagr_calculation() -> None:
    result = FinancialCalculator.cagr(
        CAGRCalculationInput(
            metric_name="revenue",
            beginning_value=Decimal("100"),
            ending_value=Decimal("121"),
            periods=2,
        )
    )

    assert abs(
        result.cagr_percentage
        - Decimal("10")
    ) < Decimal("0.0001")


def test_cagr_rejects_non_positive_values() -> None:
    with pytest.raises(
        ValueError,
        match="positive beginning value",
    ):
        FinancialCalculator.cagr(
            CAGRCalculationInput(
                metric_name="revenue",
                beginning_value=Decimal("0"),
                ending_value=Decimal("100"),
                periods=2,
            )
        )


def test_anomaly_detector() -> None:
    result = FinancialAnomalyDetector.detect(
        AnomalyDetectionInput(
            metric_name="operating_expense",
            values=[
                Decimal("100"),
                Decimal("101"),
                Decimal("99"),
                Decimal("100"),
                Decimal("220"),
            ],
            threshold=Decimal("2"),
        )
    )

    assert result.anomaly_detected is True
    assert 4 in result.anomaly_indices


def test_anomaly_detector_with_constant_values() -> None:
    result = FinancialAnomalyDetector.detect(
        AnomalyDetectionInput(
            metric_name="revenue",
            values=[
                Decimal("100"),
                Decimal("100"),
                Decimal("100"),
            ],
            threshold=Decimal("2"),
        )
    )

    assert result.anomaly_detected is False
    assert result.anomaly_indices == []


def test_revenue_analysis_sorts_periods() -> None:
    tools = FinancialAnalysisTools()

    result = tools.analyze_revenue(
        RevenueAnalysisInput(
            company="Example Corp",
            periods=[
                make_metric(
                    "Example Corp",
                    "120",
                    2025,
                    MetricType.REVENUE,
                ),
                make_metric(
                    "Example Corp",
                    "100",
                    2024,
                    MetricType.REVENUE,
                ),
            ],
        )
    )

    assert result.first_value == Decimal("100")
    assert result.latest_value == Decimal("120")
    assert result.total_change == Decimal("20")
    assert result.total_change_percentage == Decimal("20")
    assert result.trend == "increasing"


def test_expense_analysis_detects_anomaly() -> None:
    tools = FinancialAnalysisTools()

    result = tools.analyze_expense_trend(
        ExpenseTrendInput(
            company="Example Corp",
            periods=[
                make_metric(
                    "Example Corp",
                    "100",
                    2022,
                    MetricType.OPERATING_EXPENSE,
                ),
                make_metric(
                    "Example Corp",
                    "101",
                    2023,
                    MetricType.OPERATING_EXPENSE,
                ),
                make_metric(
                    "Example Corp",
                    "99",
                    2024,
                    MetricType.OPERATING_EXPENSE,
                ),
                make_metric(
                    "Example Corp",
                    "220",
                    2025,
                    MetricType.OPERATING_EXPENSE,
                ),
            ],
        )
    )

    assert result.trend == "increasing"
    assert result.anomaly_detected is True
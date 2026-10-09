from __future__ import annotations

from decimal import Decimal

from app.tools.anomaly import FinancialAnomalyDetector
from app.tools.calculator import FinancialCalculator
from app.tools.schemas import (
    AnomalyDetectionInput,
    ExpenseTrendInput,
    ExpenseTrendResult,
    FinancialMetric,
    PeriodComparisonInput,
    PeriodComparisonResult,
    RevenueAnalysisInput,
    RevenueAnalysisResult,
)


class FinancialAnalysisTools:
    """Higher-level deterministic financial analysis tools."""

    def __init__(
        self,
        *,
        calculator: FinancialCalculator | None = None,
        anomaly_detector: FinancialAnomalyDetector | None = None,
    ) -> None:
        self.calculator = (
            calculator
            or FinancialCalculator()
        )

        self.anomaly_detector = (
            anomaly_detector
            or FinancialAnomalyDetector()
        )

    def analyze_revenue(
        self,
        data: RevenueAnalysisInput,
    ) -> RevenueAnalysisResult:
        periods = self._sort_periods(data.periods)

        calculations = self._build_period_comparisons(
            periods
        )

        first_value = periods[0].value
        latest_value = periods[-1].value

        total_change = latest_value - first_value

        if first_value == 0:
            total_change_percentage = None
        else:
            total_change_percentage = (
                total_change
                / abs(first_value)
                * Decimal("100")
            )

        trend = self._determine_trend(
            calculations
        )

        return RevenueAnalysisResult(
            company=data.company,
            periods_analyzed=len(periods),
            first_value=first_value,
            latest_value=latest_value,
            total_change=total_change,
            total_change_percentage=(
                total_change_percentage
            ),
            trend=trend,
            calculations=calculations,
        )

    def analyze_expense_trend(
        self,
        data: ExpenseTrendInput,
    ) -> ExpenseTrendResult:
        """Analyze operating-expense movement and detect anomalies when possible."""

        periods = self._sort_periods(data.periods)

        if len(periods) < 2:
            raise ValueError(
                "At least two periods are required for expense trend analysis."
            )

        calculations = self._build_period_comparisons(periods)

        first_value = periods[0].value
        latest_value = periods[-1].value

        total_change = latest_value - first_value

        if first_value == 0:
            total_change_percentage = None
        else:
            total_change_percentage = (
                total_change
                / abs(first_value)
                * Decimal("100")
            )

        anomaly_detected = False

        anomaly_values = [
            metric.value
            for metric in periods
        ]

        # Statistical anomaly detection requires at least 3 observations.
        # With only two periods, trend analysis is still valid, but an
        # anomaly conclusion would not be statistically meaningful.
        if len(anomaly_values) >= 3:
            anomaly_result = self.anomaly_detector.detect(
                AnomalyDetectionInput(
                    metric_name="operating_expense",
                    values=anomaly_values,
                    threshold=Decimal("2"),
                )
            )

            anomaly_detected = anomaly_result.anomaly_detected

        trend = self._determine_trend(calculations)

        return ExpenseTrendResult(
            company=data.company,
            periods_analyzed=len(periods),
            first_value=first_value,
            latest_value=latest_value,
            total_change=total_change,
            total_change_percentage=total_change_percentage,
            trend=trend,
            calculations=calculations,
            anomaly_detected=anomaly_detected,
        )
    @staticmethod
    def _sort_periods(
        periods: list[FinancialMetric],
    ) -> list[FinancialMetric]:
        if not periods:
            raise ValueError(
                "At least one financial period is required."
            )

        return sorted(
            periods,
            key=lambda metric: metric.period.end_date,
        )

    def _build_period_comparisons(
        self,
        periods: list[FinancialMetric],
    ) -> list[PeriodComparisonResult]:
        calculations = []

        for previous, current in zip(
            periods,
            periods[1:],
            strict=False,
        ):
            calculations.append(
                self.calculator.period_comparison(
                    PeriodComparisonInput(
                        metric_name=current.metric.value,
                        current_value=current.value,
                        previous_value=previous.value,
                        current_period=current.period.label,
                        previous_period=previous.period.label,
                    )
                )
            )

        return calculations

    @staticmethod
    def _determine_trend(
        calculations: list[PeriodComparisonResult],
    ) -> str:
        if not calculations:
            return "insufficient_data"

        first_value = calculations[0].previous_value
        latest_value = calculations[-1].current_value

        if latest_value > first_value:
            return "increasing"

        if latest_value < first_value:
            return "decreasing"

        return "unchanged"
from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext

from app.tools.schemas import (
    CAGRCalculationInput,
    CAGRCalculationResult,
    GrowthCalculationInput,
    MarginCalculationInput,
    MarginCalculationResult,
    PeriodComparisonInput,
    PeriodComparisonResult,
)


class FinancialCalculator:
    """Deterministic financial calculations with explicit provenance."""

    @staticmethod
    def period_comparison(
        data: PeriodComparisonInput,
    ) -> PeriodComparisonResult:
        absolute_change = (
            data.current_value - data.previous_value
        )

        if data.previous_value == 0:
            percentage_change: Decimal | None = None
        else:
            percentage_change = (
                absolute_change
                / abs(data.previous_value)
                * Decimal("100")
            )

        if absolute_change > 0:
            direction = "increase"
        elif absolute_change < 0:
            direction = "decrease"
        else:
            direction = "unchanged"

        return PeriodComparisonResult(
            metric_name=data.metric_name,
            current_period=data.current_period,
            previous_period=data.previous_period,
            current_value=data.current_value,
            previous_value=data.previous_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            direction=direction,
            calculation_formula=(
                "absolute_change = current - previous; "
                "percentage_change = "
                "(current - previous) / |previous| * 100"
            ),
        )

    @staticmethod
    def growth(
        data: GrowthCalculationInput,
    ) -> PeriodComparisonResult:
        return FinancialCalculator.period_comparison(
            PeriodComparisonInput(
                metric_name=data.metric_name,
                current_value=data.current_value,
                previous_value=data.previous_value,
                current_period=data.current_period,
                previous_period=data.previous_period,
            )
        )

    @staticmethod
    def margin(
        data: MarginCalculationInput,
    ) -> MarginCalculationResult:
        if data.denominator_value == 0:
            raise ValueError(
                "Cannot calculate a margin with a zero denominator."
            )

        margin = (
            data.numerator_value
            / data.denominator_value
            * Decimal("100")
        )

        return MarginCalculationResult(
            numerator_name=data.numerator_name,
            denominator_name=data.denominator_name,
            numerator_value=data.numerator_value,
            denominator_value=data.denominator_value,
            margin_percentage=margin,
            calculation_formula=(
                "margin_percentage = "
                "numerator / denominator * 100"
            ),
        )

    @staticmethod
    def cagr(
        data: CAGRCalculationInput,
    ) -> CAGRCalculationResult:
        if data.beginning_value <= 0:
            raise ValueError(
                "CAGR requires a positive beginning value."
            )

        if data.ending_value <= 0:
            raise ValueError(
                "CAGR requires a positive ending value."
            )

        with localcontext() as context:
            context.prec = 28

            try:
                ratio = (
                    data.ending_value
                    / data.beginning_value
                )

                cagr = (
                    Decimal(str(float(ratio) ** (1 / data.periods)))
                    - Decimal("1")
                ) * Decimal("100")

            except (InvalidOperation, ZeroDivisionError) as exc:
                raise ValueError(
                    "Unable to calculate CAGR."
                ) from exc

        return CAGRCalculationResult(
            metric_name=data.metric_name,
            beginning_value=data.beginning_value,
            ending_value=data.ending_value,
            periods=data.periods,
            cagr_percentage=cagr,
            calculation_formula=(
                "CAGR = "
                "((ending_value / beginning_value) "
                "** (1 / periods) - 1) * 100"
            ),
        )
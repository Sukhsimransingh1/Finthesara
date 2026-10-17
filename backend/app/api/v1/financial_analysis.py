
"""Standalone financial analysis endpoint backed by SEC company facts."""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.tools.financial_analysis import FinancialAnalysisTools
from app.tools.schemas import (
    ExpenseTrendInput,
    FinancialDataQuery,
    FinancialPeriod,
    MetricType,
    RevenueAnalysisInput,
)
from app.tools.sec_data_source import (
    SECDataSourceError,
    SECFinancialDataSource,
)

router = APIRouter(
    prefix="/financial-analysis",
    tags=["financial-analysis"],
)

METRICS = (
    MetricType.REVENUE,
    MetricType.OPERATING_INCOME,
    MetricType.OPERATING_EXPENSE,
    MetricType.NET_INCOME,
    MetricType.GROSS_PROFIT,
    MetricType.EPS,
)


class FinancialAnalysisRequest(BaseModel):
    """Input supplied by the Financial Analysis page."""

    model_config = ConfigDict(extra="forbid")

    ticker: str = Field(
        min_length=1,
        max_length=12,
        pattern=r"^[A-Za-z0-9.-]+$",
    )
    period: Literal[
        "Latest",
        "FY2024",
        "FY2023",
        "FY2022",
        "Quarterly",
    ] = "Latest"


def build_periods(selection: str) -> list[FinancialPeriod]:
    """Build complete annual or quarterly periods for SEC fact lookup."""
    today = date.today()

    if selection.startswith("FY"):
        year = int(selection[2:])
        return [
            FinancialPeriod(
                label=selection,
                start_date=date(year, 1, 1),
                end_date=date(year, 12, 31),
            )
        ]

    if selection == "Quarterly":
        # Use the last four completed calendar quarters.
        current_quarter = (today.month - 1) // 3
        current_quarter_start_month = current_quarter * 3 + 1
        current_quarter_start = date(
            today.year,
            current_quarter_start_month,
            1,
        )
        periods: list[FinancialPeriod] = []

        for offset in range(4, 0, -1):
            quarter_end_index = (
                current_quarter_start.year * 12
                + current_quarter_start.month
                - 1
                - offset * 3
            )
            year, month_zero_based = divmod(quarter_end_index, 12)
            start_month = month_zero_based + 1
            end_month = start_month + 2

            start = date(year, start_month, 1)
            if end_month == 12:
                end = date(year, 12, 31)
            else:
                next_month_start = date(year, end_month + 1, 1)
                end = date.fromordinal(next_month_start.toordinal() - 1)

            periods.append(
                FinancialPeriod(
                    label=f"{year}-Q{((start_month - 1) // 3) + 1}",
                    start_date=start,
                    end_date=end,
                )
            )

        return periods

    # Exclude the current fiscal year because its annual report may
    # not yet be available.
    latest_completed_year = today.year - 1
    return [
        FinancialPeriod(
            label=f"FY{year}",
            start_date=date(year, 1, 1),
            end_date=date(year, 12, 31),
        )
        for year in range(
            latest_completed_year - 4,
            latest_completed_year + 1,
        )
    ]


@router.post("")
def run_financial_analysis(
    request: FinancialAnalysisRequest,
) -> dict[str, object]:
    """Retrieve reported metrics and calculate changes when possible."""
    ticker = request.ticker.strip().upper()

    if not ticker:
        raise HTTPException(
            status_code=422,
            detail="Enter a valid stock ticker.",
        )

    periods = build_periods(request.period)
    source = SECFinancialDataSource()
    analysis_tools = FinancialAnalysisTools()

    results: list[dict[str, object]] = []
    warnings: list[str] = []
    company_name: str | None = None

    try:
        for metric in METRICS:
            data_result = source.query(
                FinancialDataQuery(
                    company=ticker,
                    metric=metric,
                    periods=periods,
                )
            )

            metric_values = data_result.values
            if metric_values:
                company_name = metric_values[-1].company

            results.append(
                {
                    "metric": metric.value,
                    "values": [
                        item.model_dump(mode="json")
                        for item in metric_values
                    ],
                    "source_count": data_result.source_count,
                }
            )

            if not metric_values:
                warnings.append(
                    f"No SEC data was found for {metric.value} "
                    "for the selected period."
                )

        calculations: list[dict[str, object]] = []

        for result_item in results:
            metric_name = str(result_item["metric"])
            metric_values_payload = result_item["values"]

            if (
                not isinstance(metric_values_payload, list)
                or len(metric_values_payload) < 2
            ):
                continue

            # Re-query as typed financial data for deterministic
            # calculations; never calculate from LLM-generated numbers.
            metric_enum = MetricType(metric_name)
            typed_data_result = source.query(
                FinancialDataQuery(
                    company=ticker,
                    metric=metric_enum,
                    periods=periods,
                )
            )

            if len(typed_data_result.values) < 2:
                continue

            try:
                if metric_enum == MetricType.REVENUE:
                    revenue_calculation = analysis_tools.analyze_revenue(
                        RevenueAnalysisInput(
                            company=typed_data_result.company,
                            periods=typed_data_result.values,
                        )
                    )
                    calculation_data = revenue_calculation.model_dump(
                        mode="json"
                    )

                elif metric_enum == MetricType.OPERATING_EXPENSE:
                    expense_calculation = (
                        analysis_tools.analyze_expense_trend(
                            ExpenseTrendInput(
                                company=typed_data_result.company,
                                periods=typed_data_result.values,
                            )
                        )
                    )
                    calculation_data = expense_calculation.model_dump(
                        mode="json"
                    )

                else:
                    continue

                calculations.append(
                    {
                        "metric": metric_name,
                        "result": calculation_data,
                    }
                )

            except ValueError as exc:
                warnings.append(
                    f"Could not calculate {metric_name} trend: {exc}"
                )

    except SECDataSourceError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    if not any(item["values"] for item in results):
        raise HTTPException(
            status_code=404,
            detail=(
                f"No usable SEC financial data was found for {ticker}. "
                "Check the ticker and SEC_USER_AGENT configuration."
            ),
        )

    return {
        "ticker": ticker,
        "company": company_name or ticker,
        "period": request.period,
        "source": "SEC EDGAR Company Facts",
        "metrics": results,
        "calculations": calculations,
        "warnings": warnings,
    }

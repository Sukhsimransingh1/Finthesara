from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MetricType(StrEnum):
    REVENUE = "revenue"
    OPERATING_EXPENSE = "operating_expense"
    OPERATING_INCOME = "operating_income"
    NET_INCOME = "net_income"
    GROSS_PROFIT = "gross_profit"
    EPS = "eps"


class FinancialPeriod(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1)
    start_date: date
    end_date: date

    def validate_range(self) -> None:
        if self.start_date > self.end_date:
            raise ValueError(
                "start_date cannot be after end_date."
            )


class FinancialMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    metric: MetricType
    period: FinancialPeriod
    value: Decimal
    currency: str | None = None
    unit: str | None = None
    source_id: str | None = None
    source_url: str | None = None


class FinancialDataQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    metric: MetricType
    periods: list[FinancialPeriod] = Field(
        min_length=1,
        max_length=20,
    )


class FinancialDataResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    metric: MetricType
    values: list[FinancialMetric]
    source_count: int = Field(ge=0)


class PeriodComparisonInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(min_length=1)
    current_value: Decimal
    previous_value: Decimal
    current_period: str = Field(min_length=1)
    previous_period: str = Field(min_length=1)


class PeriodComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    current_period: str
    previous_period: str
    current_value: Decimal
    previous_value: Decimal

    absolute_change: Decimal
    percentage_change: Decimal | None

    direction: str
    calculation_formula: str


class GrowthCalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(min_length=1)
    current_value: Decimal
    previous_value: Decimal
    current_period: str = Field(min_length=1)
    previous_period: str = Field(min_length=1)


class MarginCalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numerator_name: str = Field(min_length=1)
    numerator_value: Decimal

    denominator_name: str = Field(min_length=1)
    denominator_value: Decimal


class MarginCalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    numerator_name: str
    denominator_name: str
    numerator_value: Decimal
    denominator_value: Decimal
    margin_percentage: Decimal
    calculation_formula: str


class CAGRCalculationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(min_length=1)
    beginning_value: Decimal
    ending_value: Decimal
    periods: int = Field(gt=0)


class CAGRCalculationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    beginning_value: Decimal
    ending_value: Decimal
    periods: int
    cagr_percentage: Decimal
    calculation_formula: str


class RevenueAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    periods: list[FinancialMetric] = Field(
        min_length=2,
        max_length=20,
    )


class RevenueAnalysisResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    periods_analyzed: int
    first_value: Decimal
    latest_value: Decimal
    total_change: Decimal
    total_change_percentage: Decimal | None
    trend: str
    calculations: list[PeriodComparisonResult]


class ExpenseTrendInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1)
    periods: list[FinancialMetric] = Field(
        min_length=2,
        max_length=20,
    )


class ExpenseTrendResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    periods_analyzed: int
    first_value: Decimal
    latest_value: Decimal
    total_change: Decimal
    total_change_percentage: Decimal | None
    trend: str
    anomaly_detected: bool
    calculations: list[PeriodComparisonResult]


class AnomalyDetectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str = Field(min_length=1)
    values: list[Decimal] = Field(
        min_length=3,
        max_length=100,
    )
    threshold: Decimal = Field(
        gt=Decimal("0"),
        le=Decimal("10"),
    )


class AnomalyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric_name: str
    anomaly_detected: bool
    anomaly_indices: list[int]
    mean: Decimal
    standard_deviation: Decimal
    threshold: Decimal
    reasons: list[str]


class CalculationProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calculation_type: str
    inputs: dict[str, Any]
    formula: str
    result: Any
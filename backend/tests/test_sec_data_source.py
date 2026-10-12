
from __future__ import annotations

from datetime import date

from app.tools.schemas import (
    FinancialDataQuery,
    FinancialPeriod,
    MetricType,
)
from app.tools.sec_data_source import SECFinancialDataSource


def test_normalize_company_removes_legal_suffixes() -> None:
    assert (
        SECFinancialDataSource._normalize_company("Apple Inc.")
        == "apple"
    )
    assert (
        SECFinancialDataSource._normalize_company(
            "Microsoft Corporation"
        )
        == "microsoft"
    )


def test_annual_period_classification() -> None:
    period = FinancialPeriod(
        label="2024",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 12, 31),
    )

    assert SECFinancialDataSource._period_kind(period) == "annual"


def test_quarterly_period_classification() -> None:
    period = FinancialPeriod(
        label="Q1 2025",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 3, 31),
    )

    assert SECFinancialDataSource._period_kind(period) == "quarterly"


def test_annual_fact_duration_validation() -> None:
    assert SECFinancialDataSource._eligible_duration(
        date(2023, 10, 1),
        date(2024, 9, 30),
        "annual",
    )

    assert not SECFinancialDataSource._eligible_duration(
        date(2024, 1, 1),
        date(2024, 3, 31),
        "annual",
    )


def test_quarterly_fact_duration_validation() -> None:
    assert SECFinancialDataSource._eligible_duration(
        date(2025, 1, 1),
        date(2025, 3, 31),
        "quarterly",
    )


def test_source_url_uses_filing_accession() -> None:
    url = SECFinancialDataSource._source_url(
        cik=320193,
        fact={
            "accn": "0000320193-24-000123",
        },
    )

    assert (
        url
        == "https://www.sec.gov/Archives/edgar/data/"
        "320193/000032019324000123/"
    )


def test_financial_query_schema_remains_compatible() -> None:
    query = FinancialDataQuery(
        company="AAPL",
        metric=MetricType.REVENUE,
        periods=[
            FinancialPeriod(
                label="2024",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 12, 31),
            )
        ],
    )

    assert query.company == "AAPL"
    assert query.metric == MetricType.REVENUE


def test_quarter_label_uses_reported_period_not_later_filing_metadata() -> None:
    # Apple's FY2024 Q1 ended on 2023-12-30, although SEC comparative
    # facts may carry later filing-year metadata.
    assert SECFinancialDataSource._quarter_label(
        date(2023, 12, 30),
        "Q1",
    ) == "Q1 FY2024"


def test_quarter_label_calendar_year_quarter() -> None:
    assert SECFinancialDataSource._quarter_label(
        date(2025, 3, 31),
        "Q1",
    ) == "Q1 FY2025"

"""Live smoke test for Apple's FY2024 revenue and net income from SEC XBRL.

Run from the repository root:
    uv run --directory backend python scripts/live_sec_smoke_test.py

Requires SEC_USER_AGENT in backend/.env or the process environment, e.g.
    AgenticFinanceResearch/1.0 contact@example.com
"""
from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

# Running via `uv run --directory backend python scripts/...` sets cwd to backend.
BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.tools.schemas import FinancialDataQuery, FinancialPeriod, MetricType  # noqa: E402
from app.tools.sec_data_source import SECFinancialDataSource  # noqa: E402


FY2024 = FinancialPeriod(
    label="FY2024",
    start_date=date(2023, 10, 1),
    # Apple reported its FY2024 financial year ended on September 28, 2024.
    # September 30 is used as the requested window boundary, not the fact's end date.
    end_date=date(2024, 9, 30),
)
EXPECTED = {
    MetricType.REVENUE: Decimal("391035000000"),
    MetricType.NET_INCOME: Decimal("93736000000"),
}


def main() -> int:
    source = SECFinancialDataSource()
    failures: list[str] = []

    for metric, expected_value in EXPECTED.items():
        result = source.query(
            FinancialDataQuery(
                company="AAPL",
                metric=metric,
                periods=[FY2024],
            )
        )
        matches = [
            item for item in result.values
            if item.period.start_date == date(2023, 10, 1)
            and item.period.end_date == date(2024, 9, 28)
        ]
        if not matches:
            failures.append(f"{metric.value}: no FY2024 fact for 2023-10-01 to 2024-09-28")
            print(f"FAIL {metric.value}: no matching FY2024 fact")
            continue

        item = matches[-1]
        valid = (
            item.value == expected_value
            and item.period.label == "FY2024"
            and bool(item.source_id)
            and bool(item.source_url)
        )
        print(f"{metric.value}: {item.value} {item.currency or ''}".strip())
        print(f"  period: {item.period.label} ({item.period.start_date} to {item.period.end_date})")
        print(f"  source_id: {item.source_id}")
        print(f"  source_url: {item.source_url}")
        if not valid:
            failures.append(
                f"{metric.value}: expected {expected_value}, got {item.value}; "
                f"label={item.period.label!r}, source_id/url required"
            )
            print("  FAIL: value, period label, or source metadata did not match")
        else:
            print("  PASS")

    if failures:
        print("\nLIVE SEC SMOKE TEST FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("\nLIVE SEC SMOKE TEST PASSED: FY2024 facts and source metadata match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from typing import Protocol

from app.tools.schemas import (
    FinancialDataQuery,
    FinancialDataResult,
)


class FinancialDataSource(Protocol):
    """Typed interface for structured financial data providers."""

    def query(
        self,
        request: FinancialDataQuery,
    ) -> FinancialDataResult:
        ...
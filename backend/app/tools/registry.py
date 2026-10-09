from __future__ import annotations

from app.tools.anomaly import FinancialAnomalyDetector
from app.tools.calculator import FinancialCalculator
from app.tools.data_source import FinancialDataSource
from app.tools.financial_analysis import FinancialAnalysisTools


class FinancialToolRegistry:
    """
    Central registry for approved financial tools.

    Agents should receive this registry rather than direct
    database/API access.
    """

    def __init__(
        self,
        *,
        financial_data_source: FinancialDataSource,
    ) -> None:
        self.financial_data_source = financial_data_source

        self.calculator = FinancialCalculator()

        self.anomaly_detector = (
            FinancialAnomalyDetector()
        )

        self.analysis = FinancialAnalysisTools(
            calculator=self.calculator,
            anomaly_detector=self.anomaly_detector,
        )
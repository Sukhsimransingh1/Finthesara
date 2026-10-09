from __future__ import annotations

from decimal import Decimal, localcontext
from math import sqrt

from app.tools.schemas import AnomalyDetectionInput, AnomalyResult


class FinancialAnomalyDetector:
    """Detect statistical anomalies using leave-one-out z-scores."""

    @staticmethod
    def detect(data: AnomalyDetectionInput) -> AnomalyResult:
        values = data.values

        if len(values) < 3:
            raise ValueError("At least three values are required for anomaly detection.")

        anomaly_indices: list[int] = []
        reasons: list[str] = []

        with localcontext() as context:
            context.prec = 28

            total = sum(values, Decimal("0"))
            count = Decimal(len(values))
            overall_mean = total / count

            squared_differences = [
                (value - overall_mean) ** 2
                for value in values
            ]
            overall_variance = (
                sum(squared_differences, Decimal("0")) / count
            )
            overall_standard_deviation = Decimal(
                str(sqrt(float(overall_variance)))
            )

            for index, value in enumerate(values):
                remaining = values[:index] + values[index + 1:]

                remaining_count = Decimal(len(remaining))
                baseline_mean = (
                    sum(remaining, Decimal("0")) / remaining_count
                )

                baseline_squared_differences = [
                    (remaining_value - baseline_mean) ** 2
                    for remaining_value in remaining
                ]

                baseline_variance = (
                    sum(
                        baseline_squared_differences,
                        Decimal("0"),
                    )
                    / remaining_count
                )

                baseline_standard_deviation = Decimal(
                    str(sqrt(float(baseline_variance)))
                )

                if baseline_standard_deviation == 0:
                    continue

                z_score = abs(
                    (value - baseline_mean)
                    / baseline_standard_deviation
                )

                if z_score >= data.threshold:
                    anomaly_indices.append(index)
                    reasons.append(
                        f"Index {index} is anomalous with "
                        f"z-score {z_score:.3f}."
                    )

        return AnomalyResult(
            metric_name=data.metric_name,
            anomaly_detected=bool(anomaly_indices),
            anomaly_indices=anomaly_indices,
            mean=overall_mean,
            standard_deviation=overall_standard_deviation,
            threshold=data.threshold,
            reasons=reasons,
        )
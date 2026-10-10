
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.research_runner import ResearchRunner
from app.tools.data_source import FinancialDataSource


class EvaluationCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)
    project_id: str
    expected_terms: list[str] = Field(default_factory=list)


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    completed: bool
    has_report: bool
    has_evidence: bool
    verification_status: str | None
    expected_terms_found: list[str]
    expected_terms_missing: list[str]
    latency_seconds: float
    error: str | None = None


def load_cases(path: Path) -> list[EvaluationCase]:
    """Load one JSON object per line."""
    cases: list[EvaluationCase] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue

            try:
                cases.append(
                    EvaluationCase.model_validate_json(line)
                )
            except Exception as exc:
                raise ValueError(
                    f"Invalid evaluation case on line {line_number}."
                ) from exc

    if not cases:
        raise ValueError("Evaluation dataset is empty.")

    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("Evaluation case IDs must be unique.")

    return cases


def evaluate_cases(
    *,
    cases: list[EvaluationCase],
    data_source: FinancialDataSource,
    production: bool = True,
) -> list[EvaluationResult]:
    """Execute cases and collect observable, reproducible metrics."""
    runner = ResearchRunner(
        data_source=data_source,
        production=production,
    )
    results: list[EvaluationResult] = []

    for case in cases:
        started = time.perf_counter()

        try:
            state = runner.run(
                question=case.question,
                project_id=case.project_id,
                run_id=str(uuid4()),
            )
            report = str(
                state.get("final_report")
                or state.get("draft_report")
                or ""
            )
            report_lower = report.casefold()

            found = [
                term for term in case.expected_terms
                if term.casefold() in report_lower
            ]
            missing = [
                term for term in case.expected_terms
                if term.casefold() not in report_lower
            ]

            verification = state.get("verification_result")
            verification_status: str | None = None

            if verification is not None:
                raw_status = getattr(
                    verification,
                    "status",
                    None,
                )
                if raw_status is None and isinstance(
                    verification,
                    dict,
                ):
                    raw_status = verification.get("status")
                if raw_status is not None:
                    verification_status = str(
                        getattr(raw_status, "value", raw_status)
                    )

            evidence = state.get("evidence", [])
            results.append(
                EvaluationResult(
                    case_id=case.case_id,
                    completed=state.get("status") not in {
                        "failed",
                        "error",
                    },
                    has_report=bool(report.strip()),
                    has_evidence=bool(evidence),
                    verification_status=verification_status,
                    expected_terms_found=found,
                    expected_terms_missing=missing,
                    latency_seconds=round(
                        time.perf_counter() - started,
                        3,
                    ),
                )
            )
        except Exception as exc:
            results.append(
                EvaluationResult(
                    case_id=case.case_id,
                    completed=False,
                    has_report=False,
                    has_evidence=False,
                    verification_status=None,
                    expected_terms_found=[],
                    expected_terms_missing=case.expected_terms,
                    latency_seconds=round(
                        time.perf_counter() - started,
                        3,
                    ),
                    error=type(exc).__name__,
                )
            )

    return results


def summarize_results(
    results: list[EvaluationResult],
) -> dict[str, Any]:
    """Calculate aggregate outcomes without inventing accuracy scores."""
    total = len(results)

    if total == 0:
        raise ValueError("No evaluation results to summarize.")

    return {
        "case_count": total,
        "completion_rate": round(
            sum(result.completed for result in results) / total,
            4,
        ),
        "report_rate": round(
            sum(result.has_report for result in results) / total,
            4,
        ),
        "evidence_rate": round(
            sum(result.has_evidence for result in results) / total,
            4,
        ),
        "mean_latency_seconds": round(
            sum(result.latency_seconds for result in results) / total,
            3,
        ),
        "verification_status_counts": {
            status: sum(
                result.verification_status == status
                for result in results
            )
            for status in sorted(
                {
                    result.verification_status
                    for result in results
                    if result.verification_status is not None
                }
            )
        },
        "expected_term_match_rate": round(
            sum(
                len(result.expected_terms_found)
                for result in results
            )
            / max(
                1,
                sum(
                    len(result.expected_terms_found)
                    + len(result.expected_terms_missing)
                    for result in results
                ),
            ),
            4,
        ),
    }


def write_results(
    *,
    results: list[EvaluationResult],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": summarize_results(results),
        "results": [
            result.model_dump(mode="json")
            for result in results
        ],
    }

    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

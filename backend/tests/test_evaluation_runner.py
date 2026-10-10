
from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.evaluation.runner import (
    EvaluationResult,
    load_cases,
    summarize_results,
    write_results,
)


def test_load_cases_reads_jsonl(tmp_path: Path) -> None:
    dataset = tmp_path / "cases.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "case_id": "case-1",
                "question": "Analyze company revenue.",
                "project_id": "test-project",
                "expected_terms": ["revenue"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    cases = load_cases(dataset)

    assert len(cases) == 1
    assert cases[0].case_id == "case-1"


def test_load_cases_rejects_duplicate_ids(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "cases.jsonl"
    item = {
        "case_id": "duplicate",
        "question": "Test question",
        "project_id": "test-project",
    }
    dataset.write_text(
        json.dumps(item) + "\n" + json.dumps(item),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unique"):
        load_cases(dataset)


def test_summary_calculates_observable_metrics() -> None:
    results = [
        EvaluationResult(
            case_id="one",
            completed=True,
            has_report=True,
            has_evidence=True,
            verification_status="pass",
            expected_terms_found=["revenue"],
            expected_terms_missing=[],
            latency_seconds=2.0,
        ),
        EvaluationResult(
            case_id="two",
            completed=False,
            has_report=False,
            has_evidence=False,
            verification_status=None,
            expected_terms_found=[],
            expected_terms_missing=["profit"],
            latency_seconds=4.0,
        ),
    ]

    summary = summarize_results(results)

    assert summary["case_count"] == 2
    assert summary["completion_rate"] == 0.5
    assert summary["report_rate"] == 0.5
    assert summary["evidence_rate"] == 0.5
    assert summary["mean_latency_seconds"] == 3.0
    assert summary["expected_term_match_rate"] == 0.5


def test_summary_rejects_empty_results() -> None:
    with pytest.raises(ValueError, match="No evaluation results"):
        summarize_results([])


def test_write_results_creates_parent_directory(
    tmp_path: Path,
) -> None:
    result = EvaluationResult(
        case_id="one",
        completed=True,
        has_report=True,
        has_evidence=False,
        verification_status=None,
        expected_terms_found=[],
        expected_terms_missing=[],
        latency_seconds=1.25,
    )
    destination = tmp_path / "nested" / "results.json"

    write_results(
        results=[result],
        output_path=destination,
    )

    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 1
    assert payload["results"][0]["case_id"] == "one"

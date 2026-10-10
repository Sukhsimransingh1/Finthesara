
from __future__ import annotations

import argparse
from pathlib import Path

from app.evaluation.runner import (
    evaluate_cases,
    load_cases,
    write_results,
)
from app.tools.mock_data_source import InMemoryFinancialDataSource


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evaluation_data/smoke.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation_results/latest.json"),
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="Run the deterministic graph without the LLM.",
    )
    args = parser.parse_args()

    cases = load_cases(args.dataset)
    results = evaluate_cases(
        cases=cases,
        data_source=InMemoryFinancialDataSource(metrics=[]),
        production=not args.deterministic,
    )
    write_results(results=results, output_path=args.output)

    print(f"Evaluated {len(results)} cases.")
    print(f"Results written to {args.output}")
    print(
        "Completion rate: "
        f"{sum(item.completed for item in results) / len(results):.1%}"
    )


if __name__ == "__main__":
    main()

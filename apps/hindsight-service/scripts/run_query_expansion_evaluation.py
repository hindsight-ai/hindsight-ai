"""CLI to evaluate query expansion quality against a dataset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.db.database import SessionLocal
from core.search.evaluation import evaluate_cases, load_cases_from_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate query expansion performance")
    parser.add_argument("--dataset", required=True, help="Path to the JSON dataset containing evaluation cases")
    parser.add_argument("--output", help="Optional path to write the evaluation summary as JSON")
    args = parser.parse_args(argv)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        parser.error(f"Dataset file not found: {dataset_path}")

    cases = load_cases_from_file(str(dataset_path))

    with SessionLocal() as session:
        summary = evaluate_cases(session, cases)

    output = json.dumps(summary, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())

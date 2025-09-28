"""CLI to evaluate query expansion quality against a dataset."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

from core.db import models
from core.db.database import SessionLocal
from core.search.evaluation import (
    QueryExpansionCase,
    evaluate_cases,
    load_cases_from_file,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate query expansion performance")
    parser.add_argument("--dataset", help="Path to the JSON dataset containing evaluation cases")
    parser.add_argument("--output", help="Optional path to write the evaluation summary as JSON")
    parser.add_argument(
        "--seed-sample-data",
        action="store_true",
        help="Populate a lightweight dataset in the current database before evaluation",
    )
    args = parser.parse_args(argv)

    dataset_cases: list[QueryExpansionCase] = []
    if args.dataset:
        dataset_path = Path(args.dataset)
        if not dataset_path.exists():
            parser.error(f"Dataset file not found: {dataset_path}")
        dataset_cases.extend(load_cases_from_file(str(dataset_path)))

    with SessionLocal() as session:
        if args.seed_sample_data:
            dataset_cases.extend(_seed_sample_dataset(session))

        if not dataset_cases:
            parser.error("No dataset supplied. Provide --dataset or --seed-sample-data.")

        summary = evaluate_cases(session, dataset_cases)

    output = json.dumps(summary, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    return 0


def _seed_sample_dataset(session) -> list[QueryExpansionCase]:
    """Create a minimal dataset mirroring the query-expansion integration test."""

    user = session.query(models.User).filter(models.User.email == "ci-expander@example.com").one_or_none()
    if not user:
        user = models.User(email="ci-expander@example.com", display_name="CI Expander")
        session.add(user)
        session.flush()

    agent = models.Agent(
        agent_id=uuid.uuid4(),
        agent_name="CI Expansion Agent",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    session.add(agent)
    session.flush()

    memory = models.MemoryBlock(
        id=uuid.uuid4(),
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="System performance tuning notes focused on speed and latency improvements.",
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    session.add(memory)
    session.commit()

    return [
        QueryExpansionCase(
            query="speed",
            search_type="hybrid",
            relevant_ids=[memory.id],
            agent_id=agent.agent_id,
        )
    ]


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())

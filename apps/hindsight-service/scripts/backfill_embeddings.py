"""Utility to backfill embeddings for existing memory blocks."""

from __future__ import annotations

import argparse
import sys
from contextlib import suppress

from sqlalchemy import func

from core.db import models
from core.db.database import SessionLocal
from core.services import get_embedding_service


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate missing memory embeddings")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of rows to process per batch (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many rows require embeddings without updating them",
    )
    return parser.parse_args(argv)


def count_missing(session) -> int:
    return (
        session.query(func.count())
        .select_from(models.MemoryBlock)
        .filter(models.MemoryBlock.content_embedding.is_(None))
        .scalar()  # type: ignore[no-untyped-call]
    )


def backfill(batch_size: int, dry_run: bool) -> int:
    session = SessionLocal()
    try:
        pending = count_missing(session)
        if dry_run:
            print(f"{pending} memory blocks require embeddings; no changes made.")
            return 0

        if pending == 0:
            print("All memory blocks already have embeddings.")
            return 0

        service = get_embedding_service()
        if not service.is_enabled:
            print(
                "Embedding provider is disabled. Set EMBEDDING_PROVIDER before running the backfill.",
                file=sys.stderr,
            )
            return 1

        updated = service.backfill_missing_embeddings(session, batch_size=batch_size)
        print(f"Backfilled embeddings for {updated} memory blocks (pending before run: {pending}).")
        return 0
    finally:
        with suppress(Exception):
            session.close()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return backfill(batch_size=args.batch_size, dry_run=args.dry_run)


if __name__ == "__main__":  # pragma: no cover - manual execution path
    sys.exit(main())

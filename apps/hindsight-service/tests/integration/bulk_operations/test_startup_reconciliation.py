"""Regression test for #88 — bulk-op startup reconciliation.

Pre-#88, killing the API process mid-bulk-operation left the DB row at
status='running' indefinitely. The status endpoint reported the long-dead
operation as live forever.

Post-#88, `reconcile_stuck_bulk_operations()` runs from the FastAPI
`lifespan` startup hook BEFORE the new process accepts traffic. It marks
any `running` row whose `started_at` is older than a grace window
(default 60s) as `failed` with an annotated `error_log`.

The grace window prevents a graceful blue/green deploy from falsely
failing operations whose worker is still alive in the new process.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from core.async_bulk_operations import reconcile_stuck_bulk_operations
from core.db import models


def _seed_user_and_org(db: Session) -> tuple[models.User, models.Organization]:
    user = models.User(
        email=f"reconcile-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Reconcile Test User",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    org = models.Organization(name=f"reconcile-org-{uuid.uuid4().hex[:6]}", slug=f"reconcile-{uuid.uuid4().hex[:6]}")
    db.add(org)
    db.commit()
    db.refresh(org)
    return user, org


def test_reconcile_marks_old_running_rows_as_failed(db_session: Session):
    """A `running` op whose started_at is well past the grace window flips to failed."""
    user, org = _seed_user_and_org(db_session)
    op = models.BulkOperation(
        type="bulk_compact",
        actor_user_id=user.id,
        organization_id=org.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
    )
    db_session.add(op)
    db_session.commit()
    db_session.refresh(op)

    reconciled = reconcile_stuck_bulk_operations(min_age_seconds=60, session=db_session)
    assert reconciled >= 1

    db_session.expire_all()
    fresh = db_session.query(models.BulkOperation).get(op.id)
    assert fresh.status == "failed"
    assert fresh.finished_at is not None
    assert "server restarted" in (fresh.error_log or {}).get("errors", [""])[0]


def test_reconcile_skips_recent_running_rows_within_grace(db_session: Session):
    """A `running` op whose started_at is INSIDE the grace window is left alone — graceful-restart safety."""
    user, org = _seed_user_and_org(db_session)
    op = models.BulkOperation(
        type="bulk_compact",
        actor_user_id=user.id,
        organization_id=org.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(seconds=10),  # within 60s grace
    )
    db_session.add(op)
    db_session.commit()
    db_session.refresh(op)

    # Pass a 60s grace window; this op is only 10s old — should NOT be reconciled
    reconcile_stuck_bulk_operations(min_age_seconds=60, session=db_session)

    db_session.expire_all()
    fresh = db_session.query(models.BulkOperation).get(op.id)
    assert fresh.status == "running"
    assert fresh.finished_at is None


def test_reconcile_skips_terminal_status_rows(db_session: Session):
    """`completed` / `failed` / `cancelled` rows are left untouched (idempotent)."""
    user, org = _seed_user_and_org(db_session)
    long_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    finished_op = models.BulkOperation(
        type="bulk_compact",
        actor_user_id=user.id,
        organization_id=org.id,
        status="completed",
        started_at=long_ago,
        finished_at=long_ago,
    )
    db_session.add(finished_op)
    db_session.commit()
    db_session.refresh(finished_op)

    reconcile_stuck_bulk_operations(min_age_seconds=60, session=db_session)

    db_session.expire_all()
    fresh = db_session.query(models.BulkOperation).get(finished_op.id)
    assert fresh.status == "completed"


def test_reconcile_appends_error_to_existing_log(db_session: Session):
    """If error_log already has entries, we append rather than clobber."""
    user, org = _seed_user_and_org(db_session)
    op = models.BulkOperation(
        type="bulk_compact",
        actor_user_id=user.id,
        organization_id=org.id,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        error_log={"errors": ["worker reported partial failure"]},
    )
    db_session.add(op)
    db_session.commit()
    db_session.refresh(op)

    reconcile_stuck_bulk_operations(min_age_seconds=60, session=db_session)

    db_session.expire_all()
    fresh = db_session.query(models.BulkOperation).get(op.id)
    errors = (fresh.error_log or {}).get("errors", [])
    assert len(errors) == 2
    assert errors[0] == "worker reported partial failure"
    assert "server restarted" in errors[1]


def test_reconcile_returns_zero_when_nothing_stuck(db_session: Session):
    """Empty case is a no-op."""
    reconciled = reconcile_stuck_bulk_operations(min_age_seconds=60)
    assert reconciled == 0

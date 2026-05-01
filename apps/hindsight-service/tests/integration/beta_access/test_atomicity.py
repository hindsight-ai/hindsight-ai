"""Regression test for #89 — beta-access admin override atomicity.

Pre-#89, `update_beta_access_request_status` committed internally and the
caller in `core/api/beta_access.py` then committed `user.beta_access_status`
in a second transaction. A process death between the two commits left the
request record updated but the user row stale until next login.

Post-#89, the repo function accepts `autocommit=False` to defer commit to
the caller. The admin-override flow uses this so both writes share one
transaction — atomic semantics.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.db import models
from core.db.repositories import beta_access as beta_repo


def _seed_user_and_request(db: Session, status: str = "pending") -> tuple[models.User, models.BetaAccessRequest]:
    user = models.User(
        email=f"atomic-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Atomic Test User",
        beta_access_status=status,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    req = models.BetaAccessRequest(
        user_id=user.id,
        email=user.email,
        status=status,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return user, req


def test_autocommit_true_preserves_legacy_behavior(db_session: Session):
    """Default behavior unchanged: the repo commits and the change is visible immediately."""
    _, req = _seed_user_and_request(db_session)
    updated = beta_repo.update_beta_access_request_status(
        db_session,
        req.id,
        "accepted",
        reviewer_email="admin@example.com",
        decision_reason="auto-approved",
    )
    assert updated is not None
    assert updated.status == "accepted"
    # Visible to a fresh query (committed)
    assert db_session.query(models.BetaAccessRequest).get(req.id).status == "accepted"


def test_autocommit_false_defers_commit_to_caller(db_session: Session):
    """With autocommit=False, the change lives in the session but not the DB until caller commits."""
    user, req = _seed_user_and_request(db_session)

    beta_repo.update_beta_access_request_status(
        db_session,
        req.id,
        "accepted",
        reviewer_email="admin@example.com",
        decision_reason="manual",
        autocommit=False,
    )
    # The session sees the change — but the row is still in the open txn,
    # not committed. Mirror to user row in the same txn.
    user.beta_access_status = "accepted"

    # Until commit, both writes can be rolled back together.
    db_session.commit()

    fresh_req = db_session.query(models.BetaAccessRequest).get(req.id)
    fresh_user = db_session.query(models.User).get(user.id)
    assert fresh_req.status == "accepted"
    assert fresh_user.beta_access_status == "accepted"


def test_autocommit_false_rollback_unwinds_both_writes(db_session: Session):
    """If something fails before commit, both the request-side AND user-side writes roll back atomically."""
    user, req = _seed_user_and_request(db_session, status="pending")

    beta_repo.update_beta_access_request_status(
        db_session,
        req.id,
        "accepted",
        reviewer_email="admin@example.com",
        decision_reason="manual",
        autocommit=False,
    )
    user.beta_access_status = "accepted"

    # Simulate something going wrong before the caller commits.
    db_session.rollback()

    fresh_req = db_session.query(models.BetaAccessRequest).get(req.id)
    fresh_user = db_session.query(models.User).get(user.id)
    # Pre-#89 the request would already be committed and the user row would
    # not — leaving the half-applied state. Post-#89, both stay at 'pending'.
    assert fresh_req.status == "pending"
    assert fresh_user.beta_access_status == "pending"


def test_autocommit_false_returns_none_when_request_missing(db_session: Session):
    """No-op signal preserved: missing row returns None without raising."""
    result = beta_repo.update_beta_access_request_status(
        db_session,
        uuid.uuid4(),  # nonexistent
        "accepted",
        autocommit=False,
    )
    assert result is None

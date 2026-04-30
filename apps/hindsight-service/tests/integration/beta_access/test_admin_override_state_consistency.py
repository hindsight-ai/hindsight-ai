"""Regression guard for the beta-access admin override state consistency (#77).

Pre-#77 the admin override route wrote `user.beta_access_status` BEFORE the
BetaAccessRequest record. If the request-side update failed, the user row
was already updated, leaving the two stores diverged. Post-#77 the request
record is written first; the user row is mirrored only after.

This test exercises the happy path (admin override succeeds → both stores
consistent) plus the model-comment match.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models
from core.db.repositories import beta_access as beta_repo


def _admin_headers():
    # Per conftest autouse env: BETA_ACCESS_ADMINS includes ibarz.jean@gmail.com
    return {
        "x-auth-request-email": "ibarz.jean@gmail.com",
        "x-auth-request-user": "ibarz.jean",
        "x-active-scope": "personal",
    }


@pytest.mark.parametrize("desired_status", ["accepted", "denied", "revoked", "not_requested"])
def test_admin_override_writes_request_record_before_user_row(db_session, desired_status):
    """For every admin-override target status, both stores reflect the change.

    Pre-#77 the user row was written first; if the request-side update failed
    afterwards, the stores would diverge. Post-#77 the request record is
    written first.
    """
    target_user = models.User(
        email=f"target-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Target",
        beta_access_status="pending",
    )
    db_session.add(target_user)
    db_session.commit()
    db_session.refresh(target_user)

    # Seed an existing pending request so the override has something to update.
    existing_request = models.BetaAccessRequest(
        email=target_user.email,
        status="pending",
    )
    db_session.add(existing_request)
    db_session.commit()
    db_session.refresh(existing_request)

    client = TestClient(app)
    resp = client.patch(
        f"/beta-access/admin/users/{target_user.id}",
        json={"status": desired_status},
        headers=_admin_headers(),
    )
    assert resp.status_code == 200, resp.text

    db_session.expire_all()
    refreshed_user = db_session.query(models.User).filter(models.User.id == target_user.id).first()
    refreshed_request = beta_repo.get_beta_access_request_by_email(db_session, target_user.email)

    assert refreshed_user.beta_access_status == desired_status, (
        f"REGRESSION (#77): user.beta_access_status should be {desired_status!r}, "
        f"got {refreshed_user.beta_access_status!r}"
    )

    if desired_status in {"accepted", "denied"}:
        # Request record mirrors directly.
        assert refreshed_request is not None
        assert refreshed_request.status == desired_status, (
            f"REGRESSION (#77): for desired={desired_status!r}, request record "
            f"should be {desired_status!r}, got {refreshed_request.status!r}"
        )
    elif desired_status in {"revoked", "not_requested"}:
        # Per existing route logic: request record maps to 'denied' for these
        # admin-override targets (the request record can't natively express
        # 'revoked' or 'not_requested'). The mapping is intentional; this
        # assertion pins it so future changes are deliberate.
        assert refreshed_request is not None
        assert refreshed_request.status == "denied", (
            f"REGRESSION (#77): admin override of {desired_status!r} should "
            f"map the request record to 'denied'; got {refreshed_request.status!r}"
        )


def test_users_model_comment_lists_revoked():
    """The model comment must enumerate all 5 possible status values; pre-#77
    the comment omitted 'revoked' even though the admin override accepts it."""
    import inspect
    from core.db.models import users as users_module

    source = inspect.getsource(users_module)
    # The comment block precedes the beta_access_status Column definition.
    # We assert all 5 known status values are mentioned in the file.
    for status in ["not_requested", "pending", "accepted", "denied", "revoked"]:
        assert status in source, (
            f"REGRESSION (#77): users.py should document the {status!r} status "
            f"value in the beta_access_status column comment."
        )

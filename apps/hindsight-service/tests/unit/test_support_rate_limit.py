import os
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.api.main import app
from core.api.deps import get_current_user_context
from core.db import models


def _h():
    return {"x-auth-request-user": "u", "x-auth-request-email": "u@example.com"}


@pytest.mark.usefixtures("db_session")
def test_support_contact_rate_limited(db_session, monkeypatch):
    monkeypatch.setenv("SUPPORT_CONTACT_MIN_INTERVAL_SECONDS", "120")

    # Create user and a recent support email log
    user = models.User(email="u@example.com", display_name="u")
    db_session.add(user); db_session.commit(); db_session.refresh(user)

    recent = models.EmailNotificationLog(
        user_id=user.id,
        email_address="support@hindsight-ai.com",
        event_type="support_contact",
        subject="help",
        status="sent",
    )
    recent.created_at = datetime.now(timezone.utc) - timedelta(seconds=30)
    db_session.add(recent); db_session.commit()

    # Dependency override to return our current user
    def _mock_ctx():
        cu = {"id": user.id, "email": user.email, "display_name": user.display_name, "memberships": [], "memberships_by_org": {}}
        return user, cu

    original = app.dependency_overrides.get(get_current_user_context)
    app.dependency_overrides[get_current_user_context] = _mock_ctx
    try:
        client = TestClient(app)
        with patch("core.services.notification_service.NotificationService") as _NS:
            # Should not be called because of rate limit
            r = client.post("/support/contact", json={"message": "help"}, headers=_h())
            assert r.status_code == 429
            assert "retry_after_seconds" in r.json()
    finally:
        if original is not None:
            app.dependency_overrides[get_current_user_context] = original
        else:
            app.dependency_overrides.pop(get_current_user_context, None)

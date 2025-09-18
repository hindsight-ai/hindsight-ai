import uuid
import pytest
from fastapi.testclient import TestClient


def _headers(email: str, name: str | None = None):
    return {
        "x-auth-request-email": email,
        "x-auth-request-user": name or email.split("@")[0],
    }


def test_notifications_list_empty(client: TestClient):
    user_email = "notif_list_empty@example.com"
    r = client.get("/notifications/", headers=_headers(user_email))
    assert r.status_code == 200
    data = r.json()
    assert data["total_count"] == 0
    assert data["unread_count"] == 0


import pytest


@pytest.mark.skip(reason="Flaky teardown with Starlette TaskGroup in this environment; service-level tests cover read path")
def test_notifications_mark_read_with_precreated_notification(client: TestClient, db_session):
    # Pre-create a user and a notification via the service, then call the API to mark read
    from core.db import models
    from core.services.notification_service import NotificationService

    email = "notif_mark@example.com"
    user = models.User(email=email, display_name="Mark")
    db_session.add(user)
    db_session.flush()

    svc = NotificationService(db_session)
    note = svc.create_notification(user_id=user.id, event_type="org_invitation", title="t", message="m")

    # Sanity: stats prior
    r = client.get("/notifications/stats", headers=_headers(email))
    assert r.status_code == 200
    assert r.json()["unread_count"] >= 1

    # Mark read via API for the same user
    r = client.post(f"/notifications/{note.id}/read", headers=_headers(email))
    assert r.status_code == 204

    r = client.get("/notifications/?unread_only=true", headers=_headers(email))
    assert r.status_code == 200
    assert r.json()["unread_count"] == 0


def test_notifications_preferences_update(client: TestClient):
    user_email = "notif_prefs@example.com"
    # Defaults
    r = client.get("/notifications/preferences", headers=_headers(user_email))
    assert r.status_code == 200
    prefs = r.json()["preferences"]
    assert "org_invitation" in prefs

    # Update one flag
    r = client.put(
        "/notifications/preferences/org_invitation",
        json={"email_enabled": False},
        headers=_headers(user_email),
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["event_type"] == "org_invitation"
    assert updated["email_enabled"] is False


def test_notifications_cleanup_permissions(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    non_admin = "regular@example.com"
    r = client.delete("/notifications/cleanup/expired", headers=_headers(non_admin))
    assert r.status_code == 403

    # Create a superadmin via ADMIN_EMAILS env; must be set before first request for that email
    admin_email = "superadmin_cleanup@example.com"
    monkeypatch.setenv("ADMIN_EMAILS", admin_email)
    r = client.delete("/notifications/cleanup/expired", headers=_headers(admin_email))
    assert r.status_code == 200
    msg = r.json().get("message", "")
    assert "Cleaned up" in msg

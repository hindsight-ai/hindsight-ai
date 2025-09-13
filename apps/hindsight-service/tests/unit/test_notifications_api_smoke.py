import uuid
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models


client = TestClient(app)


def _h(user, email):
    return {"x-auth-request-user": user, "x-auth-request-email": email}


def test_notifications_preferences_list_mark_read_and_cleanup(db_session):
    email = f"notif_{uuid.uuid4().hex[:8]}@example.com"

    # Trigger user creation and get default preferences
    r_prefs = client.get("/notifications/preferences", headers=_h("u", email))
    assert r_prefs.status_code == 200
    prefs = r_prefs.json().get("preferences")
    assert isinstance(prefs, dict)

    # Update a preference
    r_up = client.put(
        "/notifications/preferences/org_invitation",
        json={"email_enabled": False},
        headers=_h("u", email),
    )
    assert r_up.status_code == 200
    assert r_up.json().get("event_type") == "org_invitation"

    # Seed a notification directly in DB (avoids response_model issues with SQLAlchemy .metadata attribute)
    user = db_session.query(models.User).filter(models.User.email == email).first()
    import datetime
    from datetime import UTC
    n = models.Notification(
        user_id=user.id,
        event_type="org_invitation",
        title="Hello",
        message="World",
        expires_at=datetime.datetime.now(UTC) + datetime.timedelta(days=30),
    )
    db_session.add(n)
    db_session.commit(); db_session.refresh(n)
    nid = n.id

    # List unread
    r_list = client.get("/notifications/?unread_only=true", headers=_h("u", email))
    assert r_list.status_code == 200
    body = r_list.json()
    assert body["unread_count"] >= 1

    # Mark as read
    r_read = client.post(f"/notifications/{nid}/read", headers=_h("u", email))
    assert r_read.status_code == 204

    # Stats
    r_stats = client.get("/notifications/stats", headers=_h("u", email))
    assert r_stats.status_code == 200
    assert "unread_count" in r_stats.json()

    # Elevate to superadmin and cleanup expired (seed one expired)
    user = db_session.query(models.User).filter(models.User.email == email).first()
    user.is_superadmin = True
    # Create already expired notification directly
    import datetime
    from datetime import UTC
    n = models.Notification(
        user_id=user.id,
        event_type="org_invitation",
        title="Expired",
        message="Expired",
        expires_at=datetime.datetime.now(UTC) - datetime.timedelta(days=1),
    )
    db_session.add(n)
    db_session.commit()

    r_cleanup = client.delete("/notifications/cleanup/expired", headers=_h("u", email))
    assert r_cleanup.status_code == 200

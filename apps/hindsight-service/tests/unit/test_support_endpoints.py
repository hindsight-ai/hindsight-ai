import uuid
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models


client = TestClient(app)


def test_build_info_endpoint_smoke():
    r = client.get("/build-info")
    assert r.status_code == 200
    data = r.json()
    # Basic keys present
    assert data.get("service_name") == "hindsight-service"
    assert "version" in data


def test_support_contact_rate_limit(db_session):
    # Create a user that will hit rate limit
    email = f"rate_{uuid.uuid4().hex}@example.com"
    user = models.User(email=email, display_name="Rate Limited")
    db_session.add(user); db_session.commit(); db_session.refresh(user)

    # Existing support email log triggers rate limit
    log = models.EmailNotificationLog(
        notification_id=None,
        user_id=user.id,
        email_address="support@hindsight-ai.com",
        event_type="support_contact",
        subject="Test",
        status="pending",
    )
    db_session.add(log); db_session.commit()

    r = client.post(
        "/support/contact",
        json={"message": "hello", "frontend": {"version": "test"}},
        headers={"x-auth-request-user": "rate-user", "x-auth-request-email": email},
    )
    # Expect 429 due to rate limit
    assert r.status_code == 429
    body = r.json()
    assert "retry_after_seconds" in body


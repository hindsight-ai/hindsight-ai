from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from core.api.main import app


def _h():
    return {"x-auth-request-user": "user", "x-auth-request-email": "user@example.com"}


def test_build_info_returns_defaults():
    client = TestClient(app)
    r = client.get("/build-info")
    assert r.status_code == 200
    j = r.json()
    assert j.get("service_name") == "hindsight-service"
    assert "version" in j


def test_support_contact_happy_path(monkeypatch):
    client = TestClient(app)
    # Patch NotificationService to avoid real email send
    class _NS:
        def __init__(self, db):
            pass
        def create_email_notification_log(self, **kwargs):
            m = MagicMock()
            m.id = "log-1"
            return m
        async def send_email_notification(self, email_log, template_name: str, template_context: dict):
            return {"success": True}

    with patch("core.services.notification_service.NotificationService", _NS):
        r = client.post(
            "/support/contact",
            json={"message": "help", "frontend": {"version": "1.2.3"}},
            headers=_h(),
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


import uuid
import pytest
pytest.importorskip("pytest_asyncio")

from core.services.notification_service import NotificationService
from core.db import models


class _FakeEmailSvc:
    def __init__(self, *, succeed=True, raise_on_render=False):
        self.succeed = succeed
        self.raise_on_render = raise_on_render
    def render_template(self, name, ctx):
        if self.raise_on_render:
            raise RuntimeError("render fail")
        return "<b>hi</b>", "hi"
    async def send_email(self, *, to_email, subject, html_content, text_content):
        if self.succeed:
            return {"success": True, "provider": "mock", "message_id": "mid"}
        return {"success": False, "error": "boom"}


@pytest.mark.usefixtures("db_session")
@pytest.mark.asyncio
async def test_send_email_notification_success_and_failure(db_session):
    # Prepare log row
    user = models.User(email="n@example.com")
    db_session.add(user); db_session.commit(); db_session.refresh(user)
    svc = NotificationService(db_session, email_service=_FakeEmailSvc(succeed=True))
    log = svc.create_email_notification_log(None, user.id, "u@example.com", "evt", "Subject")
    out = await svc.send_email_notification(log, "welcome", {"x": 1})
    assert out["success"] is True
    # Failure path
    svc2 = NotificationService(db_session, email_service=_FakeEmailSvc(succeed=False))
    log2 = svc2.create_email_notification_log(None, user.id, "u@example.com", "evt", "Subject")
    fail = await svc2.send_email_notification(log2, "welcome", {"x": 1})
    assert fail["success"] is False


@pytest.mark.usefixtures("db_session")
@pytest.mark.asyncio
async def test_send_email_notification_exception_on_render(db_session):
    user = models.User(email="e@example.com")
    db_session.add(user); db_session.commit(); db_session.refresh(user)
    svc = NotificationService(db_session, email_service=_FakeEmailSvc(raise_on_render=True))
    log = svc.create_email_notification_log(None, user.id, "u@example.com", "evt", "Subject")
    out = await svc.send_email_notification(log, "welcome", {"x": 1})
    assert out["success"] is False

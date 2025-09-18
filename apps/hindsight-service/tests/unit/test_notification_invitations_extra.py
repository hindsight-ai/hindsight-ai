import pytest
from core.services.notification_service import NotificationService
from core.db import models


class _EmailOK:
    async def send_email(self, *, to_email, subject, html_content, text_content=None):
        return {"success": True, "message_id": "mid-1"}


@pytest.mark.usefixtures("db_session")
def test_notify_invitation_accepted_email_and_inapp(db_session):
    inviter = models.User(email="inviter@example.com")
    db_session.add(inviter); db_session.commit(); db_session.refresh(inviter)

    svc = NotificationService(db_session, email_service=_EmailOK())
    result = svc.notify_invitation_accepted(
        inviter_user_id=inviter.id,
        inviter_email=inviter.email,
        organization_name="OrgX",
        invitee_email="invitee@example.com",
    )
    # In-app should be created; email log present and status updated by send
    assert result.get("in_app_notification") is not None
    assert result.get("email_log") is not None


@pytest.mark.usefixtures("db_session")
def test_notify_invitation_declined_inapp_only(db_session):
    inviter = models.User(email="inviter2@example.com")
    db_session.add(inviter); db_session.commit(); db_session.refresh(inviter)

    svc = NotificationService(db_session, email_service=_EmailOK())
    result = svc.notify_invitation_declined(
        inviter_user_id=inviter.id,
        inviter_email=inviter.email,
        organization_name="OrgY",
        invitee_email="invitee2@example.com",
    )
    # Default prefs for 'org_invitation_declined' are email_enabled False, in_app True
    assert result.get("in_app_notification") is not None
    assert result.get("email_log") is None


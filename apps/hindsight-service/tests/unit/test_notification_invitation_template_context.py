import uuid
from unittest.mock import MagicMock

from core.services.notification_service import NotificationService, TEMPLATE_ORG_INVITATION
from core.db import models
from core.utils.role_permissions import RoleEnum


def test_notify_organization_invitation_role_is_string(db_session, monkeypatch):
    service = NotificationService(db_session)

    # Capture template context passed to transactional email service
    captured = {}

    fake_email_service = MagicMock()

    async def _fake_send(email_log, template_name, template_context):
        captured['template_name'] = template_name
        captured['context'] = dict(template_context)
        return {"success": True, "message_id": "test"}

    # Intercept NotificationService-level send to capture template context
    service.send_email_notification = _fake_send  # type: ignore
    service.email_service = fake_email_service

    inviter_id = uuid.uuid4()
    # Ensure inviter exists to satisfy FK in email log
    inviter = models.User(id=inviter_id, email="inviter@example.com", display_name="Inviter")
    db_session.add(inviter); db_session.commit(); db_session.refresh(inviter)
    invitation_id = uuid.uuid4()

    service.notify_organization_invitation(
        invitee_user_id=None,
        invitee_email="invitee@example.com",
        inviter_name="Jane Doe",
        inviter_user_id=inviter_id,
        organization_name="DevOrg",
        invitation_id=invitation_id,
        accept_url="https://example.com/accept",
        decline_url="https://example.com/decline",
        role=RoleEnum.viewer,
    )

    assert captured.get('template_name') == TEMPLATE_ORG_INVITATION
    ctx = captured.get('context') or {}
    assert ctx.get('organization_name') == 'DevOrg'
    # Role must be a plain string, not an Enum repr
    assert ctx.get('role') == 'viewer'
    assert 'RoleEnum' not in str(ctx.get('role'))

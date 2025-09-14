import uuid
import pytest

from core.services.notification_service import NotificationService
from core.db import models


@pytest.mark.usefixtures("db_session")
def test_user_preferences_defaults_and_set(db_session):
    u = models.User(email="pref@example.com")
    db_session.add(u); db_session.commit(); db_session.refresh(u)
    svc = NotificationService(db_session)

    prefs = svc.get_user_preferences(u.id)
    assert isinstance(prefs, dict) and "org_invitation" in prefs

    # Update a preference and verify readback
    svc.set_user_preference(u.id, 'org_invitation', email_enabled=False, in_app_enabled=True)
    prefs2 = svc.get_user_preferences(u.id)
    assert prefs2['org_invitation']['email_enabled'] is False


@pytest.mark.usefixtures("db_session")
def test_create_and_list_and_mark_notifications(db_session):
    u = models.User(email="note@example.com")
    db_session.add(u); db_session.commit(); db_session.refresh(u)
    svc = NotificationService(db_session)

    n = svc.create_notification(
        user_id=u.id,
        event_type='org_invitation',
        title='Hello',
        message='World',
        action_url="/x",
        action_text="Go",
        metadata={"k":"v"},
        expires_days=1,
    )
    lst = svc.get_user_notifications(u.id, unread_only=True)
    assert any(x.id == n.id for x in lst)
    assert svc.get_unread_count(u.id) >= 1
    assert svc.mark_notification_read(n.id, u.id) is True
    assert svc.get_unread_count(u.id) == 0

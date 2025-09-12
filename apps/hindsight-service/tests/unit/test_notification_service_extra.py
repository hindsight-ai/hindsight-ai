import uuid
from datetime import datetime, timedelta, UTC

from core.db import models
from core.services.notification_service import NotificationService


def _mk_user(db_session, email="svcuser@example.com"):
    u = models.User(id=uuid.uuid4(), email=email, display_name=email.split("@")[0])
    db_session.add(u)
    db_session.flush()
    return u


def test_preferences_set_and_get(db_session):
    user = _mk_user(db_session)
    svc = NotificationService(db_session)

    # Defaults contain known keys
    prefs = svc.get_user_preferences(user.id)
    assert "org_invitation" in prefs and prefs["org_invitation"]["email_enabled"] is True

    # Update one preference and read back
    svc.set_user_preference(user.id, "org_invitation", email_enabled=False, in_app_enabled=True)
    prefs2 = svc.get_user_preferences(user.id)
    assert prefs2["org_invitation"]["email_enabled"] is False


def test_create_mark_read_and_counts(db_session):
    user = _mk_user(db_session)
    svc = NotificationService(db_session)

    n = svc.create_notification(
        user_id=user.id,
        event_type="org_invitation",
        title="t",
        message="m",
    )
    assert svc.get_unread_count(user.id) == 1

    # Wrong user cannot mark
    other = _mk_user(db_session, email="other@example.com")
    assert svc.mark_notification_read(n.id, other.id) is False
    # Owner can mark
    assert svc.mark_notification_read(n.id, user.id) is True
    assert svc.get_unread_count(user.id) == 0


def test_update_email_status_transitions(db_session):
    user = _mk_user(db_session)
    svc = NotificationService(db_session)

    n = svc.create_notification(user_id=user.id, event_type="org_invitation", title="t", message="m")
    log = svc.create_email_notification_log(
        notification_id=n.id, user_id=user.id, email_address=user.email, event_type="org_invitation", subject="subj"
    )

    assert svc.update_email_status(log.id, "sent", provider_message_id="mid") is True
    # Refresh
    log_ref = db_session.query(models.EmailNotificationLog).get(log.id)
    assert log_ref.sent_at is not None and log_ref.provider_message_id == "mid"

    assert svc.update_email_status(log.id, "delivered") is True
    log_ref = db_session.query(models.EmailNotificationLog).get(log.id)
    assert log_ref.delivered_at is not None

    assert svc.update_email_status(log.id, "bounced", error_message="oops") is True
    log_ref = db_session.query(models.EmailNotificationLog).get(log.id)
    assert log_ref.bounced_at is not None and (log_ref.error_message or "").startswith("oops")


def test_cleanup_expired_notifications(db_session):
    user = _mk_user(db_session)
    svc = NotificationService(db_session)

    # Create one already expired
    expires_at = datetime.now(UTC) - timedelta(days=1)
    n = models.Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        event_type="org_invitation",
        title="x",
        message="y",
        created_at=datetime.now(UTC),
        expires_at=expires_at,
        metadata_json={}
    )
    db_session.add(n)
    db_session.commit()

    cleaned = svc.cleanup_expired_notifications()
    assert cleaned >= 1


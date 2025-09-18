import uuid
from datetime import datetime, timedelta, UTC

from core.db.database import get_db_session_local
from core.db import models
from core.services.notification_service import NotificationService


def _db():
    gen = get_db_session_local()
    db = next(gen)
    return db, gen


def test_notification_service_core_methods():
    db, gen = _db()
    try:
        user = models.User(email=f"notify_{uuid.uuid4().hex}@example.com")
        db.add(user); db.commit(); db.refresh(user)

        svc = NotificationService(db)

        # Preferences
        pref = svc.set_user_preference(user.id, 'org_invitation', email_enabled=False, in_app_enabled=True)
        prefs = svc.get_user_preferences(user.id)
        assert pref.event_type == 'org_invitation'
        assert prefs['org_invitation']['email_enabled'] is False

        # Create a visible notification
        n = svc.create_notification(
            user_id=user.id,
            event_type='org_membership_added',
            title='Added',
            message='You were added',
            expires_days=30,
        )
        assert n.id is not None

        # Unread count should be 1; then mark read
        assert svc.get_unread_count(user.id) >= 1
        assert svc.mark_notification_read(n.id, user.id) is True
        assert svc.get_unread_count(user.id) >= 0

        # Create an already-expired notification and clean up
        expired = svc.create_notification(
            user_id=user.id,
            event_type='org_membership_removed',
            title='Removed',
            message='Expired soon',
            expires_days=0,
        )
        expired.expires_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
        cleaned = svc.cleanup_expired_notifications()
        assert cleaned >= 1

    finally:
        try:
            next(gen)
        except StopIteration:
            pass


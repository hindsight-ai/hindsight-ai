"""
Notification service: thin facade that composes the dispatcher and flow classes.
Preserves the original public API so all callers and tests work unchanged.
"""

import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models
from typing import Any as _Any

# Re-export constants from their canonical location so existing imports continue to work.
from core.services.notifications.constants import (  # noqa: F401
    EVENT_ORG_INVITATION,
    EVENT_ORG_MEMBERSHIP_ADDED,
    EVENT_ORG_MEMBERSHIP_REMOVED,
    EVENT_ORG_ROLE_CHANGED,
    EVENT_ORG_INVITE_ACCEPTED,
    EVENT_ORG_INVITE_DECLINED,
    TEMPLATE_ORG_INVITATION,
    TEMPLATE_MEMBERSHIP_ADDED,
    TEMPLATE_MEMBERSHIP_REMOVED,
    TEMPLATE_ROLE_CHANGED,
    TEMPLATE_SUPPORT_CONTACT,
    TEMPLATE_BETA_ACCESS_INVITATION,
    TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION,
    TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION,
    TEMPLATE_BETA_ACCESS_ACCEPTANCE,
    TEMPLATE_BETA_ACCESS_DENIAL,
)

from core.services.notifications.dispatcher import NotificationDispatcher
from core.services.notifications.org_invitation_flow import OrgInvitationFlow
from core.services.notifications.membership_change_flow import MembershipChangeFlow
from core.services.notifications.beta_access_flow import BetaAccessFlow


class NotificationService:
    """Thin facade: composes NotificationDispatcher + flow classes."""

    def __init__(self, db: Session, email_service: Optional[_Any] = None):
        self.db = db
        if email_service is not None:
            self.email_service = email_service
        else:
            try:
                from core.services import transactional_email_service
                self.email_service = transactional_email_service.get_transactional_email_service()
            except Exception:
                self.email_service = None

        self._dispatcher = NotificationDispatcher(db, self.email_service)
        # Each flow holds a reference to the facade (self) instead of the
        # dispatcher directly so that test patches on
        # `service.send_email_notification` propagate at call time.
        self._org_invitation = OrgInvitationFlow(self, self.email_service)
        self._membership = MembershipChangeFlow(self, self.email_service)
        self._beta_access = BetaAccessFlow(self, self.email_service)

    # ------------------------------------------------------------------ #
    # Dispatcher delegates — preferences                                  #
    # ------------------------------------------------------------------ #

    def get_user_preferences(self, *a, **kw): return self._dispatcher.get_user_preferences(*a, **kw)
    def set_user_preference(self, *a, **kw): return self._dispatcher.set_user_preference(*a, **kw)

    # ------------------------------------------------------------------ #
    # Dispatcher delegates — in-app notifications                         #
    # ------------------------------------------------------------------ #

    def create_notification(self, *a, **kw): return self._dispatcher.create_notification(*a, **kw)
    def get_user_notifications(self, *a, **kw): return self._dispatcher.get_user_notifications(*a, **kw)
    def mark_notification_read(self, *a, **kw): return self._dispatcher.mark_notification_read(*a, **kw)
    def get_unread_count(self, *a, **kw): return self._dispatcher.get_unread_count(*a, **kw)

    # ------------------------------------------------------------------ #
    # Dispatcher delegates — email log management                         #
    # ------------------------------------------------------------------ #

    def create_email_notification_log(self, *a, **kw): return self._dispatcher.create_email_notification_log(*a, **kw)
    def update_email_status(self, *a, **kw): return self._dispatcher.update_email_status(*a, **kw)
    def _safe_update_email_status(self, *a, **kw): return self._dispatcher._safe_update_email_status(*a, **kw)
    def _update_email_status_with_session(self, *a, **kw): return self._dispatcher._update_email_status_with_session(*a, **kw)
    async def send_email_notification(self, *a, **kw): return await self._dispatcher.send_email_notification(*a, **kw)

    # ------------------------------------------------------------------ #
    # Dispatcher delegates — cleanup                                      #
    # ------------------------------------------------------------------ #

    def cleanup_expired_notifications(self, *a, **kw): return self._dispatcher.cleanup_expired_notifications(*a, **kw)

    # ------------------------------------------------------------------ #
    # OrgInvitationFlow delegates                                         #
    # ------------------------------------------------------------------ #

    def notify_organization_invitation(self, *a, **kw): return self._org_invitation.notify_organization_invitation(*a, **kw)
    def notify_invitation_accepted(self, *a, **kw): return self._org_invitation.notify_invitation_accepted(*a, **kw)
    def notify_invitation_declined(self, *a, **kw): return self._org_invitation.notify_invitation_declined(*a, **kw)

    # ------------------------------------------------------------------ #
    # MembershipChangeFlow delegates                                      #
    # ------------------------------------------------------------------ #

    def notify_membership_added(self, *a, **kw): return self._membership.notify_membership_added(*a, **kw)
    def notify_role_changed(self, *a, **kw): return self._membership.notify_role_changed(*a, **kw)
    def notify_membership_removed(self, *a, **kw): return self._membership.notify_membership_removed(*a, **kw)

    # ------------------------------------------------------------------ #
    # BetaAccessFlow delegates                                            #
    # ------------------------------------------------------------------ #

    def notify_beta_access_invitation(self, *a, **kw): return self._beta_access.notify_beta_access_invitation(*a, **kw)
    def notify_beta_access_request_confirmation(self, *a, **kw): return self._beta_access.notify_beta_access_request_confirmation(*a, **kw)
    def notify_beta_access_admin_notification(self, *a, **kw): return self._beta_access.notify_beta_access_admin_notification(*a, **kw)
    def notify_beta_access_acceptance(self, *a, **kw): return self._beta_access.notify_beta_access_acceptance(*a, **kw)
    def notify_beta_access_denial(self, *a, **kw): return self._beta_access.notify_beta_access_denial(*a, **kw)


# Convenience function to get a NotificationService instance
def get_notification_service(db: Session = None) -> NotificationService:
    """
    Get a NotificationService instance with a database session.
    If no session provided, gets one from the dependency.
    """
    if db is None:
        db = next(get_db())
    return NotificationService(db)

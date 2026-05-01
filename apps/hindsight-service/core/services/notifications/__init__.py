"""
notifications sub-package: modular notification flow classes.

Public surface:
    NotificationDispatcher  — persistence + preference management
    OrgInvitationFlow       — org invitation lifecycle
    MembershipChangeFlow    — membership added / role changed / removed
    BetaAccessFlow          — beta access email flows
"""

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

__all__ = [
    # Constants
    "EVENT_ORG_INVITATION",
    "EVENT_ORG_MEMBERSHIP_ADDED",
    "EVENT_ORG_MEMBERSHIP_REMOVED",
    "EVENT_ORG_ROLE_CHANGED",
    "EVENT_ORG_INVITE_ACCEPTED",
    "EVENT_ORG_INVITE_DECLINED",
    "TEMPLATE_ORG_INVITATION",
    "TEMPLATE_MEMBERSHIP_ADDED",
    "TEMPLATE_MEMBERSHIP_REMOVED",
    "TEMPLATE_ROLE_CHANGED",
    "TEMPLATE_SUPPORT_CONTACT",
    "TEMPLATE_BETA_ACCESS_INVITATION",
    "TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION",
    "TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION",
    "TEMPLATE_BETA_ACCESS_ACCEPTANCE",
    "TEMPLATE_BETA_ACCESS_DENIAL",
    # Classes
    "NotificationDispatcher",
    "OrgInvitationFlow",
    "MembershipChangeFlow",
    "BetaAccessFlow",
]

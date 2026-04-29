"""
Event type and template name constants for the notification system.
Single source of truth — imported by flow classes and re-exported from
core.services.notification_service for backward compatibility.
"""

# Event type constants (keep legacy values for test compatibility)
EVENT_ORG_INVITATION = 'org_invitation'
EVENT_ORG_MEMBERSHIP_ADDED = 'org_membership_added'
EVENT_ORG_MEMBERSHIP_REMOVED = 'org_membership_removed'
EVENT_ORG_ROLE_CHANGED = 'org_role_changed'
EVENT_ORG_INVITE_ACCEPTED = 'org_invitation_accepted'
EVENT_ORG_INVITE_DECLINED = 'org_invitation_declined'

# Template name constants (match actual template file names)
TEMPLATE_ORG_INVITATION = 'org_invitation'
TEMPLATE_MEMBERSHIP_ADDED = 'membership_added'
TEMPLATE_MEMBERSHIP_REMOVED = 'membership_removed'
TEMPLATE_ROLE_CHANGED = 'role_changed'
TEMPLATE_SUPPORT_CONTACT = 'support_contact'
TEMPLATE_BETA_ACCESS_INVITATION = 'beta_access_invitation'
TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION = 'beta_access_request_confirmation'
TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION = 'beta_access_admin_notification'
TEMPLATE_BETA_ACCESS_ACCEPTANCE = 'beta_access_acceptance'
TEMPLATE_BETA_ACCESS_DENIAL = 'beta_access_denial'

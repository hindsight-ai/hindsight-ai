"""
OrgInvitationFlow: handles organization invitation notifications
(initial invite, accepted, declined).
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from core.db import models
from core.services.notifications.dispatcher import NotificationDispatcher
from core.services.notifications.constants import (
    EVENT_ORG_INVITATION,
    TEMPLATE_ORG_INVITATION,
)


class OrgInvitationFlow:
    """
    Handles all notification flows for organization invitations.
    """

    def __init__(self, dispatcher: NotificationDispatcher, email_service=None):
        self._dispatcher = dispatcher
        self.email_service = email_service

    def notify_organization_invitation(
        self,
        invitee_user_id: Optional[uuid.UUID],
        invitee_email: str,
        inviter_name: str,
        inviter_user_id: Optional[uuid.UUID],
        organization_name: str,
        invitation_id: uuid.UUID,
        accept_url: str,
        decline_url: str,
        role: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send both in-app and email notifications for organization invitations.

        Returns:
            Dict with 'in_app_notification' and 'email_log' keys if created
        """
        # Check preferences if invitee user exists; otherwise, email-only fallback
        if invitee_user_id is not None:
            preferences = self._dispatcher.get_user_preferences(invitee_user_id)
            org_invite_prefs = preferences.get('org_invitation', {'email_enabled': True, 'in_app_enabled': True})
        else:
            org_invite_prefs = {'email_enabled': True, 'in_app_enabled': False}

        result = {}

        # Create in-app notification if enabled
        if invitee_user_id is not None and org_invite_prefs['in_app_enabled']:
            notification = self._dispatcher.create_notification(
                user_id=invitee_user_id,
                event_type=EVENT_ORG_INVITATION,
                title=f"Invitation to {organization_name}",
                message=f"{inviter_name} has invited you to join {organization_name}.",
                action_url=accept_url,
                action_text="View Invitation",
                metadata={
                    'invitation_id': str(invitation_id),
                    'organization_name': organization_name,
                    'inviter_name': inviter_name,
                    'accept_url': accept_url,
                    'decline_url': decline_url
                }
            )
            result['in_app_notification'] = notification

        # Create email notification log if email enabled
        if org_invite_prefs['email_enabled']:
            # Choose a user_id for logging: invitee if exists, else inviter
            log_user_id = invitee_user_id or inviter_user_id
            email_log = self._dispatcher.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=log_user_id,
                email_address=invitee_email,
                event_type=EVENT_ORG_INVITATION,
                subject=f"You're invited to join {organization_name}"
            )
            result['email_log'] = email_log

            # Build robust inviter identity (always non-empty for template rendering)
            inviter_name_safe = (inviter_name or "").strip()
            inviter_email_safe = ""
            inviter_display = inviter_name_safe

            try:
                if inviter_user_id:
                    inv_user = self._dispatcher.db.query(models.User).filter(
                        models.User.id == inviter_user_id
                    ).first()
                    if inv_user:
                        inv_name = (inv_user.display_name or "").strip()
                        inv_email = (inv_user.email or "").strip()
                        inviter_email_safe = inv_email
                        if inv_name and inv_email:
                            inviter_display = f"{inv_name} ({inv_email})"
                            inviter_name_safe = inv_name
                        elif inv_name:
                            inviter_display = inv_name
                            inviter_name_safe = inv_name
                        elif inv_email:
                            inviter_display = inv_email
                            inviter_name_safe = inv_email
            except Exception:
                # If lookup fails, fall back to passed-in inviter_name
                pass

            if not inviter_name_safe:
                # Absolute fallback to avoid empty placeholders in templates
                inviter_name_safe = "A team member"
                if inviter_display:
                    inviter_name_safe = inviter_display

            # Normalize role for templates
            try:
                from enum import Enum as _Enum
                role_value = role.value if isinstance(role, _Enum) else str(role)
            except Exception:
                role_value = str(role)

            # Send the actual email
            try:
                template_context = {
                    'organization_name': organization_name,
                    'inviter_name': inviter_name_safe,
                    'inviter_display': inviter_display,
                    'inviter_email': inviter_email_safe,
                    'accept_url': accept_url,
                    'decline_url': decline_url,
                    'invitation_id': str(invitation_id),
                    'current_year': datetime.now().year,
                    'role': role_value,
                }

                # Prefer using the async helper so tests can patch `send_email_notification` and
                # receive the template_context. In normal operation this will render and send
                # via the configured transactional email service.
                try:
                    import asyncio
                    send_res = asyncio.run(
                        self._dispatcher.send_email_notification(email_log, TEMPLATE_ORG_INVITATION, template_context)
                    )
                    result['email_result'] = send_res
                except Exception as e:
                    # If the send helper fails, mark email as failed but continue
                    try:
                        self._dispatcher.update_email_status(email_log.id, 'failed', error_message=str(e))
                    except Exception:
                        # best-effort; avoid masking original flow
                        pass

            except Exception as e:
                # Log error but don't fail the entire operation
                self._dispatcher.update_email_status(
                    email_log.id,
                    'failed',
                    error_message=f"Email dispatch error: {str(e)}"
                )

        return result

    def notify_invitation_accepted(
        self,
        inviter_user_id: uuid.UUID,
        inviter_email: str,
        organization_name: str,
        invitee_email: str,
    ) -> Dict[str, Any]:
        prefs = self._dispatcher.get_user_preferences(inviter_user_id).get(
            'org_invitation_accepted', {'email_enabled': True, 'in_app_enabled': True}
        )
        result: Dict[str, Any] = {}
        title = f"Invitation accepted"
        message = f"{invitee_email} accepted your invitation to join {organization_name}."

        if prefs.get('in_app_enabled'):
            n = self._dispatcher.create_notification(
                user_id=inviter_user_id,
                event_type='org_invitation_accepted',
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'invitee_email': invitee_email},
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self._dispatcher.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=inviter_user_id,
                email_address=inviter_email,
                event_type='org_invitation_accepted',
                subject=f"{organization_name}: Invitation accepted"
            )
            result['email_log'] = log
            try:
                import asyncio
                html = (
                    f"<p>{invitee_email} accepted your invitation to join <strong>{organization_name}</strong>.</p>"
                )
                text = f"{invitee_email} accepted your invitation to join {organization_name}."
                send_res = asyncio.run(self.email_service.send_email(
                    to_email=inviter_email,
                    subject=f"{organization_name}: Invitation accepted",
                    html_content=html,
                    text_content=text,
                ))
                if send_res.get('success'):
                    self._dispatcher.update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                else:
                    self._dispatcher.update_email_status(log.id, 'failed', error_message=send_res.get('error'))
            except Exception as e:
                self._dispatcher.update_email_status(log.id, 'failed', error_message=str(e))

        return result

    def notify_invitation_declined(
        self,
        inviter_user_id: uuid.UUID,
        inviter_email: str,
        organization_name: str,
        invitee_email: str,
    ) -> Dict[str, Any]:
        prefs = self._dispatcher.get_user_preferences(inviter_user_id).get(
            'org_invitation_declined', {'email_enabled': False, 'in_app_enabled': True}
        )
        result: Dict[str, Any] = {}
        title = f"Invitation declined"
        message = f"{invitee_email} declined the invitation to join {organization_name}."

        if prefs.get('in_app_enabled'):
            n = self._dispatcher.create_notification(
                user_id=inviter_user_id,
                event_type='org_invitation_declined',
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'invitee_email': invitee_email},
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self._dispatcher.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=inviter_user_id,
                email_address=inviter_email,
                event_type='org_invitation_declined',
                subject=f"{organization_name}: Invitation declined"
            )
            result['email_log'] = log
            try:
                import asyncio
                html = (
                    f"<p>{invitee_email} declined the invitation to join <strong>{organization_name}</strong>.</p>"
                )
                text = f"{invitee_email} declined the invitation to join {organization_name}."
                send_res = asyncio.run(self.email_service.send_email(
                    to_email=inviter_email,
                    subject=f"{organization_name}: Invitation declined",
                    html_content=html,
                    text_content=text,
                ))
                if send_res.get('success'):
                    self._dispatcher.update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                else:
                    self._dispatcher.update_email_status(log.id, 'failed', error_message=send_res.get('error'))
            except Exception as e:
                self._dispatcher.update_email_status(log.id, 'failed', error_message=str(e))

        return result

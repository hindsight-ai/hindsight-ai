"""
BetaAccessFlow: handles beta access notification emails
(invitation, request confirmation, admin notification, acceptance, denial).
"""

import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from core.services.notifications.dispatcher import NotificationDispatcher
from core.services.notifications.constants import (
    TEMPLATE_BETA_ACCESS_INVITATION,
    TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION,
    TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION,
    TEMPLATE_BETA_ACCESS_ACCEPTANCE,
    TEMPLATE_BETA_ACCESS_DENIAL,
)


class BetaAccessFlow:
    """
    Handles all notification flows for beta access requests.
    These methods are email-only (no in-app notifications), so they do not
    use the dispatcher's in-app methods.
    """

    def __init__(self, dispatcher: NotificationDispatcher, email_service=None):
        self._dispatcher = dispatcher
        self.email_service = email_service

    # ------------------------------------------------------------------ #
    # Private helper                                                       #
    # ------------------------------------------------------------------ #

    def _send_direct_email(
        self,
        to_email: str,
        subject: str,
        template_name: str,
        template_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Render a template and send directly (no email log entry).
        Returns a result dict with 'success' and optional 'message_id' / 'error'.
        """
        from inspect import iscoroutinefunction, isawaitable

        result: Dict[str, Any] = {}
        html_content, text_content = self.email_service.render_template(template_name, template_context)

        send_fn = getattr(self.email_service, 'send_email')
        if iscoroutinefunction(send_fn):
            import asyncio
            send_res = asyncio.run(send_fn(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            ))
        else:
            send_res = send_fn(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
            )
            if isawaitable(send_res):
                import asyncio
                send_res = asyncio.run(send_res)

        if send_res.get('success'):
            result['success'] = True
            result['message_id'] = send_res.get('message_id')
        else:
            result['success'] = False
            result['error'] = send_res.get('error', 'Unknown error')

        return result

    # ------------------------------------------------------------------ #
    # Public flow methods                                                  #
    # ------------------------------------------------------------------ #

    def notify_beta_access_invitation(self, user_email: str) -> Dict[str, Any]:
        """Send invitation email to request beta access."""
        result: Dict[str, Any] = {}
        # Skip email notification logging for beta access invitations since no user exists yet
        try:
            try:
                from core.utils.urls import get_app_base_url
                base_url = get_app_base_url()
            except Exception:
                base_url = 'https://app.hindsight.ai'

            request_url = f"{base_url}/beta-access/request"
            result = self._send_direct_email(
                to_email=user_email,
                subject="Request Beta Access to Hindsight AI",
                template_name=TEMPLATE_BETA_ACCESS_INVITATION,
                template_context={'request_url': request_url},
            )
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_request_confirmation(self, user_email: str) -> Dict[str, Any]:
        """Send confirmation email after beta access request."""
        result: Dict[str, Any] = {}
        # Skip email notification logging for beta access confirmations since user may not exist yet
        try:
            result = self._send_direct_email(
                to_email=user_email,
                subject="Beta Access Request Received",
                template_name=TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION,
                template_context={},
            )
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_admin_notification(
        self,
        request_id: uuid.UUID,
        user_email: str,
        review_token: Optional[str],
    ) -> Dict[str, Any]:
        """Send notification to admin with accept/deny links."""
        result: Dict[str, Any] = {}
        # Skip email notification logging for admin notifications
        try:
            from urllib.parse import urlencode
            try:
                from core.utils.urls import get_app_base_url
                base_url = get_app_base_url()
            except Exception:
                base_url = 'https://app.hindsight.ai'

            if review_token:
                accept_qs = urlencode({
                    'beta_review': str(request_id),
                    'beta_decision': 'accepted',
                    'decision': 'accepted',
                    'beta_token': review_token,
                    'token': review_token,
                })
                deny_qs = urlencode({
                    'beta_review': str(request_id),
                    'beta_decision': 'denied',
                    'decision': 'denied',
                    'beta_token': review_token,
                    'token': review_token,
                })
                accept_url = f"{base_url}/login?{accept_qs}"
                deny_url = f"{base_url}/login?{deny_qs}"
            else:
                accept_url = f"{base_url}/beta-access/review/{request_id}?decision=accepted"
                deny_url = f"{base_url}/beta-access/review/{request_id}?decision=denied"

            result = self._send_direct_email(
                to_email='ibarz.jean@gmail.com',
                subject=f"Beta Access Request from {user_email}",
                template_name=TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION,
                template_context={
                    'user_email': user_email,
                    'request_id': str(request_id),
                    'accept_url': accept_url,
                    'deny_url': deny_url,
                    'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'review_token': review_token,
                },
            )
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_acceptance(self, user_email: str) -> Dict[str, Any]:
        """Send acceptance email to user."""
        result: Dict[str, Any] = {}
        # Skip email notification logging for beta access acceptance
        try:
            try:
                from core.utils.urls import get_app_base_url
                base_url = get_app_base_url()
            except Exception:
                base_url = 'https://app.hindsight.ai'

            login_url = f"{base_url}/login"
            result = self._send_direct_email(
                to_email=user_email,
                subject="Beta Access Granted",
                template_name=TEMPLATE_BETA_ACCESS_ACCEPTANCE,
                template_context={'login_url': login_url},
            )
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_denial(self, user_email: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Send denial email to user."""
        result: Dict[str, Any] = {}
        # Skip email notification logging for beta access denial
        try:
            result = self._send_direct_email(
                to_email=user_email,
                subject="Beta Access Request Update",
                template_name=TEMPLATE_BETA_ACCESS_DENIAL,
                template_context={'decision_reason': reason or ''},
            )
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

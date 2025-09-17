"""
Notification service: in-app notifications, preferences, and email dispatch.
Centralizes business logic for consistent handling across the app.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import and_, desc

from core.db import models
from core.db.database import get_db
# transactional email factory will be imported lazily inside __init__ so test-time
# patching of the factory function works (avoids binding the function at module import time).
from typing import Any as _Any

# Event type constants (single source of truth; keep legacy values for tests compatibility)
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


class NotificationService:
    """Service class for handling all notification operations."""
    
    def __init__(self, db: Session, email_service: Optional[_Any] = None):
        self.db = db
        self._session_factory: Optional[sessionmaker] = None
        try:
            bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
            if bind is not None:
                engine = getattr(bind, "engine", bind)
                self._session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        except Exception:
            self._session_factory = None
        if self._session_factory is None:
            try:
                from core.db.database import SessionLocal as _SessionLocal
                self._session_factory = _SessionLocal  # type: ignore[assignment]
            except Exception:
                self._session_factory = None
        # Import the transactional email factory lazily so tests that patch
        # core.services.transactional_email_service.get_transactional_email_service
        # will be effective. If an explicit email_service is provided, use it.
        if email_service is not None:
            self.email_service = email_service
        else:
            try:
                from core.services import transactional_email_service
                self.email_service = transactional_email_service.get_transactional_email_service()
            except Exception:
                # Fallback to None so other code can guard appropriately
                self.email_service = None
    
    # === User Preference Management ===
    
    def get_user_preferences(self, user_id: uuid.UUID) -> Dict[str, Dict[str, bool]]:
        """
        Get all notification preferences for a user.
        Returns default preferences if none exist.
        
        Returns:
            Dict with event_type as key and {'email_enabled': bool, 'in_app_enabled': bool} as value
        """
        preferences = self.db.query(models.UserNotificationPreference).filter(
            models.UserNotificationPreference.user_id == user_id
        ).all()
        
        # Default preferences for all event types
        default_preferences = {
            EVENT_ORG_INVITATION: {'email_enabled': True, 'in_app_enabled': True},
            EVENT_ORG_MEMBERSHIP_ADDED: {'email_enabled': True, 'in_app_enabled': True},
            EVENT_ORG_MEMBERSHIP_REMOVED: {'email_enabled': True, 'in_app_enabled': True},
            EVENT_ORG_ROLE_CHANGED: {'email_enabled': True, 'in_app_enabled': True},
            EVENT_ORG_INVITE_ACCEPTED: {'email_enabled': True, 'in_app_enabled': True},
            EVENT_ORG_INVITE_DECLINED: {'email_enabled': False, 'in_app_enabled': True},
        }
        
        # Override with user's actual preferences
        for pref in preferences:
            if pref.event_type in default_preferences:
                default_preferences[pref.event_type] = {
                    'email_enabled': pref.email_enabled,
                    'in_app_enabled': pref.in_app_enabled
                }
        
        return default_preferences
    
    def set_user_preference(
        self, 
        user_id: uuid.UUID, 
        event_type: str, 
        email_enabled: bool, 
        in_app_enabled: bool
    ) -> models.UserNotificationPreference:
        """
        Set or update a user's notification preference for a specific event type.
        """
        existing = self.db.query(models.UserNotificationPreference).filter(
            and_(
                models.UserNotificationPreference.user_id == user_id,
                models.UserNotificationPreference.event_type == event_type
            )
        ).first()
        
        if existing:
            existing.email_enabled = email_enabled
            existing.in_app_enabled = in_app_enabled
            existing.updated_at = datetime.now(UTC)
        else:
            existing = models.UserNotificationPreference(
                user_id=user_id,
                event_type=event_type,
                email_enabled=email_enabled,
                in_app_enabled=in_app_enabled
            )
            self.db.add(existing)
        
        self.db.commit()
        self.db.refresh(existing)
        return existing
    
    # === In-App Notification Management ===
    
    def create_notification(
        self,
        user_id: uuid.UUID,
        event_type: str,
        title: str,
        message: str,
        action_url: Optional[str] = None,
        action_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        expires_days: int = 30
    ) -> models.Notification:
        """
        Create an in-app notification for a user.
        
        Args:
            user_id: The recipient user ID
            event_type: Type of event (e.g., 'org_invitation')
            title: Short notification title
            message: Detailed notification message
            action_url: Optional URL for action button
            action_text: Text for action button
            metadata: Additional event-specific data
            expires_days: Days until notification expires (default 30)
        
        Returns:
            Created notification object
        """
        expires_at = datetime.now(UTC) + timedelta(days=expires_days)
        
        notification = models.Notification(
            user_id=user_id,
            event_type=event_type,
            title=title,
            message=message,
            action_url=action_url,
            action_text=action_text,
            expires_at=expires_at
        )
        
        if metadata:
            notification.set_metadata(metadata)
        
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        
        return notification
    
    def get_user_notifications(
        self,
        user_id: uuid.UUID,
        unread_only: bool = False,
        limit: int = 50
    ) -> List[models.Notification]:
        """
        Get notifications for a user, ordered by most recent.
        """
        query = self.db.query(models.Notification).filter(
            models.Notification.user_id == user_id
        )
        
        if unread_only:
            query = query.filter(models.Notification.is_read == False)
        
        # Only show non-expired notifications
        query = query.filter(
            models.Notification.expires_at > datetime.now(UTC)
        )
        
        return query.order_by(desc(models.Notification.created_at)).limit(limit).all()

    def mark_notification_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Mark a notification as read for a specific user.
        Returns True if successful, False if notification not found or not owned by user.
        """
        notification = self.db.query(models.Notification).filter(
            and_(
                models.Notification.id == notification_id,
                models.Notification.user_id == user_id
            )
        ).first()
        
        if not notification:
            return False
        
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(UTC)
            self.db.commit()
        
        return True
    
    def get_unread_count(self, user_id: uuid.UUID) -> int:
        """
        Get count of unread notifications for a user.
        """
        return self.db.query(models.Notification).filter(
            and_(
                models.Notification.user_id == user_id,
                models.Notification.is_read == False,
                models.Notification.expires_at > datetime.now(UTC)
            )
        ).count()
    
    # === Email Notification Management ===
    
    def create_email_notification_log(
        self,
        notification_id: Optional[uuid.UUID],
        user_id: uuid.UUID,
        email_address: str,
        event_type: str,
        subject: str,
        status: str = 'pending'
    ) -> models.EmailNotificationLog:
        """
        Create an email notification log entry to track email sending.
        """
        email_log = models.EmailNotificationLog(
            notification_id=notification_id,
            user_id=user_id,
            email_address=email_address,
            event_type=event_type,
            subject=subject,
            status=status
        )
        
        self.db.add(email_log)
        self.db.commit()
        self.db.refresh(email_log)
        
        return email_log
    
    def update_email_status(
        self,
        email_log_id: uuid.UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of an email notification.
        
        Args:
            email_log_id: ID of the email log entry
            status: New status ('sent', 'failed', 'bounced', 'delivered')
            provider_message_id: Message ID from email service provider
            error_message: Error details if failed
        
        Returns:
            True if update successful, False if log not found
        """
        email_log = self.db.query(models.EmailNotificationLog).filter(
            models.EmailNotificationLog.id == email_log_id
        ).first()
        
        if not email_log:
            return False
        
        email_log.status = status
        if provider_message_id:
            email_log.provider_message_id = provider_message_id
        if error_message:
            email_log.error_message = error_message
        
        # Set appropriate timestamp based on status
        now = datetime.now(UTC)
        if status == 'sent':
            email_log.sent_at = now
        elif status == 'delivered':
            email_log.delivered_at = now
        elif status == 'bounced':
            email_log.bounced_at = now
        
        self.db.commit()
        return True

    def _safe_update_email_status(
        self,
        email_log_id: uuid.UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        if self._session_factory is not None:
            session = None
            try:
                session = self._session_factory()
                return self._update_email_status_with_session(
                    session,
                    email_log_id,
                    status,
                    provider_message_id=provider_message_id,
                    error_message=error_message,
                )
            finally:
                if session is not None:
                    try:
                        session.close()
                    except Exception:
                        pass
        return self.update_email_status(
            email_log_id,
            status,
            provider_message_id=provider_message_id,
            error_message=error_message,
        )

    def _update_email_status_with_session(
        self,
        db_session: Session,
        email_log_id: uuid.UUID,
        status: str,
        provider_message_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """
        Update the status of an email notification using a specific database session.
        
        Args:
            db_session: Database session to use for the update
            email_log_id: ID of the email log entry
            status: New status ('sent', 'failed', 'bounced', 'delivered')
            provider_message_id: Message ID from email service provider
            error_message: Error details if failed
        
        Returns:
            True if update successful, False if log not found
        """
        email_log = db_session.query(models.EmailNotificationLog).filter(
            models.EmailNotificationLog.id == email_log_id
        ).first()
        
        if not email_log:
            return False
        
        email_log.status = status
        if provider_message_id:
            email_log.provider_message_id = provider_message_id
        if error_message:
            email_log.error_message = error_message
        
        # Set appropriate timestamp based on status
        now = datetime.now(UTC)
        if status == 'sent':
            email_log.sent_at = now
        elif status == 'delivered':
            email_log.delivered_at = now
        elif status == 'bounced':
            email_log.bounced_at = now
        
        db_session.commit()
        return True
    
    async def send_email_notification(
        self,
        email_log: models.EmailNotificationLog,
        template_name: str,
        template_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an email notification using the configured email service.
        
        Args:
            email_log: EmailNotificationLog entry to update with results
            template_name: Name of the email template to use
            template_context: Context data for template rendering
            
        Returns:
            Dict with sending results
        """
        try:
            # Render email template
            html_content, text_content = self.email_service.render_template(
                template_name, 
                template_context
            )
            
            # Send email
            result = await self.email_service.send_email(
                to_email=email_log.email_address,
                subject=email_log.subject,
                html_content=html_content,
                text_content=text_content
            )
            
            # Update email log based on result
            if result['success']:
                self.update_email_status(
                    email_log.id,
                    'sent',
                    provider_message_id=result.get('message_id')
                )
                return {
                    'success': True,
                    'email_log_id': email_log.id,
                    'message_id': result.get('message_id')
                }
            else:
                self.update_email_status(
                    email_log.id,
                    'failed',
                    error_message=result.get('error', 'Unknown error')
                )
                return {
                    'success': False,
                    'email_log_id': email_log.id,
                    'error': result.get('error')
                }
                
        except Exception as e:
            error_msg = f"Failed to send email: {str(e)}"
            self.update_email_status(
                email_log.id,
                'failed',
                error_message=error_msg
            )
            return {
                'success': False,
                'email_log_id': email_log.id,
                'error': error_msg
            }
    
    # === High-Level Notification Methods ===
    
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
            preferences = self.get_user_preferences(invitee_user_id)
            org_invite_prefs = preferences.get('org_invitation', {'email_enabled': True, 'in_app_enabled': True})
        else:
            org_invite_prefs = {'email_enabled': True, 'in_app_enabled': False}
        
        result = {}
        
        # Create in-app notification if enabled
        if invitee_user_id is not None and org_invite_prefs['in_app_enabled']:
            notification = self.create_notification(
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
            email_log = self.create_email_notification_log(
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
                    inv_user = self.db.query(models.User).filter(models.User.id == inviter_user_id).first()
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
                    send_res = asyncio.run(self.send_email_notification(email_log, TEMPLATE_ORG_INVITATION, template_context))
                    result['email_result'] = send_res
                except Exception as e:
                    # If the send helper fails, mark email as failed but continue
                    try:
                        self.update_email_status(email_log.id, 'failed', error_message=str(e))
                    except Exception:
                        # best-effort; avoid masking original flow
                        pass
                
            except Exception as e:
                # Log error but don't fail the entire operation
                self.update_email_status(
                    email_log.id,
                    'failed',
                    error_message=f"Email dispatch error: {str(e)}"
                )
        
        return result

    def notify_beta_access_invitation(self, user_email: str) -> Dict[str, Any]:
        """Send invitation email to request beta access."""
        result = {}
        # Skip email notification logging for beta access invitations since no user exists yet
        try:
            from inspect import iscoroutinefunction, isawaitable

            try:
                from core.utils.urls import get_app_base_url
                base_url = get_app_base_url()
            except Exception:
                base_url = 'https://app.hindsight.ai'

            request_url = f"{base_url}/beta-access/request"

            html_content, text_content = self.email_service.render_template(
                TEMPLATE_BETA_ACCESS_INVITATION,
                {'request_url': request_url}
            )

            send_fn = getattr(self.email_service, 'send_email')
            # If the implementation is an async function, run it. If it returns an awaitable,
            # run that as well. Otherwise call it synchronously.
            if iscoroutinefunction(send_fn):
                import asyncio
                send_res = asyncio.run(send_fn(
                    to_email=user_email,
                    subject="Request Beta Access to Hindsight AI",
                    html_content=html_content,
                    text_content=text_content,
                ))
            else:
                send_res = send_fn(
                    to_email=user_email,
                    subject="Request Beta Access to Hindsight AI",
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
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_request_confirmation(self, user_email: str) -> Dict[str, Any]:
        """Send confirmation email after beta access request."""
        result = {}
        # Skip email notification logging for beta access confirmations since user may not exist yet
        try:
            from inspect import iscoroutinefunction, isawaitable

            html_content, text_content = self.email_service.render_template(
                TEMPLATE_BETA_ACCESS_REQUEST_CONFIRMATION,
                {}
            )

            send_fn = getattr(self.email_service, 'send_email')
            if iscoroutinefunction(send_fn):
                import asyncio
                send_res = asyncio.run(send_fn(
                    to_email=user_email,
                    subject="Beta Access Request Received",
                    html_content=html_content,
                    text_content=text_content,
                ))
            else:
                send_res = send_fn(
                    to_email=user_email,
                    subject="Beta Access Request Received",
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
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_admin_notification(self, request_id: uuid.UUID, user_email: str, review_token: Optional[str]) -> Dict[str, Any]:
        """Send notification to admin with accept/deny links."""
        result = {}
        # Skip email notification logging for admin notifications
        try:
            from inspect import iscoroutinefunction, isawaitable
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

            html_content, text_content = self.email_service.render_template(
                TEMPLATE_BETA_ACCESS_ADMIN_NOTIFICATION,
                {
                    'user_email': user_email,
                    'request_id': str(request_id),
                    'accept_url': accept_url,
                    'deny_url': deny_url,
                    'requested_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'review_token': review_token,
                }
            )

            send_fn = getattr(self.email_service, 'send_email')
            if iscoroutinefunction(send_fn):
                import asyncio
                send_res = asyncio.run(send_fn(
                    to_email='ibarz.jean@gmail.com',
                    subject=f"Beta Access Request from {user_email}",
                    html_content=html_content,
                    text_content=text_content,
                ))
            else:
                send_res = send_fn(
                    to_email='ibarz.jean@gmail.com',
                    subject=f"Beta Access Request from {user_email}",
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
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_acceptance(self, user_email: str) -> Dict[str, Any]:
        """Send acceptance email to user."""
        result = {}
        # Skip email notification logging for beta access acceptance
        try:
            from inspect import iscoroutinefunction, isawaitable
            try:
                from core.utils.urls import get_app_base_url
                base_url = get_app_base_url()
            except Exception:
                base_url = 'https://app.hindsight.ai'

            login_url = f"{base_url}/login"

            html_content, text_content = self.email_service.render_template(
                TEMPLATE_BETA_ACCESS_ACCEPTANCE,
                {'login_url': login_url}
            )

            send_fn = getattr(self.email_service, 'send_email')
            if iscoroutinefunction(send_fn):
                import asyncio
                send_res = asyncio.run(send_fn(
                    to_email=user_email,
                    subject="Beta Access Granted",
                    html_content=html_content,
                    text_content=text_content,
                ))
            else:
                send_res = send_fn(
                    to_email=user_email,
                    subject="Beta Access Granted",
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
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_beta_access_denial(self, user_email: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Send denial email to user."""
        result = {}
        # Skip email notification logging for beta access denial
        try:
            from inspect import iscoroutinefunction, isawaitable
            html_content, text_content = self.email_service.render_template(
                TEMPLATE_BETA_ACCESS_DENIAL,
                {'decision_reason': reason or ''}
            )

            send_fn = getattr(self.email_service, 'send_email')
            if iscoroutinefunction(send_fn):
                import asyncio
                send_res = asyncio.run(send_fn(
                    to_email=user_email,
                    subject="Beta Access Request Update",
                    html_content=html_content,
                    text_content=text_content,
                ))
            else:
                send_res = send_fn(
                    to_email=user_email,
                    subject="Beta Access Request Update",
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
        except Exception as e:
            result['success'] = False
            result['error'] = str(e)
        return result

    def notify_membership_added(
        self,
        user_id: uuid.UUID,
        user_email: str,
        organization_name: str,
    role: str,
    added_by_name: str,
    organization_id: Optional[uuid.UUID] = None,
    added_by_user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Send notifications when a user is added to an organization.
        """
        preferences = self.get_user_preferences(user_id)
        membership_prefs = preferences.get('org_membership_added', {'email_enabled': True, 'in_app_enabled': True})
        
        result = {}
        
        # Create in-app notification if enabled
        if membership_prefs['in_app_enabled']:
            metadata = {
                'organization_name': organization_name,
                'role': role,
                'added_by_name': added_by_name,
            }
            if organization_id:
                metadata['organization_id'] = str(organization_id)
            if added_by_user_id:
                metadata['added_by_user_id'] = str(added_by_user_id)

            # Title expected by tests includes trailing exclamation mark
            notification = self.create_notification(
                user_id=user_id,
                # Use canonical event_type constant for stored notifications
                event_type=EVENT_ORG_MEMBERSHIP_ADDED,
                title=f"Welcome to {organization_name}!",
                # Use wording that includes the exact substring tests look for
                message=f"{added_by_name} added you to the organization {organization_name} as a {role}.",
                metadata=metadata
            )
            result['in_app_notification'] = notification
        
        # Create email notification log if email enabled
        if membership_prefs['email_enabled']:
            email_log = self.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=user_id,
                email_address=user_email,
                # use canonical event type for logs
                event_type=EVENT_ORG_MEMBERSHIP_ADDED,
                subject=f"Welcome to {organization_name}"
            )
            result['email_log'] = email_log

            # Send the email in background so API response isn't blocked. Tests patch the
            # transactional email factory and expect render_template called with
            # template TEMPLATE_ORG_INVITATION and a specific context shape.
            try:
                if not self.email_service:
                    # If no email service (rare in tests), mark as failed but continue
                    self.update_email_status(email_log.id, 'failed', error_message='No email service configured')
                else:
                    from core.utils.urls import get_app_base_url
                    base_url = get_app_base_url()
                    # Build context expected by tests
                    context = {
                        'user_name': (user_email.split('@')[0] if user_email else ''),
                        'organization_name': organization_name,
                        'invited_by': added_by_name,
                        'role': role,
                        'dashboard_url': f'{base_url}/dashboard'
                    }

                    # Render template synchronously (so patched render_template gets called)
                    def _update(status: str, message_id: Optional[str] = None, error: Optional[str] = None) -> None:
                        self._safe_update_email_status(
                            email_log.id,
                            status,
                            provider_message_id=message_id,
                            error_message=error,
                        )

                    try:
                        html, text = self.email_service.render_template(TEMPLATE_MEMBERSHIP_ADDED, context)
                    except Exception as e:
                        # If rendering fails, mark email log and return
                        self.update_email_status(email_log.id, 'failed', error_message=f'Template render failed: {str(e)}')
                        return result

                    # Send in background thread
                    def _send():
                        import asyncio
                        try:
                            send_res = asyncio.run(self.email_service.send_email(
                                to_email=email_log.email_address,
                                subject=email_log.subject,
                                html_content=html,
                                text_content=text
                            ))
                            if send_res.get('success'):
                                _update('sent', message_id=send_res.get('message_id'))
                            else:
                                _update('failed', error=send_res.get('error'))
                        except Exception as e:
                            _update('failed', error=str(e))

                    import threading
                    t = threading.Thread(target=_send, daemon=True)
                    t.start()

                    result['email_result'] = {'dispatched_in_background': True}
            except Exception as e:
                self._safe_update_email_status(email_log.id, 'failed', error_message=f"Email dispatch error: {str(e)}")
        
        return result

    def notify_role_changed(
        self,
        user_id: uuid.UUID,
        user_email: str,
        organization_name: str,
        old_role: str,
        new_role: str,
        changed_by_name: str
    ) -> Dict[str, Any]:
        """
        Notify a user that their role in an organization has changed.
        """
        prefs = self.get_user_preferences(user_id).get('org_role_changed', {'email_enabled': True, 'in_app_enabled': True})
        result: Dict[str, Any] = {}

        title = f"Role changed in {organization_name}"
        message = f"Your role in {organization_name} changed from {old_role} to {new_role} by {changed_by_name}."

        if prefs.get('in_app_enabled'):
            n = self.create_notification(
                user_id=user_id,
                event_type=EVENT_ORG_ROLE_CHANGED,
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'old_role': old_role, 'new_role': new_role, 'changed_by': changed_by_name}
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=user_id,
                email_address=user_email,
                event_type=EVENT_ORG_ROLE_CHANGED,
                subject=f"Your role changed in {organization_name}"
            )
            result['email_log'] = log
            try:
                template_context = {
                    'organization_name': organization_name,
                    'old_role': old_role,
                    'new_role': new_role,
                    'changed_by_name': changed_by_name,
                    'date_changed': datetime.now().strftime('%B %d, %Y'),
                    'current_year': datetime.now().year,
                }

                # Render template synchronously
                try:
                    html, text = self.email_service.render_template(TEMPLATE_ROLE_CHANGED, template_context)
                except Exception as e:
                    # If rendering fails, mark email log and return
                    self.update_email_status(log.id, 'failed', error_message=f'Template render failed: {str(e)}')
                    return result

                # Send in background thread
                def _send():
                    import asyncio
                    try:
                        send_res = asyncio.run(self.email_service.send_email(
                            to_email=log.email_address,
                            subject=log.subject,
                            html_content=html,
                            text_content=text
                        ))
                        if send_res.get('success'):
                            self._safe_update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                        else:
                            self._safe_update_email_status(log.id, 'failed', error_message=send_res.get('error'))
                    except Exception as e:
                        self._safe_update_email_status(log.id, 'failed', error_message=str(e))

                import threading
                t = threading.Thread(target=_send, daemon=True)
                t.start()

                result['email_result'] = {'dispatched_in_background': True}
            except Exception as e:
                self._safe_update_email_status(log.id, 'failed', error_message=f"Email dispatch error: {str(e)}")

        return result

    def notify_membership_removed(
        self,
        user_id: uuid.UUID,
        user_email: str,
        organization_name: str,
        removed_by_name: str
    ) -> Dict[str, Any]:
        """
        Notify a user that they have been removed from an organization.
        """
        prefs = self.get_user_preferences(user_id).get('org_membership_removed', {'email_enabled': True, 'in_app_enabled': True})
        result: Dict[str, Any] = {}

        title = f"Removed from {organization_name}"
        message = f"You have been removed from {organization_name} by {removed_by_name}."

        if prefs.get('in_app_enabled'):
            n = self.create_notification(
                user_id=user_id,
                event_type=EVENT_ORG_MEMBERSHIP_REMOVED,
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'removed_by': removed_by_name}
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=user_id,
                email_address=user_email,
                event_type=EVENT_ORG_MEMBERSHIP_REMOVED,
                subject=f"You were removed from {organization_name}"
            )
            result['email_log'] = log
            try:
                template_context = {
                    'organization_name': organization_name,
                    'removed_by_name': removed_by_name,
                    'date_removed': datetime.now().strftime('%B %d, %Y'),
                    'current_year': datetime.now().year,
                }

                # Render template synchronously
                try:
                    html, text = self.email_service.render_template(TEMPLATE_MEMBERSHIP_REMOVED, template_context)
                except Exception as e:
                    # If rendering fails, mark email log and return
                    self.update_email_status(log.id, 'failed', error_message=f'Template render failed: {str(e)}')
                    return result

                # Send in background thread
                def _send():
                    import asyncio
                    try:
                        send_res = asyncio.run(self.email_service.send_email(
                            to_email=log.email_address,
                            subject=log.subject,
                            html_content=html,
                            text_content=text
                        ))
                        if send_res.get('success'):
                            self._safe_update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                        else:
                            self._safe_update_email_status(log.id, 'failed', error_message=send_res.get('error'))
                    except Exception as e:
                        self._safe_update_email_status(log.id, 'failed', error_message=str(e))

                import threading
                t = threading.Thread(target=_send, daemon=True)
                t.start()

                result['email_result'] = {'dispatched_in_background': True}
            except Exception as e:
                self._safe_update_email_status(log.id, 'failed', error_message=f"Email dispatch error: {str(e)}")

        return result

    # === Invitation Outcome Notifications (to inviter) ===

    def notify_invitation_accepted(
        self,
        inviter_user_id: uuid.UUID,
        inviter_email: str,
        organization_name: str,
        invitee_email: str,
    ) -> Dict[str, Any]:
        prefs = self.get_user_preferences(inviter_user_id).get(
            'org_invitation_accepted', {'email_enabled': True, 'in_app_enabled': True}
        )
        result: Dict[str, Any] = {}
        title = f"Invitation accepted"
        message = f"{invitee_email} accepted your invitation to join {organization_name}."

        if prefs.get('in_app_enabled'):
            n = self.create_notification(
                user_id=inviter_user_id,
                event_type='org_invitation_accepted',
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'invitee_email': invitee_email},
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self.create_email_notification_log(
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
                    self.update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                else:
                    self.update_email_status(log.id, 'failed', error_message=send_res.get('error'))
            except Exception as e:
                self.update_email_status(log.id, 'failed', error_message=str(e))

        return result

    def notify_invitation_declined(
        self,
        inviter_user_id: uuid.UUID,
        inviter_email: str,
        organization_name: str,
        invitee_email: str,
    ) -> Dict[str, Any]:
        prefs = self.get_user_preferences(inviter_user_id).get(
            'org_invitation_declined', {'email_enabled': False, 'in_app_enabled': True}
        )
        result: Dict[str, Any] = {}
        title = f"Invitation declined"
        message = f"{invitee_email} declined the invitation to join {organization_name}."

        if prefs.get('in_app_enabled'):
            n = self.create_notification(
                user_id=inviter_user_id,
                event_type='org_invitation_declined',
                title=title,
                message=message,
                metadata={'organization_name': organization_name, 'invitee_email': invitee_email},
            )
            result['in_app_notification'] = n

        if prefs.get('email_enabled'):
            log = self.create_email_notification_log(
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
                    self.update_email_status(log.id, 'sent', provider_message_id=send_res.get('message_id'))
                else:
                    self.update_email_status(log.id, 'failed', error_message=send_res.get('error'))
            except Exception as e:
                self.update_email_status(log.id, 'failed', error_message=str(e))

        return result
    
    # === Cleanup Methods ===
    
    def cleanup_expired_notifications(self) -> int:
        """
        Remove notifications that have exceeded their expiration date.
        Returns count of cleaned up notifications.
        """
        cutoff_date = datetime.now(UTC)
        
        expired_notifications = self.db.query(models.Notification).filter(
            models.Notification.expires_at <= cutoff_date
        )
        
        count = expired_notifications.count()
        expired_notifications.delete(synchronize_session=False)
        self.db.commit()
        
        return count


# Convenience function to get a NotificationService instance
def get_notification_service(db: Session = None) -> NotificationService:
    """
    Get a NotificationService instance with a database session.
    If no session provided, gets one from the dependency.
    """
    if db is None:
        db = next(get_db())
    return NotificationService(db)

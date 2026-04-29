"""
NotificationDispatcher: in-app notification persistence, user preferences,
and email log management.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import and_, desc

from core.db import models


class NotificationDispatcher:
    """
    Handles persistence-side notification operations: user preferences,
    in-app notification CRUD, and email notification log management.
    """

    def __init__(self, db: Session, email_service=None):
        self.db = db
        self.email_service = email_service

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

    # === User Preference Management ===

    def get_user_preferences(self, user_id: uuid.UUID) -> Dict[str, Dict[str, bool]]:
        """
        Get all notification preferences for a user.
        Returns default preferences if none exist.

        Returns:
            Dict with event_type as key and {'email_enabled': bool, 'in_app_enabled': bool} as value
        """
        from core.services.notifications.constants import (
            EVENT_ORG_INVITATION,
            EVENT_ORG_MEMBERSHIP_ADDED,
            EVENT_ORG_MEMBERSHIP_REMOVED,
            EVENT_ORG_ROLE_CHANGED,
            EVENT_ORG_INVITE_ACCEPTED,
            EVENT_ORG_INVITE_DECLINED,
        )

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

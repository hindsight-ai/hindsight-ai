"""
Notification Service

This service handles all notification operations including:
- Creating in-app notifications
- Sending email notifications via SMTP
- Managing user notification preferences
- Tracking email delivery status

Business logic is centralized here to ensure consistency across all notification triggers.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from core.db import models
from core.db.database import get_db
from core.services.transactional_email_service import get_transactional_email_service, TransactionalEmailService


class NotificationService:
    """Service class for handling all notification operations."""
    
    def __init__(self, db: Session, email_service: Optional[TransactionalEmailService] = None):
        self.db = db
        self.email_service = email_service or get_transactional_email_service()
    
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
            'org_invitation': {'email_enabled': True, 'in_app_enabled': True},
            'org_membership_added': {'email_enabled': True, 'in_app_enabled': True},
            'org_membership_removed': {'email_enabled': True, 'in_app_enabled': True},
            'org_role_changed': {'email_enabled': True, 'in_app_enabled': True},
            'org_invitation_accepted': {'email_enabled': True, 'in_app_enabled': True},
            'org_invitation_declined': {'email_enabled': False, 'in_app_enabled': True},
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
        invitee_user_id: uuid.UUID,
        invitee_email: str,
        inviter_name: str,
        organization_name: str,
        invitation_id: uuid.UUID,
        accept_url: str,
        decline_url: str
    ) -> Dict[str, Any]:
        """
        Send both in-app and email notifications for organization invitations.
        
        Returns:
            Dict with 'in_app_notification' and 'email_log' keys if created
        """
        # Check user preferences
        preferences = self.get_user_preferences(invitee_user_id)
        org_invite_prefs = preferences.get('org_invitation', {'email_enabled': True, 'in_app_enabled': True})
        
        result = {}
        
        # Create in-app notification if enabled
        if org_invite_prefs['in_app_enabled']:
            notification = self.create_notification(
                user_id=invitee_user_id,
                event_type='org_invitation',
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
            email_log = self.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=invitee_user_id,
                email_address=invitee_email,
                event_type='org_invitation',
                subject=f"You're invited to join {organization_name}"
            )
            result['email_log'] = email_log
            
            # Send the actual email
            try:
                import asyncio
                template_context = {
                    'organization_name': organization_name,
                    'inviter_name': inviter_name,
                    'accept_url': accept_url,
                    'decline_url': decline_url,
                    'invitation_id': str(invitation_id),
                    'current_year': datetime.now().year
                }
                
                # Send email asynchronously
                email_result = asyncio.run(self.send_email_notification(
                    email_log,
                    'organization_invitation',
                    template_context
                ))
                result['email_result'] = email_result
                
            except Exception as e:
                # Log error but don't fail the entire operation
                self.update_email_status(
                    email_log.id,
                    'failed',
                    error_message=f"Email sending failed: {str(e)}"
                )
        
        return result
    
    def notify_membership_added(
        self,
        user_id: uuid.UUID,
        user_email: str,
        organization_name: str,
        role: str,
        added_by_name: str
    ) -> Dict[str, Any]:
        """
        Send notifications when a user is added to an organization.
        """
        preferences = self.get_user_preferences(user_id)
        membership_prefs = preferences.get('org_membership_added', {'email_enabled': True, 'in_app_enabled': True})
        
        result = {}
        
        # Create in-app notification if enabled
        if membership_prefs['in_app_enabled']:
            notification = self.create_notification(
                user_id=user_id,
                event_type='org_membership_added',
                title=f"Added to {organization_name}",
                message=f"You have been added to {organization_name} as a {role} by {added_by_name}.",
                metadata={
                    'organization_name': organization_name,
                    'role': role,
                    'added_by_name': added_by_name
                }
            )
            result['in_app_notification'] = notification
        
        # Create email notification log if email enabled
        if membership_prefs['email_enabled']:
            email_log = self.create_email_notification_log(
                notification_id=result.get('in_app_notification', {}).id if 'in_app_notification' in result else None,
                user_id=user_id,
                email_address=user_email,
                event_type='org_membership_added',
                subject=f"Welcome to {organization_name}"
            )
            result['email_log'] = email_log
            
            # Send the actual email
            try:
                import asyncio
                template_context = {
                    'organization_name': organization_name,
                    'role': role,
                    'added_by_name': added_by_name,
                    'date_added': datetime.now().strftime('%B %d, %Y'),
                    'current_year': datetime.now().year,
                    'dashboard_url': 'https://hindsight-ai.com/dashboard',  # TODO: Make configurable
                    'organization_url': 'https://hindsight-ai.com/organizations'  # TODO: Make configurable
                }
                
                # Send email asynchronously
                email_result = asyncio.run(self.send_email_notification(
                    email_log,
                    'membership_added',
                    template_context
                ))
                result['email_result'] = email_result
                
            except Exception as e:
                # Log error but don't fail the entire operation
                self.update_email_status(
                    email_log.id,
                    'failed',
                    error_message=f"Email sending failed: {str(e)}"
                )
        
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

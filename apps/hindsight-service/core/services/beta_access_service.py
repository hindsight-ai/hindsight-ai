"""
Beta access service: handles beta access requests, reviews, and notifications.
"""

import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from core.db import models
from core.db.repositories import beta_access as beta_repo
from core.services.notification_service import NotificationService
from core.audit import log as audit_log
from core.audit import AuditAction, AuditStatus


class BetaAccessService:
    """Service class for handling beta access operations."""

    def __init__(self, db: Session, notification_service: Optional[NotificationService] = None):
        self.db = db
        self.notification_service = notification_service or NotificationService(db)

    def request_beta_access(self, user_id: Optional[uuid.UUID], email: str) -> Dict[str, Any]:
        """Request beta access. Creates a request if not already pending/accepted."""
        # Check if user already has a request
        existing_request = beta_repo.get_beta_access_request_by_email(self.db, email)
        if existing_request and existing_request.status in ['pending', 'accepted']:
            return {'success': False, 'message': 'Request already exists or accepted.'}

        # Create new request
        request = beta_repo.create_beta_access_request(self.db, user_id, email)

        # Send confirmation email to user
        self._send_request_confirmation_email(email)

        # Send notification to admin
        self._send_admin_notification_email(request.id, email)

        # Audit log
        audit_log(self.db, action=AuditAction.BETA_ACCESS_REQUEST, status=AuditStatus.SUCCESS,
                  target_type='beta_access_request', target_id=request.id, actor_user_id=user_id)

        return {'success': True, 'request_id': request.id}

    def review_beta_access_request(self, request_id: uuid.UUID, decision: str, reviewer_email: str,
                                   reason: Optional[str] = None, actor_user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Review a beta access request: accept or deny."""
        if decision not in ['accepted', 'denied']:
            return {'success': False, 'message': 'Invalid decision.'}

        request = beta_repo.update_beta_access_request_status(
            self.db, request_id, decision, reviewer_email, reason
        )
        if not request:
            return {'success': False, 'message': 'Request not found.'}

        # Update user status if accepted
        if decision == 'accepted' and request.user_id:
            beta_repo.update_user_beta_access_status(self.db, request.user_id, 'accepted')
            self._send_acceptance_email(request.email)
        elif decision == 'denied':
            if request.user_id:
                beta_repo.update_user_beta_access_status(self.db, request.user_id, 'denied')
            self._send_denial_email(request.email, reason)

        # Audit log
        audit_log(self.db, action=AuditAction.BETA_ACCESS_REVIEW, status=AuditStatus.SUCCESS,
                  target_type='beta_access_request', target_id=request_id, actor_user_id=actor_user_id,
                  metadata={'decision': decision, 'reviewer_email': reviewer_email})

        return {'success': True}

    def get_beta_access_status(self, user_id: uuid.UUID) -> Optional[str]:
        """Get beta access status for a user."""
        return beta_repo.get_user_beta_access_status(self.db, user_id)

    def get_pending_requests(self, skip: int = 0, limit: int = 100):
        """Get pending beta access requests."""
        return beta_repo.get_beta_access_requests_by_status(self.db, 'pending', skip, limit)

    def _send_request_confirmation_email(self, email: str):
        """Send confirmation email to user after request."""
        self.notification_service.notify_beta_access_request_confirmation(email)

    def _send_admin_notification_email(self, request_id: uuid.UUID, email: str):
        """Send notification to admin with accept/deny links."""
        self.notification_service.notify_beta_access_admin_notification(request_id, email)

    def _send_acceptance_email(self, email: str):
        """Send acceptance email to user."""
        self.notification_service.notify_beta_access_acceptance(email)

    def _send_denial_email(self, email: str, reason: Optional[str]):
        """Send denial email to user."""
        self.notification_service.notify_beta_access_denial(email, reason)

"""
Beta access service: handles beta access requests, reviews, and notifications.
"""

import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
import secrets
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

        # Update the user beta access status to pending when we have a user account
        if user_id:
            beta_repo.update_user_beta_access_status(self.db, user_id, 'pending')
        else:
            self._update_user_status_by_email(email, 'pending')

        # Send confirmation email to user
        self._send_request_confirmation_email(email)

        # Send notification to admin
        self._send_admin_notification_email(request.id, email, request.review_token)

        # Audit log (only for authenticated users)
        if user_id is not None:
            audit_log(self.db, action=AuditAction.BETA_ACCESS_REQUEST, status=AuditStatus.SUCCESS,
                      target_type='beta_access_request', target_id=request.id, actor_user_id=user_id)

        return {'success': True, 'request_id': request.id}

    def review_beta_access_request(self, request_id: uuid.UUID, decision: str, reviewer_email: str,
                                   reason: Optional[str] = None, actor_user_id: Optional[uuid.UUID] = None) -> Dict[str, Any]:
        """Review a beta access request: accept or deny."""
        decision = decision.lower()
        if decision not in ['accepted', 'denied']:
            return {'success': False, 'message': 'Invalid decision.'}

        request = beta_repo.get_beta_access_request(self.db, request_id)
        if not request:
            return {'success': False, 'message': 'Request not found.'}
        if request.status != 'pending':
            if request.status == decision:
                return self._build_already_processed_response(request)
            return {'success': False, 'message': f"Request already {request.status}."}

        return self._finalize_review(request, decision, reviewer_email, reason, actor_user_id, via_token=False)

    def review_beta_access_request_with_token(self, request_id: uuid.UUID, token: str, decision: str) -> Dict[str, Any]:
        """Allow admin to review a request via emailed token links."""
        decision = decision.lower()
        if decision not in ['accepted', 'denied']:
            return {'success': False, 'message': 'Invalid decision.'}

        request = beta_repo.get_beta_access_request(self.db, request_id)
        if not request:
            return {'success': False, 'message': 'Request not found.'}
        if request.status != 'pending':
            if request.status == decision:
                return self._build_already_processed_response(request)
            return {'success': False, 'message': f"Request already {request.status}."}

        if not request.review_token or not secrets.compare_digest(request.review_token, token):
            return {'success': False, 'message': 'Invalid or already used review token.'}
        if request.token_expires_at and datetime.now(timezone.utc) > request.token_expires_at:
            return {'success': False, 'message': 'Review token expired.'}

        return self._finalize_review(request, decision, 'beta-access-token', None, None, via_token=True)

    def get_beta_access_status(self, user_id: uuid.UUID) -> Optional[str]:
        """Get beta access status for a user."""
        return beta_repo.get_user_beta_access_status(self.db, user_id)

    def get_pending_requests(self, skip: int = 0, limit: int = 100):
        """Get pending beta access requests."""
        return beta_repo.get_beta_access_requests_by_status(self.db, 'pending', skip, limit)

    def _send_request_confirmation_email(self, email: str):
        """Send confirmation email to user after request."""
        self.notification_service.notify_beta_access_request_confirmation(email)

    def _send_admin_notification_email(self, request_id: uuid.UUID, email: str, review_token: Optional[str]):
        """Send notification to admin with accept/deny links."""
        if review_token:
            self.notification_service.notify_beta_access_admin_notification(request_id, email, review_token)
        else:
            self.notification_service.notify_beta_access_admin_notification(request_id, email, None)

    def _send_acceptance_email(self, email: str):
        """Send acceptance email to user."""
        self.notification_service.notify_beta_access_acceptance(email)

    def _send_denial_email(self, email: str, reason: Optional[str]):
        """Send denial email to user."""
        self.notification_service.notify_beta_access_denial(email, reason)

    def _finalize_review(
        self,
        request: models.BetaAccessRequest,
        decision: str,
        reviewer_email: str,
        reason: Optional[str],
        actor_user_id: Optional[uuid.UUID],
        via_token: bool = False,
    ) -> Dict[str, Any]:
        updated = beta_repo.update_beta_access_request_status(
            self.db,
            request.id,
            decision,
            reviewer_email,
            reason,
        )
        if not updated:
            return {'success': False, 'message': 'Request not found.'}

        if decision == 'accepted':
            if updated.user_id:
                beta_repo.update_user_beta_access_status(self.db, updated.user_id, 'accepted')
            else:
                self._update_user_status_by_email(updated.email, 'accepted')
            self._send_acceptance_email(updated.email)
            message = f"Beta access approved for {updated.email}."
        else:
            if updated.user_id:
                beta_repo.update_user_beta_access_status(self.db, updated.user_id, 'denied')
            else:
                self._update_user_status_by_email(updated.email, 'denied')
            self._send_denial_email(updated.email, reason)
            message = f"Beta access request denied for {updated.email}."

        metadata = {'decision': decision, 'reviewer_email': reviewer_email}
        if via_token:
            metadata['via_token'] = True

        log_actor_id = actor_user_id if actor_user_id is not None else updated.user_id
        if log_actor_id is not None:
            audit_log(
                self.db,
                action=AuditAction.BETA_ACCESS_REVIEW,
                status=AuditStatus.SUCCESS,
                target_type='beta_access_request',
                target_id=request.id,
                actor_user_id=log_actor_id,
                metadata=metadata,
            )

        return self._build_review_success_result(updated, decision, message)

    def _update_user_status_by_email(self, email: str, status: str) -> bool:
        user = self.db.query(models.User).filter(models.User.email == email).first()
        if not user:
            return False
        beta_repo.update_user_beta_access_status(self.db, user.id, status)
        return True

    def _build_already_processed_response(self, request: models.BetaAccessRequest) -> Dict[str, Any]:
        status = request.status
        if status == 'accepted':
            message = f"Beta access already granted for {request.email}."
        elif status == 'denied':
            message = f"Beta access request already denied for {request.email}."
        else:
            message = f"Request already {status}."
        return {
            'success': True,
            'request_id': request.id,
            'message': message,
            'request_email': request.email,
            'decision': status,
            'already_processed': True,
        }

    def _build_review_success_result(self, request: models.BetaAccessRequest, decision: str, message: str) -> Dict[str, Any]:
        return {
            'success': True,
            'request_id': request.id,
            'message': message,
            'request_email': request.email,
            'decision': decision,
            'already_processed': False,
        }

"""
Unit tests for beta access functionality.

Tests beta access service, repository, API endpoints, and email notifications.
"""
import uuid
import asyncio
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock, ANY
from sqlalchemy.orm import Session

from core.db import models
from core.services.beta_access_service import BetaAccessService
from core.db.repositories import beta_access as beta_repo
from core.services.notification_service import NotificationService
from core.audit import AuditAction, AuditStatus


class TestBetaAccessRepository:
    """Test beta access repository functions."""

    def test_create_beta_access_request(self, db_session: Session):
        """Test creating a beta access request."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        assert request.user_id == user.id
        assert request.email == user.email
        assert request.status == "pending"
        assert request.requested_at is not None

    def test_get_beta_access_request(self, db_session: Session):
        """Test getting a beta access request by ID."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        retrieved = beta_repo.get_beta_access_request(db_session, request.id)

        assert retrieved is not None
        assert retrieved.id == request.id
        assert retrieved.email == user.email

    def test_get_beta_access_request_by_email(self, db_session: Session):
        """Test getting a beta access request by email."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        retrieved = beta_repo.get_beta_access_request_by_email(db_session, user.email)

        assert retrieved is not None
        assert retrieved.email == user.email

    def test_get_beta_access_requests_by_status(self, db_session: Session):
        """Test getting beta access requests by status."""
        # Create multiple requests
        emails = ["test1@example.com", "test2@example.com", "test3@example.com"]
        for email in emails:
            beta_repo.create_beta_access_request(db_session, None, email)

        pending_requests = beta_repo.get_beta_access_requests_by_status(db_session, "pending")

        assert len(pending_requests) >= 3  # May have requests from other tests
        emails_found = [r.email for r in pending_requests]
        for email in emails:
            assert email in emails_found

    def test_update_beta_access_request_status(self, db_session: Session):
        """Test updating beta access request status."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        updated = beta_repo.update_beta_access_request_status(
            db_session, request.id, "accepted", "admin@example.com", "Approved for beta testing"
        )

        assert updated is not None
        assert updated.status == "accepted"
        assert updated.reviewer_email == "admin@example.com"
        assert updated.decision_reason == "Approved for beta testing"
        assert updated.reviewed_at is not None

    def test_update_beta_access_request_status_not_found(self, db_session: Session):
        """Updating a non-existent request should return None."""
        result = beta_repo.update_beta_access_request_status(
            db_session,
            uuid.uuid4(),
            "accepted",
            "admin@example.com",
            "Approved",
        )

        assert result is None

    def test_update_user_beta_access_status_not_found(self, db_session: Session):
        """Updating status for missing user should return False."""
        success = beta_repo.update_user_beta_access_status(db_session, uuid.uuid4(), 'accepted')
        assert success is False


class TestBetaAccessService:
    """Test beta access service methods."""

    def test_request_beta_access_new_user(self, db_session: Session):
        """Test requesting beta access for a new user."""
        email = "newuser@example.com"

        user = models.User(email=email, display_name="New User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(user.id, email)

            assert result["success"] is True
            assert "request_id" in result

            # User status should transition to pending
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'pending'

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_called_once_with(email)
            mock_notification.return_value.notify_beta_access_admin_notification.assert_called_once()
            args, _ = mock_notification.return_value.notify_beta_access_admin_notification.call_args
            assert str(args[0]) == str(result['request_id'])
            assert args[1] == email
            assert args[2]

    def test_request_beta_access_existing_pending(self, db_session: Session):
        """Test requesting beta access when user already has pending request."""
        email = "existing@example.com"

        user = models.User(email=email, display_name="Existing User", beta_access_status='pending')
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create existing request
        beta_repo.create_beta_access_request(db_session, user.id, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(user.id, email)

            assert result["success"] is False
            assert "already exists" in result["message"]

            # Verify notification was not called
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_not_called()
            mock_notification.return_value.notify_beta_access_admin_notification.assert_not_called()

    def test_request_beta_access_existing_accepted(self, db_session: Session):
        """Existing accepted requests should not create duplicates."""
        email = "accepted@example.com"

        user = models.User(email=email, display_name="Accepted User", beta_access_status='accepted')
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        beta_repo.create_beta_access_request(db_session, user.id, email)
        beta_repo.update_beta_access_request_status(db_session, beta_repo.get_beta_access_request_by_email(db_session, email).id, 'accepted', 'admin@example.com', None)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(user.id, email)

            assert result["success"] is False
            assert "exists" in result["message"].lower()
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_not_called()
            mock_notification.return_value.notify_beta_access_admin_notification.assert_not_called()

    def test_request_beta_access_without_user_record(self, db_session: Session):
        """Gracefully handle requests from emails without user records."""
        email = "nouser@example.com"

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(None, email)

            assert result["success"] is True
            req = beta_repo.get_beta_access_request(db_session, result["request_id"])
            assert req is not None and req.user_id is None
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_called_once_with(email)
            mock_notification.return_value.notify_beta_access_admin_notification.assert_called_once()

    def test_review_beta_access_request_accept(self, db_session: Session):
        """Test accepting a beta access request."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, "accepted", "admin@example.com")

            assert result["success"] is True
            assert result["request_id"] == request.id
            assert "approved" in result.get("message", "")
            assert result["request_email"] == user.email
            assert result["decision"] == "accepted"
            assert result["already_processed"] is False

            # Verify user status was updated
            user_status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert user_status == "accepted"

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_request_deny(self, db_session: Session):
        """Test denying a beta access request."""
        # Create a user first
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, "denied", "admin@example.com", "Not ready for beta")

            assert result["success"] is True
            assert result["request_id"] == request.id
            assert "denied" in result.get("message", "")
            assert result["request_email"] == user.email
            assert result["decision"] == "denied"
            assert result["already_processed"] is False

            # Verify user status was updated
            user_status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert user_status == "denied"

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(user.email, "Not ready for beta")

    def test_review_beta_access_request_invalid_decision(self, db_session: Session):
        """Invalid decisions should short-circuit with error payload."""
        service = BetaAccessService(db_session)
        result = service.review_beta_access_request(uuid.uuid4(), "maybe", "admin@example.com")
        assert result["success"] is False
        assert "invalid decision" in result["message"].lower()

    def test_review_beta_access_request_not_found(self, db_session: Session):
        """Missing requests should surface not found message."""
        service = BetaAccessService(db_session)
        result = service.review_beta_access_request(uuid.uuid4(), "accepted", "admin@example.com")
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    def test_review_beta_access_request_status_conflict(self, db_session: Session):
        """Conflicting decisions should report existing status."""
        user = models.User(email="conflict@example.com", display_name="Conflict User")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)
        beta_repo.update_beta_access_request_status(db_session, request.id, 'denied', 'admin@example.com', None)

        service = BetaAccessService(db_session)
        result = service.review_beta_access_request(request.id, 'accepted', 'admin@example.com')

        assert result["success"] is False
        assert "already denied" in result["message"].lower()

    def test_review_beta_access_request_with_token_accept(self, db_session: Session):
        """Test accepting a beta access request via token."""
        user = models.User(email="token@example.com", display_name="Token User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            token = request.review_token

            result = service.review_beta_access_request_with_token(request.id, token, 'accepted')

            assert result['success'] is True
            assert result['request_id'] == request.id
            assert result['request_email'] == user.email
            assert result['decision'] == 'accepted'
            assert result['already_processed'] is False
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'accepted'

    def test_review_beta_access_request_with_token_deny(self, db_session: Session):
        """Token-based denial should return structured response and send denial email once."""
        user = models.User(email="token-deny@example.com", display_name="Token Deny")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            token = request.review_token

            result = service.review_beta_access_request_with_token(request.id, token, 'denied')

            assert result['success'] is True
            assert result['request_id'] == request.id
            assert result['request_email'] == user.email
            assert result['decision'] == 'denied'
            assert result['already_processed'] is False
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(user.email, None)
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'denied'

    def test_review_beta_access_request_with_token_accept_idempotent(self, db_session: Session):
        """Accepting twice via token should be idempotent and not resend notifications."""
        user = models.User(email="idempotent@example.com", display_name="Idempotent User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            token = request.review_token

            first = service.review_beta_access_request_with_token(request.id, token, 'accepted')
            assert first['success'] is True
            assert first['request_email'] == user.email
            assert first['decision'] == 'accepted'
            assert first['already_processed'] is False

            second = service.review_beta_access_request_with_token(request.id, token, 'accepted')
            assert second['success'] is True
            assert second.get('already_processed') is True
            assert second['request_email'] == user.email
            assert second['decision'] == 'accepted'
            assert 'already' in (second.get('message') or '').lower()
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_request_accept_idempotent(self, db_session: Session):
        """Accepting twice via admin endpoint should return already_processed and avoid duplicate email."""
        user = models.User(email="doubletap@example.com", display_name="Double Tap")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log'):
            service = BetaAccessService(db_session)
            first = service.review_beta_access_request(request.id, 'accepted', 'admin@example.com')
            assert first['already_processed'] is False
            assert first['request_email'] == user.email
            assert first['decision'] == 'accepted'

            second = service.review_beta_access_request(request.id, 'accepted', 'admin@example.com')
            assert second['success'] is True
            assert second['already_processed'] is True
            assert second['request_email'] == user.email
            assert second['decision'] == 'accepted'
            assert 'already' in (second.get('message') or '').lower()
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_request_accept_without_user_id(self, db_session: Session):
        """Requests created without user ids should update status by email and skip audit log."""
        user = models.User(email="email-only@example.com", display_name="Email Only")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, None, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, 'accepted', 'admin@example.com')

            assert result['success'] is True
            assert result['request_email'] == user.email
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'accepted'
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)
            mock_audit.assert_not_called()

    def test_review_beta_access_request_deny_idempotent(self, db_session: Session):
        """Denying twice should return already_processed response without duplicate emails."""
        user = models.User(email="deny-double@example.com", display_name="Deny Twice")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log'):
            service = BetaAccessService(db_session)
            first = service.review_beta_access_request(request.id, 'denied', 'admin@example.com', 'Nope')
            assert first['success'] is True
            assert first['already_processed'] is False
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(user.email, 'Nope')

            mock_notification.return_value.notify_beta_access_denial.reset_mock()
            second = service.review_beta_access_request(request.id, 'denied', 'admin@example.com', 'Nope')
            assert second['success'] is True
            assert second['already_processed'] is True
            assert 'already' in (second.get('message') or '').lower()
            mock_notification.return_value.notify_beta_access_denial.assert_not_called()

    def test_send_admin_notification_email_without_token(self, db_session: Session):
        """Admin notifications should accept missing review tokens."""
        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            request_id = uuid.uuid4()
            service._send_admin_notification_email(request_id, 'user@example.com', None)

            mock_notification.return_value.notify_beta_access_admin_notification.assert_called_once_with(request_id, 'user@example.com', None)

    def test_finalize_review_not_found(self, db_session: Session, monkeypatch):
        """If the repository returns None we surface not found even when request exists."""
        user = models.User(email="missing-update@example.com", display_name="Missing Update")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        service = BetaAccessService(db_session)

        def fake_update(*args, **kwargs):
            return None

        monkeypatch.setattr('core.db.repositories.beta_access.update_beta_access_request_status', fake_update)
        result = service.review_beta_access_request(request.id, 'accepted', 'admin@example.com')

        assert result['success'] is False
        assert 'not found' in result['message'].lower()

    def test_review_beta_access_request_deny_without_user_id(self, db_session: Session):
        """Denials should update status by email when request lacks user_id."""
        user = models.User(email="email-deny@example.com", display_name="Email Deny")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, None, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, 'denied', 'admin@example.com', 'reason')

            assert result['success'] is True
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'denied'
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(user.email, 'reason')

    def test_build_already_processed_response_other_status(self, db_session: Session):
        """Fallback message should include arbitrary status labels."""
        service = BetaAccessService(db_session)
        request = beta_repo.create_beta_access_request(db_session, None, 'pend@example.com')
        request.status = 'pending'

        result = service._build_already_processed_response(request)

        assert result['decision'] == 'pending'
        assert result['already_processed'] is True
        assert 'pending' in result['message'].lower()

    def test_review_beta_access_request_with_token_logs_via_token_metadata(self, db_session: Session):
        """Audit log metadata should include via_token for token-based reviews."""
        user = models.User(email="tokenlog@example.com", display_name="Token Log")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request_with_token(request.id, request.review_token, 'accepted')

            assert result['success'] is True
            metadata = mock_audit.call_args.kwargs.get('metadata')
            assert metadata and metadata.get('via_token') is True
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_request_with_token_invalid(self, db_session: Session):
        """Test token review with invalid token."""
        user = models.User(email="invalid@example.com", display_name="Invalid User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        service = BetaAccessService(db_session)
        result = service.review_beta_access_request_with_token(request.id, 'wrong-token', 'accepted')

        assert result['success'] is False
        assert 'Invalid' in result['message']

    def test_review_beta_access_request_with_token_invalid_decision(self, db_session: Session):
        """Invalid token decisions should be rejected early."""
        service = BetaAccessService(db_session)
        result = service.review_beta_access_request_with_token(uuid.uuid4(), 'tok', 'maybe')
        assert result['success'] is False
        assert 'invalid decision' in result['message'].lower()

    def test_review_beta_access_request_with_token_not_found(self, db_session: Session):
        """Missing requests should return not found via token path."""
        service = BetaAccessService(db_session)
        result = service.review_beta_access_request_with_token(uuid.uuid4(), 'tok', 'accepted')
        assert result['success'] is False
        assert 'not found' in result['message'].lower()

    def test_review_beta_access_request_with_token_status_conflict(self, db_session: Session):
        """Token reviews should report existing status when conflicting."""
        user = models.User(email="token-conflict@example.com", display_name="Token Conflict")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)
        beta_repo.update_beta_access_request_status(db_session, request.id, 'accepted', 'admin@example.com', None)

        service = BetaAccessService(db_session)
        result = service.review_beta_access_request_with_token(request.id, 'does-not-matter', 'denied')

        assert result['success'] is False
        assert 'already accepted' in result['message'].lower()

    def test_review_beta_access_request_with_token_expired(self, db_session: Session):
        """Test token review when token expired."""
        user = models.User(email="expired@example.com", display_name="Expired User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)
        request.token_expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()

        service = BetaAccessService(db_session)
        result = service.review_beta_access_request_with_token(request.id, request.review_token, 'denied')

        assert result['success'] is False
        assert 'expired' in result['message'].lower()

    def test_get_beta_access_status(self, db_session: Session):
        """Test getting beta access status."""
        # Create a user
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        service = BetaAccessService(db_session)
        status = service.get_beta_access_status(user.id)

        # Default for a newly-created user should be 'not_requested'
        assert status == "not_requested"

    def test_get_pending_requests(self, db_session: Session):
        """Test getting pending beta access requests."""
        # Create some requests
        emails = ["pending1@example.com", "pending2@example.com"]
        for email in emails:
            beta_repo.create_beta_access_request(db_session, None, email)

        service = BetaAccessService(db_session)
        requests = service.get_pending_requests()

        assert len(requests) >= 2
        emails_found = [r.email for r in requests]
        for email in emails:
            assert email in emails_found


class TestBetaAccessNotifications:
    """Test beta access email notifications."""

    def test_notify_beta_access_invitation(self, db_session: Session, monkeypatch):
        """Test sending beta access invitation email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        monkeypatch.setenv('APP_BASE_URL', 'https://app.hindsight.ai')
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_invitation("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        # Verify email service was called with correct template
        mock_service.render_template.assert_called_with(
            "beta_access_invitation",
            {"request_url": "https://app.hindsight.ai/beta-access/request"}
        )

    def test_notify_beta_access_request_confirmation(self, db_session: Session, monkeypatch):
        """Test sending beta access request confirmation email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        monkeypatch.setenv('APP_BASE_URL', 'https://app.hindsight-ai.com')
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_request_confirmation("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_request_confirmation",
            {}
        )

    def test_notify_beta_access_request_confirmation_render_error(self, db_session: Session):
        """Render failures should return error payload."""
        mock_service = Mock()
        mock_service.render_template.side_effect = RuntimeError("boom")
        notification_service = NotificationService(db_session, email_service=mock_service)

        result = notification_service.notify_beta_access_request_confirmation("test@example.com")

        assert result["success"] is False
        assert result["error"] == "boom"

    def test_notify_beta_access_admin_notification(self, db_session: Session, monkeypatch):
        """Test sending beta access admin notification email."""
        request_id = uuid.uuid4()
        review_token = 'review-token-abc'

        monkeypatch.setenv('APP_BASE_URL', 'https://app.hindsight.ai')

        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_admin_notification(request_id, "user@example.com", review_token)

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_admin_notification",
            {
                "user_email": "user@example.com",
                "request_id": str(request_id),
                "accept_url": f"https://app.hindsight.ai/login?beta_review={request_id}&beta_decision=accepted&decision=accepted&beta_token={review_token}&token={review_token}",
                "deny_url": f"https://app.hindsight.ai/login?beta_review={request_id}&beta_decision=denied&decision=denied&beta_token={review_token}&token={review_token}",
                "requested_at": ANY,
                "review_token": review_token,
            }
            )

    def test_notify_beta_access_admin_notification_without_token(self, db_session: Session, monkeypatch):
        """Without a review token, fallback links should be used."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}

        monkeypatch.setenv('APP_BASE_URL', 'https://app.hindsight-ai.com')
        notification_service = NotificationService(db_session, email_service=mock_service)
        request_id = uuid.uuid4()
        notification_service.notify_beta_access_admin_notification(request_id, "user@example.com", None)

        args, kwargs = mock_service.render_template.call_args
        context = kwargs["context"] if "context" in kwargs else args[1]
        assert context["accept_url"] == f"https://app.hindsight-ai.com/beta-access/review/{request_id}?decision=accepted"
        assert context["deny_url"] == f"https://app.hindsight-ai.com/beta-access/review/{request_id}?decision=denied"
        assert context["review_token"] is None

    def test_notify_beta_access_acceptance(self, db_session: Session, monkeypatch):
        """Test sending beta access acceptance email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        monkeypatch.setenv('APP_BASE_URL', 'https://app.hindsight.ai')
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_acceptance("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_acceptance",
            {"login_url": "https://app.hindsight.ai/login"}
        )

    def test_notify_beta_access_acceptance_async_send(self, db_session: Session):
        """Async send_email paths should use asyncio.run and capture success."""

        async def fake_send_email(**kwargs):  # pragma: no cover - but executed via fake run
            return {"success": True, "message_id": "async-id"}

        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email = fake_send_email

        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_acceptance("test@example.com")

        assert result["success"] is True
        assert result["message_id"] == "async-id"

    def test_notify_beta_access_denial(self, db_session: Session):
        """Test sending beta access denial email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_denial("test@example.com", "Not approved")

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_denial",
            {"decision_reason": "Not approved"}
        )

    def test_notify_beta_access_denial_async_send(self, db_session: Session):
        """Async denial paths should succeed and surface message id."""

        async def fake_send_email(**kwargs):
            return {"success": True, "message_id": "async-deny"}

        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email = fake_send_email

        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_denial("test@example.com", "reason")

        assert result["success"] is True
        assert result["message_id"] == "async-deny"


class TestBetaAccessAPI:
    """Test beta access API endpoints."""

    def test_request_beta_access_endpoint(self, client, db_session: Session):
        """Test POST /api/beta-access/request endpoint."""
        # Create a user
        user = models.User(email="newuser@example.com", display_name="New User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post("/beta-access/request", headers={"x-auth-request-user": "newuser", "x-auth-request-email": "newuser@example.com"})

            assert response.status_code == 201
            data = response.json()
            assert data["success"] is True
            assert "request_id" in data

    def test_request_beta_access_endpoint_dev_mode_defaults(self, client, db_session: Session, monkeypatch):
        """DEV_MODE should auto-provision the development account without headers."""
        monkeypatch.setenv('DEV_MODE', 'true')

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post("/beta-access/request")

        assert response.status_code == 201
        payload = response.json()
        request = beta_repo.get_beta_access_request(db_session, uuid.UUID(payload["request_id"]))
        assert request is not None
        assert request.email == "dev@localhost"
        mock_notification.return_value.notify_beta_access_request_confirmation.assert_called_once_with("dev@localhost")
        mock_notification.return_value.notify_beta_access_admin_notification.assert_called_once()

    def test_request_beta_access_endpoint_requires_email(self, client, monkeypatch):
        """Non-dev mode requests without identity should return 401."""
        monkeypatch.setenv('DEV_MODE', 'false')

        def fake_resolve(x_auth_request_user=None, x_auth_request_email=None, x_forwarded_user=None, x_forwarded_email=None):
            return None, None

        monkeypatch.setattr('core.api.auth.resolve_identity_from_headers', fake_resolve)

        response = client.post(
            "/beta-access/request",
            headers={"X-Auth-Request-User": "Guest"},
        )

        assert response.status_code == 401
        detail = response.json()["detail"].lower()
        assert 'guest mode' in detail or 'authentication required' in detail

    def test_request_beta_access_endpoint_handles_user_creation_failure(self, client, monkeypatch):
        """If user creation raises we still create a request keyed by email."""

        def fail_create(db, email, display_name=None):
            raise RuntimeError("boom")

        monkeypatch.setattr('core.api.auth.get_or_create_user', fail_create)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post(
                "/beta-access/request",
                headers={
                    "X-Auth-Request-Email": "fallback@example.com",
                    "X-Auth-Request-User": "Fallback",
                },
            )

        assert response.status_code == 201
        payload = response.json()
        assert payload["success"] is True
        mock_notification.return_value.notify_beta_access_request_confirmation.assert_called_once_with("fallback@example.com")

    def test_request_beta_access_endpoint_duplicate(self, client, db_session: Session):
        """Test POST /api/beta-access/request endpoint with duplicate request."""
        # Create a user
        user = models.User(email="existing@example.com", display_name="Existing User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        # Create existing request
        beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post("/beta-access/request", headers={"x-auth-request-user": "existing", "x-auth-request-email": "existing@example.com"})

            assert response.status_code == 400
            data = response.json()
            assert "detail" in data
            assert "already exists" in data["detail"]

    def test_review_beta_access_endpoint_accept(self, client, db_session: Session):
        """Test POST /api/beta-access/review/{id} endpoint for acceptance."""
        # Create a user and request
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        # Create admin user
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post(
                f"/beta-access/review/{request.id}?decision=accepted",
                headers={"x-auth-request-user": "admin", "x-auth-request-email": "ibarz.jean@gmail.com"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
            assert data["decision"] == "accepted"
            assert data["request_email"] == user.email
            assert data["already_processed"] is False

    def test_review_beta_access_endpoint_invalid_decision(self, client, db_session: Session):
        """Invalid decisions should produce 400 errors."""
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin); db_session.commit(); db_session.refresh(admin)

        response = client.post(
            f"/beta-access/review/{uuid.uuid4()}?decision=maybe",
            headers={
                "X-Auth-Request-Email": "ibarz.jean@gmail.com",
                "X-Auth-Request-User": "Admin",
            },
        )

        assert response.status_code == 400
        assert "Invalid decision" in response.json()["detail"]

    def test_review_beta_access_endpoint_forbidden_for_non_admin(self, client):
        """Non-admin reviewers should be rejected."""
        response = client.post(
            f"/beta-access/review/{uuid.uuid4()}?decision=accepted",
            headers={
                "X-Auth-Request-Email": "viewer@example.com",
                "X-Auth-Request-User": "Viewer",
            },
        )

        assert response.status_code == 403
        assert 'beta access admin' in response.json()["detail"].lower()

    def test_review_beta_access_endpoint_accept_idempotent(self, client, db_session: Session):
        """Repeated admin approvals should return already_processed and skip duplicate email."""
        user = models.User(email="admin-idem@example.com", display_name="Admin Idem")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin)
        db_session.commit(); db_session.refresh(admin)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            first = client.post(
                f"/beta-access/review/{request.id}?decision=accepted",
                headers={"x-auth-request-user": "admin", "x-auth-request-email": "ibarz.jean@gmail.com"}
            )
            assert first.status_code == 200
            first_body = first.json()
            assert first_body['already_processed'] is False

            second = client.post(
                f"/beta-access/review/{request.id}?decision=accepted",
                headers={"x-auth-request-user": "admin", "x-auth-request-email": "ibarz.jean@gmail.com"}
            )
            assert second.status_code == 200
            second_body = second.json()
            assert second_body['success'] is True
            assert second_body['already_processed'] is True
            assert second_body['decision'] == 'accepted'
            assert second_body['request_email'] == user.email
            assert 'already' in (second_body.get('message') or '').lower()
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_get_beta_access_status_endpoint(self, client, db_session: Session):
        """Test GET /api/beta-access/status endpoint."""
        # Create a user
        user = models.User(email="test@example.com", display_name="Test User")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        response = client.get("/beta-access/status", headers={"x-auth-request-user": "test", "x-auth-request-email": "test@example.com"})

        assert response.status_code == 200, (response.status_code, response.json())
        data = response.json()

        assert "status" in data

        # Default status should be 'not_requested'
        assert data["status"] == "not_requested"

    def test_get_pending_requests_endpoint(self, client, db_session: Session):
        """Test GET /api/beta-access/pending endpoint."""
        # Create admin user
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)

        # Create some requests
        emails = ["pending1@example.com", "pending2@example.com"]
        for email in emails:
            beta_repo.create_beta_access_request(db_session, None, email)

        response = client.get("/beta-access/pending", headers={"x-auth-request-user": "admin", "x-auth-request-email": "ibarz.jean@gmail.com"})

        assert response.status_code == 200
        data = response.json()
        assert "requests" in data
        assert isinstance(data["requests"], list)
        assert len(data["requests"]) >= 2

    def test_get_pending_requests_endpoint_forbidden(self, client):
        """Pending requests should be locked down to admins."""
        response = client.get(
            "/beta-access/pending",
            headers={
                "X-Auth-Request-Email": "viewer@example.com",
                "X-Auth-Request-User": "Viewer",
            },
        )

        assert response.status_code == 403
        assert 'beta access admin' in response.json()["detail"].lower()

    def test_review_beta_access_endpoint_token(self, client, db_session: Session):
        """Test POST /api/beta-access/review/{id}/token endpoint."""
        user = models.User(email="token-api@example.com", display_name="Token Admin")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post(
                f"/beta-access/review/{request.id}/token",
                json={"decision": "accepted", "token": request.review_token}
            )

            data = response.json()
            assert response.status_code == 200, (response.status_code, data)
            assert data["success"] is True
            assert data["request_id"] == str(request.id)
            assert data["request_email"] == user.email
            assert data["decision"] == "accepted"
            assert data["already_processed"] is False
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_endpoint_token_idempotent(self, client, db_session: Session):
        """Token endpoint should surface already_processed on subsequent approvals."""
        user = models.User(email="token-idem@example.com", display_name="Token Idem")
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)
        token_value = request.review_token

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            first = client.post(
                f"/beta-access/review/{request.id}/token",
                json={"decision": "accepted", "token": token_value}
            )
            assert first.status_code == 200
            assert first.json()['already_processed'] is False

            second = client.post(
                f"/beta-access/review/{request.id}/token",
                json={"decision": "accepted", "token": token_value}
            )
            second_body = second.json()
            assert second.status_code == 200, (second.status_code, second_body)
            assert second_body['success'] is True
            assert second_body['already_processed'] is True
            assert second_body['decision'] == 'accepted'
            assert second_body['request_email'] == user.email
            assert 'already' in (second_body.get('message') or '').lower()
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)

    def test_review_beta_access_endpoint_token_expired(self, client, db_session: Session):
        """Expired tokens should map to HTTP 410."""
        user = models.User(email="token-expired@example.com", display_name="Token Expired")
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)
        request.token_expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        db_session.commit()

        response = client.post(
            f"/beta-access/review/{request.id}/token",
            json={"decision": "accepted", "token": request.review_token}
        )

        assert response.status_code == 410
        assert "expired" in response.json()["detail"].lower()

    def test_admin_users_endpoint_forbidden(self, client, db_session: Session):
        response = client.get(
            "/beta-access/admin/users",
            headers={"x-auth-request-email": "viewer@example.com", "x-auth-request-user": "Viewer"}
        )
        assert response.status_code == 403

    def test_admin_users_endpoint_lists_users(self, client, db_session: Session):
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin)
        db_session.commit(); db_session.refresh(admin)

        user = models.User(email="tester@example.com", display_name="Tester", beta_access_status='pending')
        db_session.add(user)
        db_session.commit(); db_session.refresh(user)

        beta_repo.create_beta_access_request(db_session, user.id, user.email)

        response = client.get(
            "/beta-access/admin/users",
            headers={"x-auth-request-email": "ibarz.jean@gmail.com", "x-auth-request-user": "Admin"}
        )

        assert response.status_code == 200
        data = response.json()
        users = data.get('users')
        assert any(entry['email'] == user.email for entry in users)

    def test_admin_update_requires_valid_status(self, client, db_session: Session):
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin); db_session.commit(); db_session.refresh(admin)

        target = models.User(email="manual@example.com", display_name="Manual")
        db_session.add(target); db_session.commit(); db_session.refresh(target)

        response = client.patch(
            f"/beta-access/admin/users/{target.id}",
            json={"status": "invalid"},
            headers={"x-auth-request-email": "ibarz.jean@gmail.com", "x-auth-request-user": "Admin"}
        )

        assert response.status_code == 400

    def test_admin_update_revoked(self, client, db_session: Session):
        admin = models.User(email="ibarz.jean@gmail.com", display_name="Admin")
        db_session.add(admin); db_session.commit(); db_session.refresh(admin)

        target = models.User(email="manual@example.com", display_name="Manual", beta_access_status='accepted')
        db_session.add(target); db_session.commit(); db_session.refresh(target)

        request = beta_repo.create_beta_access_request(db_session, target.id, target.email)
        beta_repo.update_beta_access_request_status(db_session, request.id, 'accepted', 'admin@example.com', None)

        with patch('core.api.beta_access.audit_log') as mock_audit:
            response = client.patch(
                f"/beta-access/admin/users/{target.id}",
                json={"status": "revoked"},
                headers={"x-auth-request-email": "ibarz.jean@gmail.com", "x-auth-request-user": "Admin"}
            )

        assert response.status_code == 200
        body = response.json()
        assert body['success'] is True
        assert body['user']['beta_access_status'] == 'revoked'
        mock_audit.assert_called_once()



class TestAuthHelpers:
    """Additional coverage for auth utility helpers used by beta access flows."""

    def test_get_or_create_user_sets_default_status_for_existing(self, db_session: Session):
        user = models.User(email="nostatus@example.com", display_name="No Status", beta_access_status=None)
        db_session.add(user); db_session.commit(); db_session.refresh(user)
        user.beta_access_status = None

        from core.api import auth

        result = auth.get_or_create_user(db_session, email=user.email, display_name="No Status")

        assert result.beta_access_status == 'not_requested'

    def test_get_user_memberships_handles_query_exception(self, db_session: Session, monkeypatch):
        from core.api import auth

        original_query = db_session.query

        def failing_query(*args, **kwargs):
            raise RuntimeError("db down")

        monkeypatch.setattr(db_session, 'query', failing_query)

        memberships = auth.get_user_memberships(db_session, uuid.uuid4())
        assert memberships == []

        monkeypatch.setattr(db_session, 'query', original_query, raising=False)


class TestAuditAPI:
    """Small checks for audit endpoints to satisfy coverage penalties."""

    def test_list_audit_logs_requires_org_for_non_superadmin(self, client, monkeypatch):
        monkeypatch.setattr('core.db.crud.get_audit_logs', lambda *args, **kwargs: [])

        response = client.get(
            "/audits/?skip=0&limit=10",
            headers={
                "X-Auth-Request-Email": "user@example.com",
                "X-Auth-Request-User": "User",
            },
        )

        assert response.status_code == 403
        assert "organization_id is required" in response.json().get("detail", "")

    def test_list_audit_logs_forbids_without_manage_permission(self, client, monkeypatch):
        monkeypatch.setattr('core.db.crud.get_audit_logs', lambda *args, **kwargs: [])
        monkeypatch.setattr('core.api.audits.can_manage_org', lambda *args, **kwargs: False)

        org_id = uuid.uuid4()
        response = client.get(
            f"/audits/?organization_id={org_id}",
            headers={
                "X-Auth-Request-Email": "user@example.com",
                "X-Auth-Request-User": "User",
            },
        )

        assert response.status_code == 403
        assert "Forbidden" in response.json().get("detail", "")


class TestAuthDepsBetaAccess:
    """Exercise get_current_user_context beta gating branches."""

    def test_get_current_user_context_dev_mode_auto_accepts(self, db_session: Session, monkeypatch):
        monkeypatch.setenv('DEV_MODE', 'true')

        from core.api import deps

        user, ctx = deps.get_current_user_context(db=db_session, x_auth_request_user='Dev', x_auth_request_email='dev@localhost')
        assert ctx['beta_access_status'] == 'accepted'
        assert user.beta_access_status == 'accepted'

    def test_get_current_user_context_syncs_request_status(self, db_session: Session, monkeypatch):
        monkeypatch.setenv('DEV_MODE', 'false')

        email = "beta-sync@example.com"
        user = models.User(email=email, display_name="Beta Sync", beta_access_status='pending')
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, email)
        beta_repo.update_beta_access_request_status(db_session, request.id, 'accepted', 'admin@example.com', None)

        monkeypatch.setattr('core.api.deps.resolve_identity_from_headers', lambda **kwargs: ("Beta Sync", email))

        from core.api import deps

        user_obj, ctx = deps.get_current_user_context(db=db_session, x_auth_request_user='Beta Sync', x_auth_request_email=email)
        assert ctx['beta_access_status'] == 'accepted'
        assert user_obj.beta_access_status == 'accepted'

    def test_get_current_user_context_requires_email(self, db_session: Session, monkeypatch):
        monkeypatch.setenv('DEV_MODE', 'false')
        monkeypatch.setattr('core.api.deps.resolve_identity_from_headers', lambda **kwargs: (None, None))

        from core.api import deps
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            deps.get_current_user_context(db=db_session, x_auth_request_user=None, x_auth_request_email=None)

        assert exc.value.status_code == 401
        assert "Authentication required" in exc.value.detail

    def test_get_current_user_context_clears_stale_pending(self, db_session: Session, monkeypatch):
        monkeypatch.setenv('DEV_MODE', 'false')

        email = "stale@example.com"
        user = models.User(email=email, display_name="Stale Pending", beta_access_status='pending')
        db_session.add(user); db_session.commit(); db_session.refresh(user)

        # No existing request should downgrade pending to not_requested
        monkeypatch.setattr('core.api.deps.resolve_identity_from_headers', lambda **kwargs: ("Stale", email))

        from core.api import deps

        user_obj, ctx = deps.get_current_user_context(db=db_session, x_auth_request_user='Stale', x_auth_request_email=email)
        assert ctx['beta_access_status'] == 'not_requested'
        assert user_obj.beta_access_status == 'not_requested'

    def test_get_user_memberships_handles_non_iterable_results(self, db_session: Session, monkeypatch):
        from core.api import auth

        class FakeQuery:
            def join(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def all(self):
                return object()

        original_query = db_session.query
        monkeypatch.setattr(db_session, 'query', lambda *args, **kwargs: FakeQuery())

        memberships = auth.get_user_memberships(db_session, uuid.uuid4())
        assert memberships == []

        monkeypatch.setattr(db_session, 'query', original_query, raising=False)

    def test_get_user_memberships_parses_membership_rows(self, db_session: Session):
        user = models.User(email="membership@example.com", display_name="Member")
        org = models.Organization(name="Org", slug="org")
        db_session.add_all([user, org]); db_session.commit(); db_session.refresh(user); db_session.refresh(org)

        membership = models.OrganizationMembership(user_id=user.id, organization_id=org.id, role="admin")
        db_session.add(membership); db_session.commit()

        from core.api import auth

        results = auth.get_user_memberships(db_session, user.id)
        assert results
        assert results[0]["organization_id"] == str(org.id)
        assert results[0]["role"] == "admin"

    def test_get_user_memberships_skips_malformed_rows(self, db_session: Session, monkeypatch):
        from core.api import auth

        class MalformedRow:
            def __iter__(self):
                raise RuntimeError("bad row")

        class FakeQuery:
            def join(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def all(self):
                return [MalformedRow()]

        original_query = db_session.query
        monkeypatch.setattr(db_session, 'query', lambda *args, **kwargs: FakeQuery())

        memberships = auth.get_user_memberships(db_session, uuid.uuid4())
        assert memberships == []

        monkeypatch.setattr(db_session, 'query', original_query, raising=False)

    def test_get_user_memberships_handles_membership_object(self, db_session: Session, monkeypatch):
        from core.api import auth

        class OrgObj:
            name = "Detached"

        class MembershipObj:
            organization_id = uuid.uuid4()
            organization = OrgObj()
            role = "viewer"
            can_read = True
            can_write = False

        class FakeQuery:
            def join(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def all(self):
                return [MembershipObj()]

        original_query = db_session.query
        monkeypatch.setattr(db_session, 'query', lambda *args, **kwargs: FakeQuery())

        memberships = auth.get_user_memberships(db_session, uuid.uuid4())
        assert memberships and memberships[0]["organization_name"] == "Detached"

        monkeypatch.setattr(db_session, 'query', original_query, raising=False)

    def test_get_user_memberships_skips_empty_membership(self, db_session: Session, monkeypatch):
        from core.api import auth

        class FakeQuery:
            def join(self, *args, **kwargs):
                return self

            def filter(self, *args, **kwargs):
                return self

            def all(self):
                return [(None, object())]

        original_query = db_session.query
        monkeypatch.setattr(db_session, 'query', lambda *args, **kwargs: FakeQuery())

        memberships = auth.get_user_memberships(db_session, uuid.uuid4())
        assert memberships == []

        monkeypatch.setattr(db_session, 'query', original_query, raising=False)

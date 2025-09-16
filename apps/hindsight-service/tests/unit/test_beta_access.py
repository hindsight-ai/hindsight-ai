"""
Unit tests for beta access functionality.

Tests beta access service, repository, API endpoints, and email notifications.
"""
import uuid
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


class TestBetaAccessService:
    """Test beta access service methods."""

    def test_request_beta_access_new_user(self, db_session: Session):
        """Test requesting beta access for a new user."""
        email = "newuser@example.com"

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(None, email)

            assert result["success"] is True
            assert "request_id" in result

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

        # Create existing request
        beta_repo.create_beta_access_request(db_session, None, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification, \
             patch('core.services.beta_access_service.audit_log') as mock_audit:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(None, email)

            assert result["success"] is False
            assert "already exists" in result["message"]

            # Verify notification was not called
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_not_called()
            mock_notification.return_value.notify_beta_access_admin_notification.assert_not_called()

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

            # Verify user status was updated
            user_status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert user_status == "denied"

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(user.email, "Not ready for beta")

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
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(user.email)
            status = beta_repo.get_user_beta_access_status(db_session, user.id)
            assert status == 'accepted'

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

        assert status == "pending"

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

    def test_notify_beta_access_invitation(self, db_session: Session):
        """Test sending beta access invitation email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_invitation("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        # Verify email service was called with correct template
        mock_service.render_template.assert_called_with(
            "beta_access_invitation",
            {"request_url": "https://app.hindsight.ai/beta-access/request"}
        )

    def test_notify_beta_access_request_confirmation(self, db_session: Session):
        """Test sending beta access request confirmation email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_request_confirmation("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_request_confirmation",
            {}
        )

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

    def test_notify_beta_access_acceptance(self, db_session: Session):
        """Test sending beta access acceptance email."""
        mock_service = Mock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        mock_service.send_email.return_value = {"success": True, "message_id": "test-id"}
        
        notification_service = NotificationService(db_session, email_service=mock_service)
        result = notification_service.notify_beta_access_acceptance("test@example.com")

        assert result["success"] is True
        assert "message_id" in result
        mock_service.render_template.assert_called_with(
            "beta_access_acceptance",
            {"login_url": "https://app.hindsight.ai/login"}
        )

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
        assert data["status"] == "pending"  # Default status

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

    def test_review_beta_access_endpoint_token(self, client, db_session: Session):
        """Test POST /api/beta-access/review/{id}/token endpoint."""
        user = models.User(email="token-api@example.com", display_name="Token Admin")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

        request = beta_repo.create_beta_access_request(db_session, user.id, user.email)

        response = client.post(
            f"/beta-access/review/{request.id}/token",
            json={"decision": "accepted", "token": request.review_token}
        )

        data = response.json()
        assert response.status_code == 200, (response.status_code, data)
        assert data["success"] is True
        assert data["request_id"] == str(request.id)

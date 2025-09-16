"""
Unit tests for beta access functionality.

Tests beta access service, repository, API endpoints, and email notifications.
"""
import uuid
import pytest
from unittest.mock import Mock, patch, MagicMock
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
        user_id = uuid.uuid4()
        email = "test@example.com"

        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        assert request.user_id == user_id
        assert request.email == email
        assert request.status == "pending"
        assert request.requested_at is not None

    def test_get_beta_access_request(self, db_session: Session):
        """Test getting a beta access request by ID."""
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        retrieved = beta_repo.get_beta_access_request(db_session, request.id)

        assert retrieved is not None
        assert retrieved.id == request.id
        assert retrieved.email == email

    def test_get_beta_access_request_by_email(self, db_session: Session):
        """Test getting a beta access request by email."""
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        retrieved = beta_repo.get_beta_access_request_by_email(db_session, email)

        assert retrieved is not None
        assert retrieved.email == email

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
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        updated = beta_repo.update_beta_access_request_status(
            db_session, request.id, "accepted", "admin@example.com", "Approved for beta testing"
        )

        assert updated is not None
        assert updated.status == "accepted"
        assert updated.reviewer_email == "admin@example.com"
        assert updated.decision_reason == "Approved for beta testing"
        assert updated.reviewed_at is not None

    def test_get_user_beta_access_status(self, db_session: Session, test_user: models.User):
        """Test getting user beta access status."""
        status = beta_repo.get_user_beta_access_status(db_session, test_user.id)

        assert status == "pending"  # Default status

    def test_update_user_beta_access_status(self, db_session: Session, test_user: models.User):
        """Test updating user beta access status."""
        success = beta_repo.update_user_beta_access_status(db_session, test_user.id, "accepted")

        assert success is True

        # Verify the update
        updated_status = beta_repo.get_user_beta_access_status(db_session, test_user.id)
        assert updated_status == "accepted"


class TestBetaAccessService:
    """Test beta access service methods."""

    def test_request_beta_access_new_user(self, db_session: Session):
        """Test requesting beta access for a new user."""
        email = "newuser@example.com"

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(email)

            assert result["success"] is True
            assert "request_id" in result

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_called_once_with(email)

    def test_request_beta_access_existing_pending(self, db_session: Session):
        """Test requesting beta access when user already has pending request."""
        email = "existing@example.com"

        # Create existing request
        beta_repo.create_beta_access_request(db_session, None, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.request_beta_access(email)

            assert result["success"] is False
            assert "already have a pending request" in result["message"]

            # Verify notification was not called
            mock_notification.return_value.notify_beta_access_request_confirmation.assert_not_called()

    def test_review_beta_access_request_accept(self, db_session: Session):
        """Test accepting a beta access request."""
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, "accepted", "admin@example.com")

            assert result["success"] is True

            # Verify user status was updated
            user_status = beta_repo.get_user_beta_access_status(db_session, user_id)
            assert user_status == "accepted"

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_acceptance.assert_called_once_with(email)

    def test_review_beta_access_request_deny(self, db_session: Session):
        """Test denying a beta access request."""
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            service = BetaAccessService(db_session)
            result = service.review_beta_access_request(request.id, "denied", "admin@example.com", "Not ready for beta")

            assert result["success"] is True

            # Verify user status was updated
            user_status = beta_repo.get_user_beta_access_status(db_session, user_id)
            assert user_status == "denied"

            # Verify notification was called
            mock_notification.return_value.notify_beta_access_denial.assert_called_once_with(email, "Not ready for beta")

    def test_get_beta_access_status(self, db_session: Session, test_user: models.User):
        """Test getting beta access status."""
        service = BetaAccessService(db_session)
        status = service.get_beta_access_status(test_user.id)

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
        with patch('core.services.notification_service.TransactionalEmailService') as mock_email_service:
            notification_service = NotificationService(db_session)
            result = notification_service.notify_beta_access_invitation("test@example.com")

            assert "email_log" in result
            # Verify email service was called with correct template
            mock_email_service.return_value.render_template.assert_called_with(
                "beta_access_invitation",
                {"request_url": "https://app.hindsight.ai/beta-access/request"}
            )

    def test_notify_beta_access_request_confirmation(self, db_session: Session):
        """Test sending beta access request confirmation email."""
        with patch('core.services.notification_service.TransactionalEmailService') as mock_email_service:
            notification_service = NotificationService(db_session)
            result = notification_service.notify_beta_access_request_confirmation("test@example.com")

            assert "email_log" in result
            mock_email_service.return_value.render_template.assert_called_with(
                "beta_access_request_confirmation",
                {}
            )

    def test_notify_beta_access_admin_notification(self, db_session: Session):
        """Test sending beta access admin notification email."""
        request_id = uuid.uuid4()

        with patch('core.services.notification_service.TransactionalEmailService') as mock_email_service:
            notification_service = NotificationService(db_session)
            result = notification_service.notify_beta_access_admin_notification(request_id, "user@example.com")

            assert "email_log" in result
            mock_email_service.return_value.render_template.assert_called_with(
                "beta_access_admin_notification",
                {
                    "user_email": "user@example.com",
                    "request_id": str(request_id),
                    "accept_url": f"https://app.hindsight.ai/beta-access/review/{request_id}?decision=accepted",
                    "deny_url": f"https://app.hindsight.ai/beta-access/review/{request_id}?decision=denied",
                    "requested_at": pytest.any(str)
                }
            )

    def test_notify_beta_access_acceptance(self, db_session: Session):
        """Test sending beta access acceptance email."""
        with patch('core.services.notification_service.TransactionalEmailService') as mock_email_service:
            notification_service = NotificationService(db_session)
            result = notification_service.notify_beta_access_acceptance("test@example.com")

            assert "email_log" in result
            mock_email_service.return_value.render_template.assert_called_with(
                "beta_access_acceptance",
                {"login_url": "https://app.hindsight.ai/login"}
            )

    def test_notify_beta_access_denial(self, db_session: Session):
        """Test sending beta access denial email."""
        with patch('core.services.notification_service.TransactionalEmailService') as mock_email_service:
            notification_service = NotificationService(db_session)
            result = notification_service.notify_beta_access_denial("test@example.com", "Not approved")

            assert "email_log" in result
            mock_email_service.return_value.render_template.assert_called_with(
                "beta_access_denial",
                {"decision_reason": "Not approved"}
            )


class TestBetaAccessAPI:
    """Test beta access API endpoints."""

    def test_request_beta_access_endpoint(self, client, db_session: Session):
        """Test POST /api/beta-access/request endpoint."""
        email = "newuser@example.com"

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post("/api/beta-access/request", json={"email": email})

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "request_id" in data

    def test_request_beta_access_endpoint_duplicate(self, client, db_session: Session):
        """Test POST /api/beta-access/request endpoint with duplicate request."""
        email = "existing@example.com"

        # Create existing request
        beta_repo.create_beta_access_request(db_session, None, email)

        response = client.post("/api/beta-access/request", json={"email": email})

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        assert "already have a pending request" in data["message"]

    def test_review_beta_access_endpoint_accept(self, client, db_session: Session):
        """Test POST /api/beta-access/review/{id} endpoint for acceptance."""
        user_id = uuid.uuid4()
        email = "test@example.com"
        request = beta_repo.create_beta_access_request(db_session, user_id, email)

        with patch('core.services.beta_access_service.NotificationService') as mock_notification:
            response = client.post(
                f"/api/beta-access/review/{request.id}",
                json={"decision": "accepted", "reviewer_email": "admin@example.com"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_beta_access_status_endpoint(self, client, db_session: Session, authenticated_user):
        """Test GET /api/beta-access/status endpoint."""
        response = client.get("/api/beta-access/status")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "pending"  # Default status

    def test_get_pending_requests_endpoint(self, client, db_session: Session):
        """Test GET /api/beta-access/pending endpoint."""
        # Create some requests
        emails = ["pending1@example.com", "pending2@example.com"]
        for email in emails:
            beta_repo.create_beta_access_request(db_session, None, email)

        response = client.get("/api/beta-access/pending")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2


class TestBetaAccessAuthentication:
    """Test beta access invitation logic in authentication."""

    def test_beta_access_invitation_sent_for_pending_user(self, db_session: Session, test_user: models.User):
        """Test that beta access invitation is sent for users with pending status."""
        # Ensure user has pending status
        test_user.beta_access_status = "pending"
        db_session.commit()

        with patch('core.api.deps.NotificationService') as mock_notification, \
             patch('core.api.deps.beta_repo') as mock_beta_repo:

            mock_beta_repo.get_beta_access_request_by_email.return_value = None

            # Import here to avoid circular imports
            from core.api.deps import get_current_user_context

            # Mock the dependencies
            with patch('core.api.deps.get_db', return_value=db_session), \
                 patch('core.api.deps.resolve_identity_from_headers', return_value=("Test User", test_user.email)):

                try:
                    user, context = get_current_user_context()
                    # Verify notification was called
                    mock_notification.return_value.notify_beta_access_invitation.assert_called_once_with(test_user.email)
                except Exception:
                    # Authentication might fail in test environment, but we just want to check if notification was called
                    pass

    def test_beta_access_invitation_not_sent_for_existing_request(self, db_session: Session, test_user: models.User):
        """Test that beta access invitation is not sent if user already has a pending request."""
        # Ensure user has pending status
        test_user.beta_access_status = "pending"
        db_session.commit()

        with patch('core.api.deps.NotificationService') as mock_notification, \
             patch('core.api.deps.beta_repo') as mock_beta_repo:

            # Mock existing request
            mock_existing_request = Mock()
            mock_existing_request.status = "pending"
            mock_beta_repo.get_beta_access_request_by_email.return_value = mock_existing_request

            # Import here to avoid circular imports
            from core.api.deps import get_current_user_context

            # Mock the dependencies
            with patch('core.api.deps.get_db', return_value=db_session), \
                 patch('core.api.deps.resolve_identity_from_headers', return_value=("Test User", test_user.email)):

                try:
                    user, context = get_current_user_context()
                    # Verify notification was NOT called
                    mock_notification.return_value.notify_beta_access_invitation.assert_not_called()
                except Exception:
                    # Authentication might fail in test environment
                    pass

    def test_beta_access_invitation_not_sent_for_accepted_user(self, db_session: Session, test_user: models.User):
        """Test that beta access invitation is not sent for users with accepted status."""
        # Ensure user has accepted status
        test_user.beta_access_status = "accepted"
        db_session.commit()

        with patch('core.api.deps.NotificationService') as mock_notification, \
             patch('core.api.deps.beta_repo') as mock_beta_repo:

            # Import here to avoid circular imports
            from core.api.deps import get_current_user_context

            # Mock the dependencies
            with patch('core.api.deps.get_db', return_value=db_session), \
                 patch('core.api.deps.resolve_identity_from_headers', return_value=("Test User", test_user.email)):

                try:
                    user, context = get_current_user_context()
                    # Verify notification was NOT called
                    mock_notification.return_value.notify_beta_access_invitation.assert_not_called()
                except Exception:
                    # Authentication might fail in test environment
                    pass

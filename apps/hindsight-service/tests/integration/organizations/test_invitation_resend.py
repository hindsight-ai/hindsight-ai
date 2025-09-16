"""
Tests for invitation resend functionality to ensure emails are actually sent.
"""
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models
from core.services.notification_service import NotificationService


client = TestClient(app, headers={"X-Active-Scope": "personal"})


def auth(email="test@example.com", name="TestUser"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


@pytest.fixture
def setup_org_and_invitation(db_session):
    """Setup test data: organization, users, and invitation."""
    # Create owner user
    owner = models.User(
        email="owner@example.com",
        display_name="Owner User",
        is_superadmin=False
    )
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create organization
    org = models.Organization(
        name="TestOrg",
        slug="test-org",
        created_by=owner.id
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    # Create membership for owner
    membership = models.OrganizationMembership(
        organization_id=org.id,
        user_id=owner.id,
        role="owner",
        can_read=True,
        can_write=True
    )
    db_session.add(membership)
    db_session.commit()

    # Create invitation
    invitation = models.OrganizationInvitation(
        organization_id=org.id,
        email="invitee@example.com",
        role="editor",
        status="pending",
        token="original_token_123",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        invited_by_user_id=owner.id
    )
    db_session.add(invitation)
    db_session.commit()
    db_session.refresh(invitation)

    return org, owner, invitation


class TestInvitationResend:
    """Test suite for invitation resend functionality."""

    @patch('core.services.notification_service.NotificationService.notify_organization_invitation')
    def test_resend_invitation_sends_email(self, mock_notify, db_session, setup_org_and_invitation):
        """Test that resend invitation actually calls the notification service to send email."""
        org, owner, invitation = setup_org_and_invitation

        # Mock the email service
        mock_email_service = MagicMock()
        mock_notify.return_value = None

        with patch('core.services.transactional_email_service.get_transactional_email_service') as mock_get_email:
            mock_get_email.return_value = mock_email_service

            # Call the resend endpoint
            response = client.post(
                f"/organizations/{org.id}/invitations/{invitation.id}/resend",
                headers=auth(owner.email, owner.display_name)
            )

            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["id"] == str(invitation.id)
            assert response_data["email"] == invitation.email
            assert response_data["role"] == invitation.role

            # Verify notification service was called
            mock_notify.assert_called_once()

            # Get the call arguments
            call_args = mock_notify.call_args
            assert call_args[1]["invitee_email"] == invitation.email
            assert call_args[1]["inviter_name"] == owner.display_name
            assert call_args[1]["inviter_user_id"] == owner.id
            assert call_args[1]["organization_name"] == org.name
            assert call_args[1]["invitation_id"] == invitation.id
            assert call_args[1]["role"] == invitation.role
            assert "accept_url" in call_args[1]
            assert "decline_url" in call_args[1]

    def test_resend_invitation_rotates_token(self, db_session, setup_org_and_invitation):
        """Test that resend invitation rotates the token to invalidate old links."""
        org, owner, invitation = setup_org_and_invitation
        original_token = invitation.token

        # Call the resend endpoint
        response = client.post(
            f"/organizations/{org.id}/invitations/{invitation.id}/resend",
            headers=auth(owner.email, owner.display_name)
        )

        assert response.status_code == 200

        # Refresh the invitation in the test's transactional session to observe updates
        db_session.refresh(invitation)

        # Verify token was rotated
        assert invitation.token != original_token
        assert len(invitation.token) > 0  # New token should not be empty

    def test_resend_invitation_updates_expiration(self, db_session, setup_org_and_invitation):
        """Test that resend invitation extends the expiration date."""
        org, owner, invitation = setup_org_and_invitation
        original_expires_at = invitation.expires_at

        # Call the resend endpoint
        response = client.post(
            f"/organizations/{org.id}/invitations/{invitation.id}/resend",
            headers=auth(owner.email, owner.display_name)
        )

        assert response.status_code == 200

        # Refresh the invitation in the test's transactional session to observe updates
        db_session.refresh(invitation)

        # Verify expiration was extended by 7 days
        expected_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        # Allow some tolerance for execution time
        time_diff = abs((invitation.expires_at - expected_expires_at).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_resend_invitation_fails_without_permission(self, db_session, setup_org_and_invitation):
        """Test that resend invitation fails when user doesn't have permission."""
        org, owner, invitation = setup_org_and_invitation

        # Try to resend as a different user without permission
        response = client.post(
            f"/organizations/{org.id}/invitations/{invitation.id}/resend",
            headers=auth("unauthorized@example.com", "Unauthorized User")
        )

        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    def test_resend_invitation_fails_for_nonexistent_invitation(self, db_session, setup_org_and_invitation):
        """Test that resend invitation fails for nonexistent invitation."""
        org, owner, invitation = setup_org_and_invitation
        fake_invitation_id = uuid.uuid4()

        response = client.post(
            f"/organizations/{org.id}/invitations/{fake_invitation_id}/resend",
            headers=auth(owner.email, owner.display_name)
        )

        assert response.status_code == 404
        assert "Invitation not found" in response.json()["detail"]

    def test_resend_invitation_fails_for_wrong_organization(self, db_session, setup_org_and_invitation):
        """Test that resend invitation fails when invitation belongs to different org."""
        org, owner, invitation = setup_org_and_invitation
        fake_org_id = uuid.uuid4()

        response = client.post(
            f"/organizations/{fake_org_id}/invitations/{invitation.id}/resend",
            headers=auth(owner.email, owner.display_name)
        )

        # The permission check happens before invitation lookup, so we get 403 instead of 404
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    @patch('core.services.notification_service.NotificationService.notify_organization_invitation')
    def test_resend_invitation_handles_email_failure_gracefully(self, mock_notify, db_session, setup_org_and_invitation):
        """Test that resend invitation still succeeds even if email sending fails."""
        org, owner, invitation = setup_org_and_invitation

        # Mock notification service to raise an exception
        mock_notify.side_effect = Exception("Email service unavailable")

        # Call the resend endpoint
        response = client.post(
            f"/organizations/{org.id}/invitations/{invitation.id}/resend",
            headers=auth(owner.email, owner.display_name)
        )

        # Should still return 200 despite email failure
        assert response.status_code == 200

        # Verify notification service was called (and failed)
        mock_notify.assert_called_once()

        # Verify token was still rotated and expiration updated
        db_session.refresh(invitation)
        assert invitation.token != "original_token_123"  # Token should be rotated
        expected_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        time_diff = abs((invitation.expires_at - expected_expires_at).total_seconds())
        assert time_diff < 60  # Expiration should be updated

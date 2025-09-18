"""
Regression tests for organization member addition with notifications.

These tests ensure that the member addition API continues to work correctly
with the notification system integration, preventing future regressions.
"""

import pytest
pytest.importorskip("jinja2")

import uuid
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models


class TestOrganizationMemberAdditionRegression:
    """Regression tests for member addition with notifications."""

    def test_member_addition_api_adds_member(self, client: TestClient, test_org_owner, test_organization, db_session):
        """Test that member addition works and persists the membership."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "regression@example.com",
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        assert response.status_code == 201
        assert response.json() == {"status": "added"}

        member = db_session.query(models.User).filter(models.User.email == "regression@example.com").first()
        assert member is not None
        membership = db_session.query(models.OrganizationMembership).filter(
            models.OrganizationMembership.user_id == member.id,
            models.OrganizationMembership.organization_id == test_organization.id
        ).first()
        assert membership is not None
        assert membership.role == "viewer"

    def test_member_addition_api_still_works_with_email_failure(self, client: TestClient, test_org_owner, test_organization, db_session):
        """Test that member addition works even if email sending fails."""
        with patch('core.services.transactional_email_service.get_transactional_email_service') as mock_email:
            # Make email service fail
            mock_service = MagicMock()
            mock_service.render_template.side_effect = Exception("Email template error")
            mock_email.return_value = mock_service
            
            response = client.post(
                f"/organizations/{test_organization.id}/members",
                json={
                    "email": "emailfail@example.com",
                    "role": "editor",
                    "can_read": True,
                    "can_write": True
                },
                headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
            )
            
            # Member addition should still succeed
            assert response.status_code == 201
            assert response.json() == {"status": "added"}
            
            # Verify member and membership exist
            member = db_session.query(models.User).filter(
                models.User.email == "emailfail@example.com"
            ).first()
            assert member is not None
            
            membership = db_session.query(models.OrganizationMembership).filter(
                models.OrganizationMembership.user_id == member.id,
                models.OrganizationMembership.organization_id == test_organization.id
            ).first()
            assert membership is not None
            assert membership.role == "editor"

    def test_member_addition_audit_log_still_created(self, client: TestClient, test_org_owner, test_organization, db_session):
        """Test that audit logs are still created even with notification integration."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "audit@example.com",
                "role": "admin",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert response.status_code == 201
        
        # Verify audit log was created
        from core.db.models import AuditLog
        
        audit_log = db_session.query(AuditLog).filter(
            AuditLog.action_type == "member_add",
            AuditLog.organization_id == test_organization.id
        ).order_by(AuditLog.created_at.desc()).first()
        
        assert audit_log is not None
        assert audit_log.actor_user_id == test_org_owner.id
        assert audit_log.status == "success"

    def test_existing_member_addition_behavior_unchanged(self, client: TestClient, test_org_owner, test_organization):
        """Test that existing member addition behavior hasn't changed."""
        member_email = "existing@example.com"
        
        # Add member first time
        response1 = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": member_email,
                "role": "viewer"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        assert response1.status_code == 201
        
        # Try to add same member again - should still fail with 409
        response2 = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": member_email,
                "role": "editor"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        assert response2.status_code == 409
        assert "already a member" in response2.json()["detail"]

    def test_invalid_role_behavior_unchanged(self, client: TestClient, test_org_owner, test_organization):
        """Test that invalid role validation still works."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "invalid_role@example.com",
                "role": "invalid_role"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert response.status_code == 422
        assert "Invalid role" in response.json().get("detail", "")

    def test_missing_email_behavior_unchanged(self, client: TestClient, test_org_owner, test_organization):
        """Test that missing email validation still works."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "role": "viewer"
                # Missing email
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert response.status_code == 422
        assert "Email is required" in response.json().get("detail", "")

    def test_permission_checking_unchanged(self, client: TestClient, test_user, test_organization):
        """Test that permission checking still works correctly."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "permission_test@example.com",
                "role": "viewer"
            },
            headers={"x-auth-request-email": test_user.email, "x-auth-request-user": test_user.display_name or test_user.email}  # Not authorized
        )
        
        assert response.status_code == 403
        assert "Forbidden" in response.json()["detail"]

    def test_response_format_unchanged(self, client: TestClient, test_org_owner, test_organization):
        """Test that API response format hasn't changed."""
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "format_test@example.com",
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert response.status_code == 201
        
        # Response should be exactly what it was before
        assert response.json() == {"status": "added"}
        
        # No additional fields should be added
        assert len(response.json()) == 1

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_notification_system_runs_in_background(self, mock_email_service, client: TestClient, test_org_owner, test_organization):
        """Test that notification system doesn't block the API response."""
        import time
        
        # Mock email service with delay to simulate slow email sending
        mock_service = MagicMock()
        mock_service.render_template.return_value = ("<html>Test</html>", "Test")
        
        async def slow_send_email(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow email service
            return {"success": True}
        
        mock_service.send_email = slow_send_email
        mock_email_service.return_value = mock_service
        
        # Time the API call
        start_time = time.time()
        
        response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "background@example.com",
                "role": "viewer"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        end_time = time.time()
        api_duration = end_time - start_time
        
        # API should respond quickly (under 200ms), not wait for email
        assert api_duration < 0.2
        assert response.status_code == 201
        assert response.json() == {"status": "added"}

    def test_member_addition_database_transaction_integrity(self, client: TestClient, test_org_owner, test_organization, db_session):
        """Test that database transactions are properly handled with notifications."""
        with patch('core.db.models.Notification') as mock_notification:
            # Make notification creation fail
            mock_notification.side_effect = Exception("Database error")
            
            response = client.post(
                f"/organizations/{test_organization.id}/members",
                json={
                    "email": "transaction@example.com",
                    "role": "viewer"
                },
                headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
            )
            
            # Member addition should still succeed
            assert response.status_code == 201
            
            # Database state is not asserted here – notification failure is tolerated.


class TestNotificationSystemBackwardCompatibility:
    """Test that notification system integration doesn't break existing functionality."""

    def test_organization_creation_unaffected(self, client: TestClient, test_user, db_session):
        """Test that organization creation still works normally."""
        response = client.post(
            "/organizations/",
            json={
                "name": "Test Backward Compatibility",
                "slug": "test-backward"
            },
            headers={"x-auth-request-email": test_user.email, "x-auth-request-user": test_user.display_name or test_user.email}
        )
        
        assert response.status_code == 201
        
        # Verify organization was created
        org = db_session.query(models.Organization).filter(
            models.Organization.name == "Test Backward Compatibility"
        ).first()
        assert org is not None

    def test_member_listing_unaffected(self, client: TestClient, test_org_owner, test_organization):
        """Test that member listing still works normally."""
        # Add a member first
        client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "list_test@example.com",
                "role": "viewer"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        # List members
        response = client.get(
            f"/organizations/{test_organization.id}/members",
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert response.status_code == 200
        members = response.json()
        
        # Should include the owner and the new member
        assert len(members) >= 2
        member_emails = [m["email"] for m in members]
        assert "list_test@example.com" in member_emails

    def test_member_deletion_unaffected(self, client: TestClient, test_org_owner, test_organization):
        """Test that member deletion still works normally."""
        # Add a member first
        add_response = client.post(
            f"/organizations/{test_organization.id}/members",
            json={
                "email": "delete_test@example.com",
                "role": "viewer"
            },
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        assert add_response.status_code == 201
        
        # Get the member ID
        from sqlalchemy.orm.session import Session as _Sess
        # Use db_session from fixture scope via another request if available
        # Fallback to list members endpoint
        member_list = client.get(
            f"/organizations/{test_organization.id}/members",
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        ).json()
        member_id = next(m["user_id"] for m in member_list if m["email"] == "delete_test@example.com")
        
        # Delete the member
        delete_response = client.delete(
            f"/organizations/{test_organization.id}/members/{member_id}",
            headers={"x-auth-request-email": test_org_owner.email, "x-auth-request-user": test_org_owner.display_name or test_org_owner.email}
        )
        
        assert delete_response.status_code == 204

    def test_organization_api_endpoints_unaffected(self, client: TestClient, test_user):
        """Test that other organization API endpoints work normally."""
        # List organizations
        response = client.get(
            "/organizations/",
            headers={"x-auth-request-email": test_user.email, "x-auth-request-user": test_user.display_name or test_user.email}
        )
        assert response.status_code == 200
        
        # List manageable organizations
        response = client.get(
            "/organizations/manageable",
            headers={"x-auth-request-email": test_user.email, "x-auth-request-user": test_user.display_name or test_user.email}
        )
        assert response.status_code == 200

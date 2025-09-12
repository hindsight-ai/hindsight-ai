import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db import models
from core.db.database import get_db
from core.services.notification_service import NotificationService
from core.services.transactional_email_service import TransactionalEmailService


class TestMemberNotifications:
    """Test notification creation when adding organization members."""
    
    def test_add_member_creates_notification(self, client: TestClient, org_owner_context):
        """Test that adding a member creates an in-app notification."""
        owner, organization = org_owner_context
        
        # Create another user to add as member
        member_email = "newmember@example.com"
        
        # Use headers for authentication
        response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": member_email,
                "role": "editor",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
            
        assert response.status_code == 201
        
        # Check if notification was created for the new member
        # First, find the newly created user
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        assert new_user is not None
        
        # Check for notification
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == "organization_invitation"
        ).first()
        
        assert notification is not None
        assert notification.title == "Welcome to Test Org!"
        assert "added you to the organization" in notification.message
        meta = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
        assert meta.get("organization_id") == str(organization.id)
        assert meta.get("added_by_user_id") == str(owner.id)
        assert meta.get("role") == "editor"

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_add_member_sends_email(self, mock_email_service, client: TestClient, org_owner_context):
        """Test that adding a member triggers email sending."""
        owner, organization = org_owner_context
        
        # Mock the email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test email</html>", "Test email")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-email-id"})
        mock_email_service.return_value = mock_service_instance
        
        new_member_email = "emailtest@example.com"
        
        # Use headers for authentication
        response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": new_member_email,
                "role": "editor",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        assert response.status_code == 201
        
        # Give background thread time to execute
        import time
        time.sleep(0.5)
        
        # Verify email service was called
        mock_email_service.assert_called_once()
        mock_service_instance.render_template.assert_called_once_with(
            "organization_invitation",
            {
                "user_name": new_member_email.split('@')[0],  # Default name from email
                "organization_name": organization.name,
                "invited_by": owner.display_name or owner.email,  # Use display_name if available
                "role": "editor",
                "dashboard_url": "https://hindsight-ai.com/dashboard"
            }
        )

    def test_add_member_with_different_roles(self, client: TestClient, org_owner_context):
        """Test notifications work with different member roles."""
        owner, organization = org_owner_context
        
        roles = ["viewer", "editor", "admin", "owner"]
        
        for i, role in enumerate(roles):
            member_email = f"member{i}@example.com"
            
            response = client.post(
                f"/organizations/{organization.id}/members",
                json={
                    "email": member_email,
                    "role": role,
                    "can_read": True,
                    "can_write": role in ["editor", "admin", "owner"]
                },
                headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
            )
            
            assert response.status_code == 201
            
            # Verify notification contains correct role
            session = client.app.dependency_overrides[get_db]
            db_session = next(session())
            
            member = db_session.query(models.User).filter(models.User.email == member_email).first()
            notification = db_session.query(models.Notification).filter(
                models.Notification.user_id == member.id,
                models.Notification.event_type == "organization_invitation"
            ).first()
            
            assert notification is not None
            assert role in notification.message
            meta = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
            assert meta["role"] == role

    def test_add_existing_member_no_duplicate_notification(self, client: TestClient, org_owner_context):
        """Test that adding an existing member doesn't create duplicate notifications."""
        owner, organization = org_owner_context
        
        member_email = "existing@example.com"
        
        # Add member first time
        first_response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": member_email,
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        assert first_response.status_code == 201
        
        # Get the newly created user
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        member_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        # Count initial notifications
        initial_count = db_session.query(models.Notification).filter(
            models.Notification.user_id == member_user.id
        ).count()
        
        # Try to add member again
        second_response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": member_email,
                "role": "editor",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        # Should return conflict for existing member
        assert second_response.status_code == 409
        
        # Check notification count hasn't increased
        final_count = db_session.query(models.Notification).filter(
            models.Notification.user_id == member_user.id
        ).count()
        
        assert final_count == initial_count  # No duplicate notifications

    def test_add_member_unauthorized_no_notification(self, client: TestClient, user_factory, organization_factory):
        """Test that unauthorized member addition doesn't create notifications."""
        # Create a regular user (not org owner)
        unauthorized_user = user_factory("unauthorized@example.com")
        org = organization_factory("Unauthorized Test Org")
        
        member_email = "victim@example.com"
        
        # Try to add member as unauthorized user
        response = client.post(
            f"/organizations/{org.id}/members",
            json={
                "email": member_email,
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": unauthorized_user.email, "x-auth-request-user": unauthorized_user.display_name or unauthorized_user.email}
        )
        
        # Should be forbidden
        assert response.status_code == 403
        
        # Check no notification was created
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        notifications = db_session.query(models.Notification).filter(
            models.Notification.event_type == "organization_invitation"
        ).count()
        
        assert notifications == 0

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_email_failure_does_not_block_member_addition(self, mock_email_service, client: TestClient, org_owner_context):
        """Test that email failure doesn't prevent member addition."""
        owner, organization = org_owner_context
        
        # Mock email service to raise an exception
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.side_effect = Exception("Email service error")
        mock_email_service.return_value = mock_service_instance
        
        member_email = "emailfail@example.com"
        
        # Use headers for authentication
        response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": member_email,
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        # Member addition should still succeed
        assert response.status_code == 201
        
        # Verify member was actually added
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        assert new_user is not None
        
        # Verify membership was created
        membership = db_session.query(models.OrganizationMembership).filter(
            models.OrganizationMembership.user_id == new_user.id,
            models.OrganizationMembership.organization_id == organization.id
        ).first()
        
        assert membership is not None
        
        # In-app notification should still be created
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == "organization_invitation"
        ).first()
        
        assert notification is not None

    def test_notification_metadata_completeness(self, client: TestClient, org_owner_context):
        """Test that notification metadata contains all expected fields."""
        owner, organization = org_owner_context
        
        member_email = "metadata@example.com"
        
        # Use headers for authentication
        response = client.post(
            f"/organizations/{organization.id}/members",
            json={
                "email": member_email,
                "role": "admin",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        assert response.status_code == 201
        
        # Get the notification
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == "organization_invitation"
        ).first()
        
        assert notification is not None
        
        # Verify all expected metadata fields
        metadata = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
        required_fields = ["organization_id", "added_by_user_id", "role"]
        
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"
        
        assert metadata["organization_id"] == str(organization.id)
        assert metadata["added_by_user_id"] == str(owner.id)
        assert metadata["role"] == "admin"

    def test_member_addition_with_display_names(self, client: TestClient, organization_factory, user_factory):
        """Test notifications use display names when available."""
        # Create organization with owner who has display name
        owner = user_factory("displayowner@example.com")
        owner.display_name = "Display Owner"
        
        org = organization_factory("Display Test Org")
        
        # Create membership for owner
        session = client.app.dependency_overrides[get_db]
        db_session = next(session())
        
        membership = models.OrganizationMembership(
            organization_id=org.id,
            user_id=owner.id,
            role="owner",
            can_read=True,
            can_write=True
        )
        db_session.add(membership)
        db_session.commit()
        
        member_email = "displaymember@example.com"
        
        # Use headers for authentication
        response = client.post(
            f"/organizations/{org.id}/members",
            json={
                "email": member_email,
                "role": "viewer",
                "can_read": True,
                "can_write": False
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )
        
        assert response.status_code == 201
        
        # Get the notification
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == "organization_invitation"
        ).first()
        
        assert notification is not None
        # Notification should reference display name in message
        assert "Display Owner" in notification.message


class TestNotificationService:
    """Test direct notification service functionality in integration context."""
    
    def test_create_notification_success(self, db_session):
        """Test direct notification creation through service."""
        service = NotificationService(db_session)
        
        # Create test user
        user = models.User(
            id=uuid.uuid4(),
            email="service_test@example.com",
            display_name="Service Test User"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create notification
        notification_id = service.create_notification(
            user_id=user.id,
            event_type="organization_invitation",
            title="Test Notification",
            message="This is a test notification",
            metadata={
                "test_key": "test_value",
                "organization_id": str(uuid.uuid4())
            }
        )
        
        assert notification_id is not None
        
        # Verify notification was created
        notification = db_session.query(models.Notification).filter(
            models.Notification.id == notification_id.id
        ).first()
        
        assert notification is not None
        assert notification.user_id == user.id
        assert notification.event_type == "organization_invitation"
        assert notification.title == "Test Notification"
        assert notification.message == "This is a test notification"
        meta = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
        assert meta["test_key"] == "test_value"

    def test_get_notifications_for_user(self, db_session):
        """Test retrieving notifications for a user."""
        service = NotificationService(db_session)
        
        # Create test user
        user = models.User(
            id=uuid.uuid4(),
            email="notifications_test@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create multiple notifications
        for i in range(3):
            service.create_notification(
                user_id=user.id,
                event_type="organization_invitation",
                title=f"Notification {i}",
                message=f"This is notification {i}"
            )
        
        # Get user notifications
        notifications = service.get_user_notifications(user_id=user.id)
        
        assert len(notifications) == 3
        assert all(n.user_id == user.id for n in notifications)

    def test_get_unread_count(self, db_session):
        """Test getting unread notification count."""
        service = NotificationService(db_session)
        
        # Create test user
        user = models.User(
            id=uuid.uuid4(),
            email="unread_test@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create notifications
        for i in range(5):
            service.create_notification(
                user_id=user.id,
                event_type="organization_invitation",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
        
        # Get unread count
        unread_count = service.get_unread_count(user_id=user.id)
        assert unread_count == 5
        
        # Mark one as read
        notifications = service.get_user_notifications(user_id=user.id, limit=1)
        service.mark_notification_read(notification_id=notifications[0].id, user_id=user.id)
        
        # Check count again
        unread_count = service.get_unread_count(user_id=user.id)
        assert unread_count == 4

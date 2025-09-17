import pytest
import uuid
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db import models
from core.services.notification_service import EVENT_ORG_INVITATION, EVENT_ORG_MEMBERSHIP_ADDED
from core.services.notification_service import NotificationService
from core.services.transactional_email_service import TransactionalEmailService


class TestMemberNotifications:
    """Test notification creation when adding organization members."""
    
    def test_add_member_creates_notification(self, client: TestClient, org_owner_context, db_session):
        """Test that adding a member creates an in-app notification."""
        owner, organization = org_owner_context
        
        # Create another user to add as member
        member_email = "newmember@example.com"
        
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
        
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        assert new_user is not None
        
        # Check for notification
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        ).first()
        
        assert notification is not None
        assert "Welcome to" in notification.title
        assert organization.name in notification.message
        meta = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
        assert meta.get("organization_id") == str(organization.id)
        assert meta.get("organization_name") == organization.name
        assert meta.get("added_by_user_id") == str(owner.id)
        assert meta.get("role") == "editor"

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_add_member_sends_email(self, mock_email_service, client: TestClient, org_owner_context, db_session):
        """Test that adding a member triggers email sending."""
        owner, organization = org_owner_context
        
        # Ensure owner has beta access to avoid beta access invitation email
        owner.beta_access_status = 'accepted'
        db_session.commit()
        
        # Mock the email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test email</html>", "Test email")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-email-id"})
        mock_email_service.return_value = mock_service_instance
        
        new_member_email = "emailtest@example.com"
        
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
        mock_service_instance.render_template.assert_called()

    def test_add_member_with_different_roles(self, client: TestClient, org_owner_context, db_session):
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
            member = db_session.query(models.User).filter(models.User.email == member_email).first()
            notification = db_session.query(models.Notification).filter(
                models.Notification.user_id == member.id,
                models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
            ).first()
            
            assert notification is not None
            assert role in notification.message
            meta = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
            assert meta["role"] == role

    def test_add_existing_member_no_duplicate_notification(self, client: TestClient, org_owner_context, db_session):
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

        # Should conflict on re-adding existing member
        assert second_response.status_code == 409
        
        # Check notification count hasn't increased
        final_count = db_session.query(models.Notification).filter(
            models.Notification.user_id == member_user.id
        ).count()
        
        assert final_count == initial_count  # No duplicate notifications

    def test_add_member_unauthorized_no_notification(self, client: TestClient, user_factory, organization_factory, db_session):
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
        notifications = db_session.query(models.Notification).filter(
            models.Notification.event_type == EVENT_ORG_INVITATION
        ).count()
        
        assert notifications == 0

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_email_failure_does_not_block_member_addition(self, mock_email_service, client: TestClient, org_owner_context, db_session):
        """Test that email failure doesn't prevent member addition."""
        owner, organization = org_owner_context
        
        # Ensure owner has beta access to avoid beta access invitation email
        owner.beta_access_status = 'accepted'
        db_session.commit()
        
        # Mock email service to raise an exception
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.side_effect = Exception("Email service error")
        mock_email_service.return_value = mock_service_instance
        
        member_email = "emailfail@example.com"
        
        # Act as owner via headers
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
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        ).first()
        
        assert notification is not None

    def test_notification_metadata_completeness(self, client: TestClient, org_owner_context, db_session):
        """Test that notification metadata contains all expected fields."""
        owner, organization = org_owner_context
        
        member_email = "metadata@example.com"
        
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
        
        new_user = db_session.query(models.User).filter(
            models.User.email == member_email
        ).first()
        
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == new_user.id,
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        ).first()
        
        assert notification is not None
        
        # Verify all expected metadata fields
        metadata = notification.get_metadata() if hasattr(notification, 'get_metadata') else notification.metadata_json
        required_fields = ["organization_id", "organization_name", "added_by_user_id", "role"]
        
        for field in required_fields:
            assert field in metadata, f"Missing metadata field: {field}"
        
        assert metadata["organization_id"] == str(organization.id)
        assert metadata["added_by_user_id"] == str(owner.id)
        assert metadata["role"] == "admin"

    def test_member_addition_with_display_names(self, client: TestClient, organization_factory, user_factory, db_session):
        """Test notifications use display names when available."""
        # Create organization with owner who has display name
        owner = user_factory("displayowner@example.com")
        owner.display_name = "Display Owner"
        
        org = organization_factory("Display Test Org")
        
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
        
        member_email = "displaymember@example.com"
        
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
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        ).first()
        
        assert notification is not None
        # Message should reference the organization name and role
        assert org.name in notification.message


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
        notification = service.create_notification(
            user_id=user.id,
            event_type=EVENT_ORG_MEMBERSHIP_ADDED,
            title="Test Notification",
            message="This is a test notification",
            metadata={
                "test_key": "test_value",
                "organization_id": str(uuid.uuid4())
            }
        )
        
        assert notification is not None
        assert notification.user_id == user.id
        assert notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
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
                event_type=EVENT_ORG_MEMBERSHIP_ADDED,
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
                event_type=EVENT_ORG_MEMBERSHIP_ADDED,
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


class TestNotificationEventTypesAndTemplates:
    """Test that notifications use correct event types and template names."""

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_membership_added_uses_correct_event_type_and_template(self, mock_email_service, client: TestClient, org_owner_context, db_session):
        """Test that membership added notifications use correct event type and template."""
        from core.services.notification_service import EVENT_ORG_MEMBERSHIP_ADDED, TEMPLATE_MEMBERSHIP_ADDED

        owner, organization = org_owner_context
        
        # Ensure owner has beta access to avoid beta access invitation email
        owner.beta_access_status = 'accepted'
        db_session.commit()

        # Mock the email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test email</html>", "Test email")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-email-id"})
        mock_email_service.return_value = mock_service_instance

        new_member_email = "template_test@example.com"

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

        # Verify the correct template was used
        mock_service_instance.render_template.assert_called_once_with(
            TEMPLATE_MEMBERSHIP_ADDED,
            {
                'user_name': 'template_test',
                'organization_name': organization.name,
                'invited_by': owner.display_name or owner.email,
                'role': 'editor',
                'dashboard_url': f'http://localhost:3000/dashboard'
            }
        )

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_role_change_notification_uses_correct_event_type_and_template(self, mock_email_service, client: TestClient, org_owner_context, db_session):
        """Test that role change notifications use correct event type and template."""
        from core.services.notification_service import EVENT_ORG_ROLE_CHANGED, TEMPLATE_ROLE_CHANGED

        owner, organization = org_owner_context
        
        # Ensure owner has beta access to avoid beta access invitation email
        owner.beta_access_status = 'accepted'
        db_session.commit()

        # Create a member first
        member_email = "role_change_test@example.com"
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
        assert response.status_code == 201

        # Get the member user
        member = db_session.query(models.User).filter(models.User.email == member_email).first()
        assert member is not None

        # Mock the email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test email</html>", "Test email")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-email-id"})
        mock_email_service.return_value = mock_service_instance

        # Change the member's role
        response = client.put(
            f"/organizations/{organization.id}/members/{member.id}",
            json={
                "role": "admin",
                "can_read": True,
                "can_write": True
            },
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )

        assert response.status_code == 200

        # Give background thread time to execute
        import time
        time.sleep(0.5)

        # Verify the correct template was used for role change
        mock_service_instance.render_template.assert_called_once_with(
            TEMPLATE_ROLE_CHANGED,
            {
                'organization_name': organization.name,
                'old_role': 'viewer',
                'new_role': 'admin',
                'changed_by_name': owner.display_name or owner.email,
                'date_changed': ANY,  # Date will be generated dynamically
                'current_year': ANY,  # Year will be current year
            }
        )

        # Verify notification was created with correct event type
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == member.id,
            models.Notification.event_type == EVENT_ORG_ROLE_CHANGED
        ).first()
        assert notification is not None
        assert "Role changed" in notification.title
        assert "viewer" in notification.message
        assert "admin" in notification.message

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_membership_removal_notification_uses_correct_event_type_and_template(self, mock_email_service, client: TestClient, org_owner_context, db_session):
        """Test that membership removal notifications use correct event type and template."""
        from core.services.notification_service import EVENT_ORG_MEMBERSHIP_REMOVED, TEMPLATE_MEMBERSHIP_REMOVED

        owner, organization = org_owner_context
        
        # Ensure owner has beta access to avoid beta access invitation email
        owner.beta_access_status = 'accepted'
        db_session.commit()

        # Create a member first
        member_email = "removal_test@example.com"
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

        # Get the member user
        member = db_session.query(models.User).filter(models.User.email == member_email).first()
        assert member is not None

        # Mock the email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test email</html>", "Test email")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-email-id"})
        mock_email_service.return_value = mock_service_instance

        # Remove the member
        response = client.delete(
            f"/organizations/{organization.id}/members/{member.id}",
            headers={"x-auth-request-email": owner.email, "x-auth-request-user": owner.display_name or owner.email}
        )

        assert response.status_code == 204

        # Give background thread time to execute
        import time
        time.sleep(0.5)

        # Verify the correct template was used for membership removal
        mock_service_instance.render_template.assert_called_once_with(
            TEMPLATE_MEMBERSHIP_REMOVED,
            {
                'organization_name': organization.name,
                'removed_by_name': owner.display_name or owner.email,
                'date_removed': ANY,  # Date will be generated dynamically
                'current_year': ANY,  # Year will be current year
            }
        )

        # Verify notification was created with correct event type
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == member.id,
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_REMOVED
        ).first()
        assert notification is not None
        assert "Removed from" in notification.title
        assert organization.name in notification.title

    def test_membership_added_notification_created_with_correct_event_type(self, client: TestClient, org_owner_context, db_session):
        """Test that membership added creates notification with correct event type."""
        from core.services.notification_service import EVENT_ORG_MEMBERSHIP_ADDED

        owner, organization = org_owner_context

        # Create a member
        member_email = "event_type_test@example.com"
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

        # Get the member user
        member = db_session.query(models.User).filter(models.User.email == member_email).first()
        assert member is not None

        # Verify notification was created with correct event type
        notification = db_session.query(models.Notification).filter(
            models.Notification.user_id == member.id,
            models.Notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        ).first()

        assert notification is not None
        assert notification.event_type == EVENT_ORG_MEMBERSHIP_ADDED
        assert "Welcome to" in notification.title
        assert organization.name in notification.title

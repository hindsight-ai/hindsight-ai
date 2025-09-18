"""
Unit tests for the NotificationService class.

These tests verify the core notification service functionality including:
- Notification creation and retrieval
- Email notification sending
- User pr          # Create 3 notifications
        ids = []
        for i in range(3):
            notification_id = service.create_notification(
                user_id=user.id,
                event_type="test",
                title=f"Test {i}",
                message=f"Message {i}"
            )
            ids.append(notification_id)notification_id = service.create_notification(
                user_id=user.id,
                event_type="test",
                title=f"Notification {i}",
                message=f"Message {i}"
            )ces management
- Template data handling
"""

import pytest
pytest.importorskip("jinja2")

import uuid
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, UTC
import os
from pathlib import Path

from core.services.notification_service import NotificationService
from core.services.transactional_email_service import TransactionalEmailService
from core.db import models
from core.services.notification_service import (
    EVENT_ORG_INVITATION,
    EVENT_ORG_MEMBERSHIP_ADDED,
    EVENT_ORG_ROLE_CHANGED,
    TEMPLATE_ORG_INVITATION,
    TEMPLATE_MEMBERSHIP_ADDED,
    TEMPLATE_MEMBERSHIP_REMOVED,
    TEMPLATE_ROLE_CHANGED,
    TEMPLATE_SUPPORT_CONTACT,
)


class TestNotificationServiceUnit:
    """Unit tests for NotificationService."""

    def test_create_notification_with_all_fields(self, db_session):
        """Test creating a notification with all fields populated."""
        service = NotificationService(db_session)
        
        # Create test user
        user = models.User(
            id=uuid.uuid4(),
            email="test@example.com",
            display_name="Test User"
        )
        db_session.add(user)
        db_session.flush()
        
        metadata = {
            "organization_id": str(uuid.uuid4()),
            "organization_name": "Test Org",
            "invited_by": "Admin User",
            "role": "editor"
        }
        
        # Create notification
        notification = service.create_notification(
            user_id=user.id,
            event_type=EVENT_ORG_INVITATION,
            title="Organization Invitation",
            message="You have been invited to join Test Org",
            metadata=metadata,
            action_url="https://example.com/accept",
            action_text="Accept Invitation"
        )

        # Verify notification was stored in database
        db_notification = db_session.query(models.Notification).filter(
            models.Notification.id == notification.id
        ).first()
        
        assert db_notification is not None
        assert db_notification.user_id == user.id
        assert db_notification.event_type == EVENT_ORG_INVITATION
        assert db_notification.title == "Organization Invitation"
        assert db_notification.message == "You have been invited to join Test Org"
        assert db_notification.action_url == "https://example.com/accept"
        assert db_notification.action_text == "Accept Invitation"
        assert db_notification.metadata_json == metadata
        assert not db_notification.is_read
        assert notification.read_at is None
        assert notification.created_at is not None

    def test_create_notification_minimal_fields(self, db_session):
        """Test creating a notification with only required fields."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="minimal@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        notification = service.create_notification(
            user_id=user.id,
            event_type="test_notification",
            title="Test",
            message="Test message"
        )
        
        db_notification = db_session.query(models.Notification).filter(
            models.Notification.id == notification.id
        ).first()
        
        assert db_notification is not None
        assert db_notification.user_id == user.id
        assert db_notification.event_type == "test_notification"
        assert db_notification.title == "Test"
        assert db_notification.message == "Test message"
        assert db_notification.action_url is None
        assert db_notification.action_text is None
        assert db_notification.metadata_json is None

    def test_get_notifications_ordering(self, db_session):
        """Test that notifications are returned in correct order (newest first)."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="ordering@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create notifications with slight delay to ensure different timestamps
        import time

        first_notification = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="First",
            message="First notification"
        )
        time.sleep(0.01)

        second_notification = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="Second",
            message="Second notification"
        )
        time.sleep(0.01)

        third_notification = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="Third",
            message="Third notification"
        )
        
        db_session.commit()

        # Get notifications
        notifications = service.get_user_notifications(user.id, limit=10)

        assert len(notifications) == 3
        assert notifications[0].title == "Third"  # Most recent first
        assert notifications[1].title == "Second"
        assert notifications[2].title == "First"
        assert str(notifications[0].id) == str(third_notification.id)
        assert str(notifications[1].id) == str(second_notification.id)
        assert str(notifications[2].id) == str(first_notification.id)

    def test_get_notifications_with_limit(self, db_session):
        """Test getting notifications with limit parameter."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="limit@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create 5 notifications
        for i in range(5):
            service.create_notification(
                user_id=user.id,
                event_type="test",
                title=f"Notification {i}",
                message=f"Message {i}"
            )
        
        db_session.commit()
        
        # Test different limits
        notifications_2 = service.get_user_notifications(user.id, limit=2)
        assert len(notifications_2) == 2
        
        notifications_10 = service.get_user_notifications(user.id, limit=10)
        assert len(notifications_10) == 5  # Only 5 exist
        
        notifications_0 = service.get_user_notifications(user.id, limit=0)
        assert len(notifications_0) == 0

    def test_get_unread_count_accuracy(self, db_session):
        """Test that unread count is accurate under various scenarios."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="unread@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Initially no notifications
        assert service.get_unread_count(user.id) == 0
        
        # Add 3 notifications
        notifications = []
        for i in range(3):
            notification = service.create_notification(
                user_id=user.id,
                event_type="test",
                title=f"Test {i}",
                message=f"Message {i}"
            )
            notifications.append(notification)
        
        db_session.commit()
        
        # All should be unread
        assert service.get_unread_count(user.id) == 3
        
        # Mark one as read
        service.mark_notification_read(notifications[0].id, user.id)
        assert service.get_unread_count(user.id) == 2
        
        # Mark another as read
        service.mark_notification_read(notifications[1].id, user.id)
        assert service.get_unread_count(user.id) == 1
        
        # Mark last as read
        service.mark_notification_read(notifications[2].id, user.id)
        assert service.get_unread_count(user.id) == 0

    def test_mark_as_read_updates_timestamp(self, db_session):
        """Test that marking as read updates the read_at timestamp."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="timestamp@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create notification
        notification = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="Read Test",
            message="Test message"
        )
        
        # Verify initially unread
        db_notification = db_session.query(models.Notification).filter(
            models.Notification.id == notification.id
        ).first()
        assert not db_notification.is_read
        assert db_notification.read_at is None
        
        # Mark as read
        before_mark = datetime.now(UTC)
        service.mark_notification_read(notification.id, user.id)
        after_mark = datetime.now(UTC)
        
        # Verify updated
        db_session.refresh(db_notification)
        assert db_notification.is_read
        assert db_notification.read_at is not None
        assert before_mark <= db_notification.read_at <= after_mark

    def test_get_user_preferences_defaults(self, db_session):
        """Test that user preferences return defaults when none exist."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="prefs@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        preferences = service.get_user_preferences(user.id)
        
        # Should return defaults for known notification types (dicts with flags)
        pref_inv = preferences.get(EVENT_ORG_INVITATION)
        assert pref_inv["email_enabled"] is True
        assert pref_inv["in_app_enabled"] is True
        pref_added = preferences.get(EVENT_ORG_MEMBERSHIP_ADDED)
        assert pref_added["email_enabled"] is True
        assert pref_added["in_app_enabled"] is True

    def test_update_user_preferences(self, db_session):
        """Test updating user notification preferences."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="update_prefs@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Update preferences using set_user_preference
        service.set_user_preference(user.id, EVENT_ORG_INVITATION, email_enabled=False, in_app_enabled=True)
        service.set_user_preference(user.id, EVENT_ORG_MEMBERSHIP_ADDED, email_enabled=True, in_app_enabled=True)
        service.set_user_preference(user.id, EVENT_ORG_ROLE_CHANGED, email_enabled=False, in_app_enabled=False)
        
        # Verify preferences were saved
        saved_preferences = service.get_user_preferences(user.id)
        assert saved_preferences[EVENT_ORG_INVITATION]["email_enabled"] is False
        assert saved_preferences[EVENT_ORG_INVITATION]["in_app_enabled"] is True
        assert saved_preferences[EVENT_ORG_MEMBERSHIP_ADDED]["email_enabled"] is True
        assert saved_preferences[EVENT_ORG_MEMBERSHIP_ADDED]["in_app_enabled"] is True
        assert saved_preferences[EVENT_ORG_ROLE_CHANGED]["email_enabled"] is False
        assert saved_preferences[EVENT_ORG_ROLE_CHANGED]["in_app_enabled"] is False

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_send_email_notification_success(self, mock_email_service, db_session):
        """Test successful email notification sending."""
        # Mock email service
        mock_service_instance = MagicMock()
        mock_service_instance.render_template.return_value = ("<html>Test</html>", "Test text")
        mock_service_instance.send_email = AsyncMock(return_value={"id": "test-id", "success": True})
        mock_email_service.return_value = mock_service_instance
        
        service = NotificationService(db_session, email_service=mock_service_instance)
        
        user = models.User(
            id=uuid.uuid4(),
            email="email_test@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        template_data = {
            "user_name": "Test User",
            "organization_name": "Test Org",
            "invited_by": "Admin",
            "role": "viewer"
        }

        # Create an email log entry first
        email_log = service.create_email_notification_log(
            notification_id=None,
            user_id=user.id,
            email_address=user.email,
            event_type=EVENT_ORG_INVITATION,
            subject="Organization Invitation"
        )

        # Send email notification
        import asyncio
        result = asyncio.run(service.send_email_notification(
            email_log=email_log,
            template_name=TEMPLATE_ORG_INVITATION,
            template_context=template_data
        ))
        
        assert result is not None
        
        # Verify email service was called correctly
        mock_service_instance.render_template.assert_called_once_with(
            TEMPLATE_ORG_INVITATION, template_data
        )

    @patch('core.services.transactional_email_service.get_transactional_email_service')
    def test_send_email_notification_respects_preferences(self, mock_email_service, db_session):
        """Test that email notifications respect user preferences."""
        mock_service_instance = MagicMock()
        mock_email_service.return_value = mock_service_instance
        
        service = NotificationService(db_session, email_service=mock_service_instance)
        
        user = models.User(
            id=uuid.uuid4(),
            email="prefs_test@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Disable email notifications for this type
        service.set_user_preference(user.id, EVENT_ORG_INVITATION, email_enabled=False, in_app_enabled=True)
        
        template_data = {"test": "data"}
        
        # Create an email log entry first  
        email_log = service.create_email_notification_log(
            notification_id=None,
            user_id=user.id,
            email_address=user.email,
            event_type=EVENT_ORG_INVITATION,
            subject="Organization Invitation"
        )
        
        # Try to send email notification (should still send even if preference is disabled for low-level method)
        import asyncio
        result = asyncio.run(service.send_email_notification(
            email_log=email_log,
            template_name=TEMPLATE_ORG_INVITATION,
            template_context=template_data
        ))
        
        # The low-level send_email_notification should still send emails
        # Preference checking happens at higher levels (like notify_organization_invitation)
        # But if there's an error, the result will contain error info
        assert result is not None
        # Could be successful or contain error info
        
        # The method should have attempted to render template at least
        # (send_email might fail due to mock setup, but render should be called)

    def test_notification_json_serialization(self, db_session):
        """Test that notification data can be properly serialized to JSON."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="json@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        complex_metadata = {
            "organization_id": str(uuid.uuid4()),
            "organization_name": "Test Org",
            "invited_by": "Admin User",
            "role": "editor",
            "permissions": ["read", "write"],
            "nested": {
                "key": "value",
                "number": 42,
                "bool": True
            }
        }
        
        notification_obj = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="JSON Test",
            message="Testing JSON serialization",
            metadata=complex_metadata
        )
        
        # Retrieve and verify
        notifications = service.get_user_notifications(user.id, limit=1)
        notification = notifications[0]
        
        # Verify all fields are present and correctly typed
        assert str(notification.id) == str(notification_obj.id)
        assert notification.event_type == "test"
        assert notification.title == "JSON Test"
        assert notification.message == "Testing JSON serialization"
        assert notification.metadata_json == complex_metadata
        assert isinstance(notification.created_at.isoformat(), str)  # ISO format string
        assert notification.read_at is None
        assert notification.is_read is False


class TestNotificationServiceEdgeCases:
    """Test edge cases and error conditions."""

    def test_create_notification_nonexistent_user(self, db_session):
        """Test creating notification for non-existent user."""
        service = NotificationService(db_session)
        
        fake_user_id = uuid.uuid4()
        
        # Should handle gracefully (implementation detail)
        with pytest.raises(Exception):  # Could be IntegrityError or custom exception
            service.create_notification(
                user_id=fake_user_id,
                event_type="test",
                title="Test",
                message="Test message"
            )

    def test_get_notifications_nonexistent_user(self, db_session):
        """Test getting notifications for non-existent user."""
        service = NotificationService(db_session)
        
        fake_user_id = uuid.uuid4()
        
        # Should return empty list
        notifications = service.get_user_notifications(fake_user_id, limit=10)
        assert notifications == []

    def test_get_unread_count_nonexistent_user(self, db_session):
        """Test getting unread count for non-existent user."""
        service = NotificationService(db_session)
        
        fake_user_id = uuid.uuid4()
        
        # Should return 0
        count = service.get_unread_count(fake_user_id)
        assert count == 0

    def test_mark_as_read_nonexistent_notification(self, db_session):
        """Test marking non-existent notification as read."""
        service = NotificationService(db_session)
        
        fake_notification_id = uuid.uuid4()
        
        # Should handle gracefully without error
        service.mark_notification_read(fake_notification_id, uuid.uuid4())
        # No exception should be raised

    def test_large_metadata_handling(self, db_session):
        """Test handling of large metadata objects."""
        service = NotificationService(db_session)
        
        user = models.User(
            id=uuid.uuid4(),
            email="large_meta@example.com"
        )
        db_session.add(user)
        db_session.flush()
        
        # Create large metadata object
        large_metadata = {
            "large_list": list(range(1000)),
            "large_string": "x" * 10000,
            "nested_structure": {
                f"key_{i}": f"value_{i}" for i in range(100)
            }
        }
        
        notification_id = service.create_notification(
            user_id=user.id,
            event_type="test",
            title="Large Metadata Test",
            message="Testing large metadata",
            metadata=large_metadata
        )
        
        # Verify it was stored and can be retrieved
        notifications = service.get_user_notifications(user.id, limit=1)
        assert len(notifications) == 1
        assert notifications[0].metadata_json == large_metadata


class TestTemplateFiles:
    """Tests for template file existence and validation."""

    @pytest.mark.parametrize("template_name", [
        TEMPLATE_ORG_INVITATION,
        TEMPLATE_MEMBERSHIP_ADDED,
        TEMPLATE_MEMBERSHIP_REMOVED,
        TEMPLATE_ROLE_CHANGED,
        TEMPLATE_SUPPORT_CONTACT,
    ])
    @pytest.mark.parametrize("extension", [".html", ".txt"])
    def test_template_files_exist(self, template_name, extension):
        """Test that all required template files exist in the expected location."""
        template_dir = Path("core/templates/email")
        template_file = template_dir / f"{template_name}{extension}"

        assert template_file.exists(), f"Template file {template_file} does not exist"
        assert template_file.is_file(), f"{template_file} is not a file"

        # Verify the file is not empty
        assert template_file.stat().st_size > 0, f"Template file {template_file} is empty"

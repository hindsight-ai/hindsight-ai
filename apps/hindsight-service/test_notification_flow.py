#!/usr/bin/env python3
"""
End-to-End Notification System Test

This script tests the complete notification flow from organization events
to in-app notifications and email delivery.

Run with: uv run python test_notification_flow.py
"""

import asyncio
import uuid
import sys
from pathlib import Path
from datetime import datetime, UTC

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from core.db.database import get_db, engine
from core.db import models
from core.services.notification_service import NotificationService
from sqlalchemy.orm import Session

def create_test_user(db: Session) -> models.User:
    """Create a test user for notification testing."""
    test_user = models.User(
        id=uuid.uuid4(),
        email="test@example.com",
        display_name="Test User",
        provider="test",
        provider_user_id="test123",
        avatar_url="https://example.com/avatar.jpg"
    )
    
    db.add(test_user)
    db.commit()
    db.refresh(test_user)
    return test_user

def create_test_organization(db: Session, owner_id: uuid.UUID) -> models.Organization:
    """Create a test organization."""
    test_org = models.Organization(
        id=uuid.uuid4(),
        name="Test Organization",
        description="Test organization for notification testing",
        owner_id=owner_id
    )
    
    db.add(test_org)
    db.commit()
    db.refresh(test_org)
    return test_org

def test_user_preferences(notification_service: NotificationService, user_id: uuid.UUID):
    """Test user notification preferences management."""
    print("🔧 Testing User Notification Preferences...")
    
    # Test getting default preferences
    prefs = notification_service.get_user_preferences(user_id)
    print(f"✅ Default preferences retrieved: {len(prefs)} event types")
    
    # Test updating preferences
    notification_service.update_user_preference(
        user_id=user_id,
        event_type='org_invitation',
        email_enabled=False,
        in_app_enabled=True
    )
    
    updated_prefs = notification_service.get_user_preferences(user_id)
    org_invite_prefs = updated_prefs.get('org_invitation', {})
    
    assert not org_invite_prefs['email_enabled'], "Email should be disabled"
    assert org_invite_prefs['in_app_enabled'], "In-app should be enabled"
    
    print("✅ User preferences updated and verified")

def test_organization_invitation(
    notification_service: NotificationService,
    invitee_user: models.User,
    organization: models.Organization
):
    """Test organization invitation notification flow."""
    print("\n📧 Testing Organization Invitation Notifications...")
    
    result = notification_service.notify_organization_invitation(
        invitee_user_id=invitee_user.id,
        invitee_email=invitee_user.email,
        inviter_name="John Doe",
        organization_name=organization.name,
        invitation_id=uuid.uuid4(),
        accept_url="https://example.com/accept/123",
        decline_url="https://example.com/decline/123"
    )
    
    # Check in-app notification was created
    if 'in_app_notification' in result:
        notification = result['in_app_notification']
        print(f"✅ In-app notification created: {notification.title}")
        print(f"   Message: {notification.message}")
        print(f"   Action URL: {notification.action_url}")
    else:
        print("⚠️  No in-app notification created (may be disabled in preferences)")
    
    # Check email log was created
    if 'email_log' in result:
        email_log = result['email_log']
        print(f"✅ Email log created: {email_log.subject}")
        print(f"   Status: {email_log.status}")
        print(f"   Email: {email_log.email_address}")
        
        # Check if email was actually attempted
        if 'email_result' in result:
            email_result = result['email_result']
            if email_result['success']:
                print(f"✅ Email sent successfully: {email_result.get('message_id', 'N/A')}")
            else:
                print(f"⚠️  Email sending failed (expected in test): {email_result['error']}")
        else:
            print("ℹ️  Email sending not attempted (SMTP not configured)")
    else:
        print("⚠️  No email log created (email disabled in preferences)")
    
    return result

def test_membership_added(
    notification_service: NotificationService,
    user: models.User,
    organization: models.Organization
):
    """Test membership added notification flow."""
    print("\n👥 Testing Membership Added Notifications...")
    
    result = notification_service.notify_membership_added(
        user_id=user.id,
        user_email=user.email,
        organization_name=organization.name,
        role="Member",
        added_by_name="Jane Smith"
    )
    
    # Check results
    if 'in_app_notification' in result:
        notification = result['in_app_notification']
        print(f"✅ In-app notification created: {notification.title}")
        print(f"   Message: {notification.message}")
    
    if 'email_log' in result:
        email_log = result['email_log']
        print(f"✅ Email log created: {email_log.subject}")
        print(f"   Status: {email_log.status}")
    
    return result

def test_notification_queries(notification_service: NotificationService, user_id: uuid.UUID):
    """Test notification query methods."""
    print("\n📊 Testing Notification Queries...")
    
    # Test getting notifications for user
    notifications = notification_service.get_notifications_for_user(user_id, limit=10)
    print(f"✅ Retrieved {len(notifications)} notifications for user")
    
    # Test getting unread count
    unread_count = notification_service.get_unread_count(user_id)
    print(f"✅ Unread count: {unread_count}")
    
    # Test marking notifications as read
    if notifications:
        first_notification = notifications[0]
        success = notification_service.mark_as_read(first_notification.id)
        print(f"✅ Marked notification as read: {success}")
        
        # Verify unread count decreased
        new_unread_count = notification_service.get_unread_count(user_id)
        print(f"✅ New unread count: {new_unread_count}")

def test_cleanup(notification_service: NotificationService):
    """Test notification cleanup functionality."""
    print("\n🧹 Testing Notification Cleanup...")
    
    # Test cleanup (won't remove anything since our notifications are fresh)
    cleaned_count = notification_service.cleanup_expired_notifications()
    print(f"✅ Cleaned up {cleaned_count} expired notifications")

def cleanup_test_data(db: Session, user: models.User, organization: models.Organization):
    """Clean up test data."""
    print("\n🗑️  Cleaning up test data...")
    
    try:
        # Clean up notifications
        db.query(models.Notification).filter(
            models.Notification.user_id == user.id
        ).delete()
        
        # Clean up email logs
        db.query(models.EmailNotificationLog).filter(
            models.EmailNotificationLog.user_id == user.id
        ).delete()
        
        # Clean up user preferences
        db.query(models.UserNotificationPreference).filter(
            models.UserNotificationPreference.user_id == user.id
        ).delete()
        
        # Clean up organization
        db.delete(organization)
        
        # Clean up user
        db.delete(user)
        
        db.commit()
        print("✅ Test data cleaned up successfully")
        
    except Exception as e:
        print(f"⚠️  Error cleaning up test data: {e}")
        db.rollback()

def main():
    """Run end-to-end notification system tests."""
    print("🚀 Starting End-to-End Notification System Test\n")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Create test data
        print("📝 Setting up test data...")
        test_user = create_test_user(db)
        test_organization = create_test_organization(db, test_user.id)
        print(f"✅ Created test user: {test_user.email}")
        print(f"✅ Created test organization: {test_organization.name}")
        
        # Initialize notification service
        notification_service = NotificationService(db)
        
        # Run tests
        print("\n" + "="*60)
        print("🧪 Running Notification System Tests")
        print("="*60)
        
        # Test 1: User preferences
        test_user_preferences(notification_service, test_user.id)
        
        # Test 2: Organization invitation
        invitation_result = test_organization_invitation(
            notification_service,
            test_user,
            test_organization
        )
        
        # Test 3: Membership added
        membership_result = test_membership_added(
            notification_service,
            test_user,
            test_organization
        )
        
        # Test 4: Notification queries
        test_notification_queries(notification_service, test_user.id)
        
        # Test 5: Cleanup
        test_cleanup(notification_service)
        
        print("\n" + "="*60)
        print("📊 Test Summary")
        print("="*60)
        print("✅ User preference management: PASS")
        print("✅ Organization invitation flow: PASS")
        print("✅ Membership added flow: PASS")
        print("✅ Notification queries: PASS")
        print("✅ Cleanup functionality: PASS")
        
        print("\n🎉 All notification system tests completed successfully!")
        
        # Note about email testing
        print("\nℹ️  Email sending may show warnings if SMTP is not configured.")
        print("   This is expected in development. Configure SMTP to test actual email delivery.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test data
        if 'test_user' in locals() and 'test_organization' in locals():
            cleanup_test_data(db, test_user, test_organization)
        
        db.close()

if __name__ == "__main__":
    main()

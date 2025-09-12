"""
Notification API Endpoints

Provides REST API for managing notifications and user preferences.
Supports both in-app notifications and email notification preferences.
"""

from typing import List, Dict, Any
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import schemas
from core.api.deps import get_current_user_context
from core.services.notification_service import NotificationService


router = APIRouter(tags=["notifications"])


@router.get("/", response_model=schemas.NotificationListResponse)
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Get notifications for the current user.
    
    - **unread_only**: If true, only return unread notifications
    - **limit**: Maximum number of notifications to return (default 50)
    """
    user, current_user = user_context
    
    service = NotificationService(db)
    notifications = service.get_user_notifications(
        user_id=user.id,
        unread_only=unread_only,
        limit=limit
    )
    
    unread_count = service.get_unread_count(user.id)
    
    return schemas.NotificationListResponse(
        notifications=notifications,
        unread_count=unread_count,
        total_count=len(notifications)
    )


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Mark a specific notification as read.
    """
    user, current_user = user_context
    
    service = NotificationService(db)
    success = service.mark_notification_read(notification_id, user.id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )


@router.get("/stats", response_model=schemas.NotificationStatsResponse)
def get_notification_stats(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Get notification statistics for the current user.
    """
    user, current_user = user_context
    
    service = NotificationService(db)
    unread_count = service.get_unread_count(user.id)
    recent_notifications = service.get_user_notifications(
        user_id=user.id,
        unread_only=False,
        limit=5
    )
    
    return schemas.NotificationStatsResponse(
        unread_count=unread_count,
        total_notifications=len(recent_notifications),
        recent_notifications=recent_notifications
    )


@router.get("/preferences", response_model=schemas.NotificationPreferencesResponse)
def get_notification_preferences(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Get notification preferences for the current user.
    """
    user, current_user = user_context
    
    service = NotificationService(db)
    preferences = service.get_user_preferences(user.id)
    
    return schemas.NotificationPreferencesResponse(preferences=preferences)


@router.put("/preferences/{event_type}", response_model=schemas.UserNotificationPreference)
def update_notification_preference(
    event_type: str,
    preference_update: schemas.UserNotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Update notification preferences for a specific event type.
    
    Available event types:
    - org_invitation
    - org_membership_added
    - org_membership_removed
    - org_role_changed
    - org_invitation_accepted
    - org_invitation_declined
    """
    user, current_user = user_context
    
    # Validate event type
    valid_event_types = {
        'org_invitation',
        'org_membership_added', 
        'org_membership_removed',
        'org_role_changed',
        'org_invitation_accepted',
        'org_invitation_declined'
    }
    
    if event_type not in valid_event_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid event type. Must be one of: {', '.join(valid_event_types)}"
        )
    
    service = NotificationService(db)
    
    # Get current preferences to use as defaults
    current_prefs = service.get_user_preferences(user.id)
    current_event_prefs = current_prefs.get(event_type, {'email_enabled': True, 'in_app_enabled': True})
    
    # Use provided values or current values as defaults
    email_enabled = preference_update.email_enabled 
    if email_enabled is None:
        email_enabled = current_event_prefs['email_enabled']
        
    in_app_enabled = preference_update.in_app_enabled
    if in_app_enabled is None:
        in_app_enabled = current_event_prefs['in_app_enabled']
    
    updated_preference = service.set_user_preference(
        user_id=user.id,
        event_type=event_type,
        email_enabled=email_enabled,
        in_app_enabled=in_app_enabled
    )
    
    return updated_preference


# Admin/Debug endpoints (for development and testing)
@router.post("/test/create", response_model=schemas.Notification)
def create_test_notification(
    notification_data: schemas.NotificationCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Create a test notification for the current user.
    This endpoint is for development/testing purposes.
    """
    user, current_user = user_context
    
    service = NotificationService(db)
    notification = service.create_notification(
        user_id=user.id,
        event_type=notification_data.event_type,
        title=notification_data.title,
        message=notification_data.message,
        action_url=notification_data.action_url,
        action_text=notification_data.action_text,
        metadata=notification_data.metadata,
        expires_days=notification_data.expires_days or 30
    )
    
    return notification


@router.delete("/cleanup/expired")
def cleanup_expired_notifications(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context)
):
    """
    Clean up expired notifications.
    This endpoint is for admin/maintenance purposes.
    """
    user, current_user = user_context
    
    # Basic admin check - in a real app you'd want proper role-based access
    if not user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    service = NotificationService(db)
    count = service.cleanup_expired_notifications()
    
    return {"message": f"Cleaned up {count} expired notifications"}

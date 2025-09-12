import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict


class UserNotificationPreferenceBase(BaseModel):
    user_id: uuid.UUID
    event_type: str
    email_enabled: bool = True
    in_app_enabled: bool = True


class UserNotificationPreferenceCreate(UserNotificationPreferenceBase):
    pass


class UserNotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None


class UserNotificationPreference(UserNotificationPreferenceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationBase(BaseModel):
    user_id: uuid.UUID
    event_type: str
    title: str
    message: str
    action_url: Optional[str] = None
    action_text: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    expires_days: Optional[int] = 30


class Notification(NotificationBase):
    id: uuid.UUID
    is_read: bool
    read_at: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


class EmailNotificationLogBase(BaseModel):
    notification_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    email_address: str
    event_type: str
    subject: str
    status: str = 'pending'


class EmailNotificationLogCreate(EmailNotificationLogBase):
    pass


class EmailNotificationLog(EmailNotificationLogBase):
    id: uuid.UUID
    provider_message_id: Optional[str]
    error_message: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    bounced_at: Optional[datetime]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    notifications: List[Notification]
    unread_count: int
    total_count: int


class NotificationPreferencesResponse(BaseModel):
    preferences: Dict[str, Dict[str, bool]]


class NotificationStatsResponse(BaseModel):
    unread_count: int
    total_notifications: int
    recent_notifications: List[Notification]


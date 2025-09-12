import uuid
from sqlalchemy import Column, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, now_utc


class UserNotificationPreference(Base):
    __tablename__ = 'user_notification_preferences'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    email_enabled = Column(Boolean, nullable=False, default=True)
    in_app_enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False)

    __table_args__ = (
        Index('idx_user_notification_preferences_user_id', 'user_id'),
        Index('idx_user_notification_preferences_unique', 'user_id', 'event_type', unique=True),
    )


class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    event_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)
    action_text = Column(String(100), nullable=True)
    metadata_json = Column('metadata', JSONB, nullable=True)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('idx_notifications_user_id_created_at', 'user_id', 'created_at'),
        Index('idx_notifications_user_id_is_read', 'user_id', 'is_read'),
        Index('idx_notifications_expires_at', 'expires_at'),
        Index('idx_notifications_event_type', 'event_type'),
    )

    def get_metadata(self):
        return self.metadata_json

    def set_metadata(self, value):
        self.metadata_json = value


class EmailNotificationLog(Base):
    __tablename__ = 'email_notification_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey('notifications.id', ondelete='CASCADE'), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email_address = Column(String(320), nullable=False)
    event_type = Column(String(50), nullable=False)
    subject = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    provider_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    __table_args__ = (
        Index('idx_email_notification_logs_user_id_created_at', 'user_id', 'created_at'),
        Index('idx_email_notification_logs_status', 'status'),
        Index('idx_email_notification_logs_event_type', 'event_type'),
        Index('idx_email_notification_logs_notification_id', 'notification_id'),
    )


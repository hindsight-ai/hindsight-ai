import uuid
from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, now_utc


class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=True)
    is_superadmin = Column(Boolean, nullable=False, default=False)
    auth_provider = Column(String, nullable=True)
    external_subject = Column(String, nullable=True)
    # Beta access status: 'accepted'|'pending'|'denied'
    beta_access_status = Column(String, nullable=False, default='pending')
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


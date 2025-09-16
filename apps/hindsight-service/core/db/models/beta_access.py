import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, now_utc


class BetaAccessRequest(Base):
    __tablename__ = 'beta_access_requests'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    email = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='pending')  # pending|accepted|denied
    requested_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewer_email = Column(Text, nullable=True)
    decision_reason = Column(Text, nullable=True)

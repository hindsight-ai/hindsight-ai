import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, now_utc


class PersonalAccessToken(Base):
    __tablename__ = 'personal_access_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)

    # Token identity and secret hash (never store raw secret)
    token_id = Column(String(64), nullable=False, unique=True)
    token_hash = Column(Text, nullable=False)

    # Display metadata
    name = Column(String(100), nullable=False)
    prefix = Column(String(12), nullable=True)
    last_four = Column(String(4), nullable=True)

    # Authorization metadata
    scopes = Column(JSONB, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=True)
    status = Column(String(20), nullable=False, default='active')  # active|revoked|expired

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_pat_token_id', 'token_id', unique=True),
        Index('idx_pat_user_created', 'user_id', 'created_at'),
        Index('idx_pat_status', 'status'),
    )


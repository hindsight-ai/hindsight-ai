import uuid
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, now_utc


class BulkOperation(Base):
    __tablename__ = 'bulk_operations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    type = Column(Text, nullable=False)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    request_payload = Column(JSONB, nullable=True)
    status = Column(Text, nullable=False, default='pending')  # pending|running|completed|failed|cancelled
    progress = Column(Integer, nullable=False, default=0)
    total = Column(Integer, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error_log = Column(JSONB, nullable=True)
    result_summary = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    __table_args__ = (
        Index('ix_bulk_operations_organization_id_created_at', 'organization_id', 'created_at'),
        Index('ix_bulk_operations_actor_user_id_created_at', 'actor_user_id', 'created_at'),
    )


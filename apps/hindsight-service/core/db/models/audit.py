import uuid
from sqlalchemy import Column, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from .base import Base, now_utc


class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='SET NULL'), nullable=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    action_type = Column(Text, nullable=False)
    target_type = Column(Text, nullable=True)
    target_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(Text, nullable=False)
    reason = Column(Text, nullable=True)
    # Use a non-reserved Python attribute name while keeping DB column name 'metadata'
    metadata_json = Column('metadata', JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)

    __table_args__ = (
        Index('ix_audit_logs_organization_id_created_at', 'organization_id', 'created_at'),
        Index('ix_audit_logs_actor_user_id_created_at', 'actor_user_id', 'created_at'),
        Index('ix_audit_logs_action_type', 'action_type'),
    )

    def get_metadata(self):
        return self.metadata_json

    def set_metadata(self, value):
        self.metadata_json = value


import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from .base import Base, now_utc


class Organization(Base):
    __tablename__ = 'organizations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, unique=True)
    slug = Column(String, nullable=True, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class OrganizationMembership(Base):
    __tablename__ = 'organization_memberships'
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), primary_key=True)
    role = Column(String, nullable=False)  # 'owner'|'admin'|'editor'|'viewer'
    can_read = Column(Boolean, nullable=False, default=True)
    can_write = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    __table_args__ = (
        Index('idx_org_memberships_user_id', 'user_id'),
        CheckConstraint("role in ('owner','admin','editor','viewer')", name='ck_org_memberships_role'),
    )


class OrganizationInvitation(Base):
    __tablename__ = 'organization_invitations'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    email = Column(Text, nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    role = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default='pending')  # pending|accepted|revoked|expired
    token = Column(Text, nullable=True, unique=True)
    created_at = Column(DateTime(timezone=True), default=now_utc, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_organization_invitations_email', 'email'),
        Index('ix_organization_invitations_organization_id', 'organization_id'),
        # Pending unique enforced at DB via partial index created in migration
    )


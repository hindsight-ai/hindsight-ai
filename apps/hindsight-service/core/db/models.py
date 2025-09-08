import uuid
from sqlalchemy import (
    create_engine,
    Column,
    String,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    Boolean,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, UTC


def now_utc():
    """Return an aware UTC datetime for default/updated timestamps."""
    return datetime.now(UTC)

Base = declarative_base()

"""
Data governance additions:
- Users, Organizations, OrganizationMembership models
- Scoped ownership on Agents, MemoryBlock, and Keyword via:
  visibility_scope ('personal'|'organization'|'public'), owner_user_id, organization_id
- Note: Uniqueness per scope is enforced at the DB layer via Alembic partial
  unique indexes, not via ORM-level unique constraints.
"""

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False, unique=True, index=True)
    display_name = Column(String, nullable=True)
    is_superadmin = Column(Boolean, nullable=False, default=False)
    auth_provider = Column(String, nullable=True)
    external_subject = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


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

class Agent(Base):
    __tablename__ = 'agents'
    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(255), nullable=False)
    # Governance scoping
    visibility_scope = Column(String(20), nullable=False, default='personal')
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    transcripts = relationship("AgentTranscript", back_populates="agent")
    memory_blocks = relationship("MemoryBlock", back_populates="agent")

class AgentTranscript(Base):
    __tablename__ = 'agent_transcripts'
    transcript_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.agent_id'), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    transcript_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    agent = relationship("Agent", back_populates="transcripts")

    __table_args__ = (
        Index('idx_agent_transcripts_agent_id', 'agent_id'),
        Index('idx_agent_transcripts_conversation_id', 'conversation_id'),
    )

class MemoryBlock(Base):
    __tablename__ = 'memory_blocks'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) # Renamed from memory_id to id
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.agent_id'), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=now_utc)
    content = Column(Text, nullable=False)
    errors = Column(Text)
    lessons_learned = Column(Text)
    metadata_col = Column('metadata', JSONB)
    feedback_score = Column(Integer, default=0)
    retrieval_count = Column(Integer, default=0) # Added retrieval_count
    archived = Column(Boolean, default=False) # Added archived column
    archived_at = Column(DateTime(timezone=True), nullable=True) # Added archived timestamp
    # Governance scoping
    visibility_scope = Column(String(20), nullable=False, default='personal')
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
    
    # Search-related fields
    search_vector = Column(TSVECTOR, nullable=True)  # For full-text search
    content_embedding = Column(Text, nullable=True)  # For future semantic search

    agent = relationship("Agent", back_populates="memory_blocks")
    feedback_logs = relationship("FeedbackLog", back_populates="memory_block", cascade="all, delete-orphan")
    memory_block_keywords = relationship("MemoryBlockKeyword", back_populates="memory_block", cascade="all, delete-orphan")

    @property
    def keywords(self):
        return [mbk.keyword for mbk in self.memory_block_keywords]

    __table_args__ = (
        Index('idx_memory_blocks_agent_id', 'agent_id'),
        Index('idx_memory_blocks_conversation_id', 'conversation_id'),
        Index('idx_memory_blocks_timestamp', 'timestamp'),
        Index('idx_memory_blocks_archived_at', 'archived_at'),
        Index('idx_memory_blocks_owner_user_id', 'owner_user_id'),
        Index('idx_memory_blocks_org_scope', 'organization_id', 'visibility_scope'),
        CheckConstraint("visibility_scope in ('personal','organization','public')", name='ck_memory_blocks_visibility_scope'),
    )

class FeedbackLog(Base):
    __tablename__ = 'feedback_logs'
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey('memory_blocks.id'), nullable=False) # Updated ForeignKey
    feedback_type = Column(String(50), nullable=False)
    feedback_details = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    memory_block = relationship("MemoryBlock", back_populates="feedback_logs")

class Keyword(Base):
    __tablename__ = 'keywords'
    keyword_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_text = Column(String(255), nullable=False)
    # Governance scoping
    visibility_scope = Column(String(20), nullable=False, default='personal')
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    memory_block_keywords = relationship("MemoryBlockKeyword", back_populates="keyword")

    __table_args__ = (
        Index('idx_keywords_keyword_text', 'keyword_text'),
        Index('idx_keywords_owner_user_id', 'owner_user_id'),
        Index('idx_keywords_org_scope', 'organization_id', 'visibility_scope'),
        CheckConstraint("visibility_scope in ('personal','organization','public')", name='ck_keywords_visibility_scope'),
    )

class MemoryBlockKeyword(Base):
    __tablename__ = 'memory_block_keywords'
    memory_id = Column(UUID(as_uuid=True), ForeignKey('memory_blocks.id'), primary_key=True) # Updated ForeignKey
    keyword_id = Column(UUID(as_uuid=True), ForeignKey('keywords.keyword_id'), primary_key=True)

    memory_block = relationship("MemoryBlock", back_populates="memory_block_keywords")
    keyword = relationship("Keyword", back_populates="memory_block_keywords")


class ConsolidationSuggestion(Base):
    __tablename__ = 'consolidation_suggestions'
    suggestion_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    suggested_content = Column(Text, nullable=False)
    suggested_lessons_learned = Column(Text, nullable=False)
    suggested_keywords = Column(JSONB, nullable=False)
    original_memory_ids = Column(JSONB, nullable=False)
    status = Column(String(20), nullable=False, default='pending')
    timestamp = Column(DateTime(timezone=True), default=now_utc)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    __table_args__ = (
        Index('idx_consolidation_suggestions_status', 'status'),
        Index('idx_consolidation_suggestions_group_id', 'group_id'),
    )


# Governance Phase 2.1 additions (invitations, audit logs, bulk operations)
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

    # Avoid defining a .metadata property (reserved by SQLAlchemy for MetaData); use explicit accessors if needed
    def get_metadata(self):
        return self.metadata_json

    def set_metadata(self, value):
        self.metadata_json = value


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

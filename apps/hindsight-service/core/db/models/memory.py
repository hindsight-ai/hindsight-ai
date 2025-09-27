import uuid
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Index, Boolean, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.orm import relationship
from .base import Base, now_utc
from core.db.types import EmbeddingVector


class MemoryBlock(Base):
    __tablename__ = 'memory_blocks'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.agent_id'), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime(timezone=True), default=now_utc)
    content = Column(Text, nullable=False)
    errors = Column(Text)
    lessons_learned = Column(Text)
    metadata_col = Column('metadata', JSONB)
    feedback_score = Column(Integer, default=0)
    retrieval_count = Column(Integer, default=0)
    archived = Column(Boolean, default=False)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    # Governance scoping
    visibility_scope = Column(String(20), nullable=False, default='personal')
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=now_utc)
    updated_at = Column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    # Search-related fields
    search_vector = Column(TSVECTOR, nullable=True)  # For full-text search
    content_embedding = Column(EmbeddingVector(), nullable=True)  # For semantic search embeddings

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
    memory_id = Column(UUID(as_uuid=True), ForeignKey('memory_blocks.id'), nullable=False)
    feedback_type = Column(String(50), nullable=False)
    feedback_details = Column(Text)
    created_at = Column(DateTime(timezone=True), default=now_utc)

    memory_block = relationship("MemoryBlock", back_populates="feedback_logs")


class MemoryBlockKeyword(Base):
    __tablename__ = 'memory_block_keywords'
    memory_id = Column(UUID(as_uuid=True), ForeignKey('memory_blocks.id'), primary_key=True)
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

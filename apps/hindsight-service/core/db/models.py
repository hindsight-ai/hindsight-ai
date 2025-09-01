import uuid
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB, TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class Agent(Base):
    __tablename__ = 'agents'
    agent_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    transcripts = relationship("AgentTranscript", back_populates="agent")
    memory_blocks = relationship("MemoryBlock", back_populates="agent")

class AgentTranscript(Base):
    __tablename__ = 'agent_transcripts'
    transcript_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.agent_id'), nullable=False)
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    transcript_content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

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
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    content = Column(Text, nullable=False)
    errors = Column(Text)
    lessons_learned = Column(Text)
    metadata_col = Column('metadata', JSONB)
    feedback_score = Column(Integer, default=0)
    retrieval_count = Column(Integer, default=0) # Added retrieval_count
    archived = Column(Boolean, default=False) # Added archived column
    archived_at = Column(DateTime(timezone=True), nullable=True) # Added archived timestamp
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
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
    )

class FeedbackLog(Base):
    __tablename__ = 'feedback_logs'
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id = Column(UUID(as_uuid=True), ForeignKey('memory_blocks.id'), nullable=False) # Updated ForeignKey
    feedback_type = Column(String(50), nullable=False)
    feedback_details = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    memory_block = relationship("MemoryBlock", back_populates="feedback_logs")

class Keyword(Base):
    __tablename__ = 'keywords'
    keyword_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    keyword_text = Column(String(255), nullable=False, unique=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    memory_block_keywords = relationship("MemoryBlockKeyword", back_populates="keyword")

    __table_args__ = (
        Index('idx_keywords_keyword_text', 'keyword_text'),
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
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_consolidation_suggestions_status', 'status'),
        Index('idx_consolidation_suggestions_group_id', 'group_id'),
    )

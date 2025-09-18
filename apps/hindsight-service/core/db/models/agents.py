import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, now_utc


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


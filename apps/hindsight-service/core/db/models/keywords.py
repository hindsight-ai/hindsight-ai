import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import Base, now_utc


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


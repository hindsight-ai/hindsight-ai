import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict

# Base Schemas
class AgentBase(BaseModel):
    agent_name: str
    # Governance scoping (optional on input for now)
    visibility_scope: Optional[str] = 'personal'
    owner_user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None

class AgentTranscriptBase(BaseModel):
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    transcript_content: str

class MemoryBlockBase(BaseModel):
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    errors: Optional[str] = None
    lessons_learned: Optional[str] = None
    metadata_col: Optional[Dict[str, Any]] = None
    feedback_score: Optional[int] = 0
    retrieval_count: Optional[int] = 0  # Added missing field
    archived: Optional[bool] = False
    archived_at: Optional[datetime] = None
    # Governance scoping (optional on input for now)
    visibility_scope: Optional[str] = 'personal'
    owner_user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None

class FeedbackLogBase(BaseModel):
    feedback_type: str
    feedback_details: Optional[str] = None

class KeywordBase(BaseModel):
    keyword_text: str
    # Governance scoping (optional on input for now)
    visibility_scope: Optional[str] = 'personal'
    owner_user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None

# Create Schemas (for POST requests)
class AgentCreate(AgentBase):
    pass

class AgentTranscriptCreate(AgentTranscriptBase):
    pass

class MemoryBlockCreate(MemoryBlockBase):
    pass

class FeedbackLogCreate(FeedbackLogBase):
    memory_id: uuid.UUID

class KeywordCreate(KeywordBase):
    pass

# Update Schemas (for PUT/PATCH requests)
class AgentUpdate(BaseModel):
    agent_name: Optional[str] = None

class AgentTranscriptUpdate(BaseModel):
    transcript_content: Optional[str] = None

class MemoryBlockUpdate(BaseModel):
    content: Optional[str] = None
    errors: Optional[str] = None
    lessons_learned: Optional[str] = None
    metadata_col: Optional[Dict[str, Any]] = None
    feedback_score: Optional[int] = None

class FeedbackLogUpdate(BaseModel):
    feedback_type: Optional[str] = None
    feedback_details: Optional[str] = None

class KeywordUpdate(BaseModel):
    keyword_text: Optional[str] = None
    visibility_scope: Optional[str] = None

# Read Schemas (for GET responses)
class Agent(AgentBase):
    agent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class AgentTranscript(AgentTranscriptBase):
    transcript_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class MemoryBlock(MemoryBlockBase):
    id: uuid.UUID
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    keywords: List['Keyword'] = [] # Add this line
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class MemoryBlockKeywordAssociation(BaseModel):
    memory_id: uuid.UUID # Changed from memory_block_id to memory_id
    keyword_id: uuid.UUID

class FeedbackLog(FeedbackLogBase):
    feedback_id: uuid.UUID
    memory_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Keyword(KeywordBase):
    keyword_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Consolidation Suggestion Schemas
class ConsolidationSuggestionBase(BaseModel):
    group_id: uuid.UUID
    suggested_content: str
    suggested_lessons_learned: str
    suggested_keywords: List[str]
    original_memory_ids: List[str] # Changed from List[uuid.UUID] to List[str]
    status: str = "pending"

class ConsolidationSuggestionCreate(ConsolidationSuggestionBase):
    pass

class ConsolidationSuggestionUpdate(BaseModel):
    status: Optional[str] = None
    suggested_content: Optional[str] = None
    suggested_lessons_learned: Optional[str] = None
    suggested_keywords: Optional[List[str]] = None

class ConsolidationSuggestion(ConsolidationSuggestionBase):
    suggestion_id: uuid.UUID
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class PaginatedConsolidationSuggestions(BaseModel):
    items: List[ConsolidationSuggestion]
    total_items: int
    total_pages: int

class PaginatedMemoryBlocks(BaseModel):
    items: List[MemoryBlock]
    total_items: int
    total_pages: int

# Search-related schemas
class MemoryBlockWithScore(MemoryBlock):
    search_score: float
    search_type: str = "basic"
    rank_explanation: Optional[str] = None

# Governance Schemas
class UserBase(BaseModel):
    email: str
    display_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: uuid.UUID
    is_superadmin: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OrganizationBase(BaseModel):
    name: str
    slug: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(OrganizationBase):
    pass

class Organization(OrganizationBase):
    id: uuid.UUID
    is_active: bool
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OrganizationMemberBase(BaseModel):
    user_id: uuid.UUID
    role: str
    can_read: Optional[bool] = True
    can_write: Optional[bool] = False

class OrganizationMemberCreate(OrganizationMemberBase):
    pass

class OrganizationMemberUpdate(BaseModel):
    role: Optional[str] = None
    can_read: Optional[bool] = None
    can_write: Optional[bool] = None

class OrganizationMember(OrganizationMemberBase):
    organization_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OrganizationInvitationBase(BaseModel):
    email: str
    role: str

class OrganizationInvitationCreate(OrganizationInvitationBase):
    pass

class OrganizationInvitationUpdate(BaseModel):
    status: Optional[str] = None
    role: Optional[str] = None

class OrganizationInvitation(OrganizationInvitationBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    invited_by_user_id: uuid.UUID
    status: str
    token: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AuditLogBase(BaseModel):
    action_type: str
    status: str
    target_type: Optional[str] = None
    target_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None  # Pydantic field; internal SQLAlchemy column is metadata_json

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    actor_user_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BulkOperationBase(BaseModel):
    type: str
    request_payload: Optional[Dict[str, Any]] = None

class BulkOperationCreate(BulkOperationBase):
    pass

class BulkOperation(BulkOperationBase):
    id: uuid.UUID
    actor_user_id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    status: str
    progress: int
    total: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_log: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class BulkOperationUpdate(BaseModel):
    status: Optional[str] = None
    progress: Optional[int] = None
    total: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error_log: Optional[Dict[str, Any]] = None
    result_summary: Optional[Dict[str, Any]] = None


class SearchMetadata(BaseModel):
    total_search_time_ms: Optional[float] = None
    fulltext_results_count: Optional[int] = None
    semantic_results_count: Optional[int] = None
    hybrid_weights: Optional[Dict[str, float]] = None
    query_terms: Optional[List[str]] = None

class PaginatedMemoryBlocksWithSearch(BaseModel):
    items: List[MemoryBlockWithScore]
    total_items: int
    total_pages: int
    search_metadata: Optional[SearchMetadata] = None

# Enhanced search request schemas
class FulltextSearchRequest(BaseModel):
    query: str
    agent_id: Optional[uuid.UUID] = None
    limit: int = 50
    min_score: float = 0.1

class SemanticSearchRequest(BaseModel):
    query: str
    agent_id: Optional[uuid.UUID] = None
    limit: int = 50
    similarity_threshold: float = 0.7

class HybridSearchRequest(BaseModel):
    query: str
    agent_id: Optional[uuid.UUID] = None
    limit: int = 50
    fulltext_weight: float = 0.7
    semantic_weight: float = 0.3
    min_combined_score: float = 0.1

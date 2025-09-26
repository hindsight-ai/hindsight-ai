import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from core.utils.scopes import VisibilityScopeEnum


class MemoryBlockBase(BaseModel):
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    content: str
    errors: Optional[str] = None
    lessons_learned: Optional[str] = None
    metadata_col: Optional[Dict[str, Any]] = None
    feedback_score: Optional[int] = 0
    retrieval_count: Optional[int] = 0
    archived: Optional[bool] = False
    archived_at: Optional[datetime] = None
    visibility_scope: Optional[VisibilityScopeEnum] = VisibilityScopeEnum.personal
    owner_user_id: Optional[uuid.UUID] = None
    organization_id: Optional[uuid.UUID] = None
    content_embedding: Optional[List[float]] = None


class MemoryBlockCreate(MemoryBlockBase):
    pass


class MemoryBlockUpdate(BaseModel):
    content: Optional[str] = None
    errors: Optional[str] = None
    lessons_learned: Optional[str] = None
    metadata_col: Optional[Dict[str, Any]] = None
    feedback_score: Optional[int] = None


class MemoryBlock(MemoryBlockBase):
    id: uuid.UUID
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    keywords: List['Keyword'] = []
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class MemoryBlockKeywordAssociation(BaseModel):
    memory_id: uuid.UUID
    keyword_id: uuid.UUID


class FeedbackLogBase(BaseModel):
    feedback_type: str
    feedback_details: Optional[str] = None


class FeedbackLogCreate(FeedbackLogBase):
    memory_id: uuid.UUID


class FeedbackLogUpdate(BaseModel):
    feedback_type: Optional[str] = None
    feedback_details: Optional[str] = None


class FeedbackLog(FeedbackLogBase):
    feedback_id: uuid.UUID
    memory_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConsolidationSuggestionBase(BaseModel):
    group_id: uuid.UUID
    suggested_content: str
    suggested_lessons_learned: str
    suggested_keywords: List[str]
    original_memory_ids: List[str]
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


class MemoryBlockWithScore(MemoryBlock):
    search_score: float
    search_type: str = "basic"
    rank_explanation: Optional[str] = None


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

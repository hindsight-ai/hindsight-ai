import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

# Base Schemas
class AgentBase(BaseModel):
    agent_name: str

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

class FeedbackLogBase(BaseModel):
    id: uuid.UUID # Changed from memory_id to id
    feedback_type: str
    feedback_details: Optional[str] = None

class KeywordBase(BaseModel):
    keyword_text: str

# Create Schemas (for POST requests)
class AgentCreate(AgentBase):
    pass

class AgentTranscriptCreate(AgentTranscriptBase):
    pass

class MemoryBlockCreate(MemoryBlockBase):
    pass

class FeedbackLogCreate(FeedbackLogBase):
    pass

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

# Read Schemas (for GET responses)
class Agent(AgentBase):
    agent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class AgentTranscript(AgentTranscriptBase):
    transcript_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class MemoryBlock(MemoryBlockBase):
    id: uuid.UUID
    timestamp: datetime
    created_at: datetime
    updated_at: datetime
    keywords: List['Keyword'] = [] # Add this line

    class Config:
        from_attributes = True # Pydantic V2 equivalent of orm_mode
        populate_by_name = True # Allow population by field name or alias

class MemoryBlockKeywordAssociation(BaseModel):
    memory_id: uuid.UUID # Changed from memory_block_id to memory_id
    keyword_id: uuid.UUID

class FeedbackLog(FeedbackLogBase):
    feedback_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class Keyword(KeywordBase):
    keyword_id: uuid.UUID
    created_at: datetime

    class Config:
        orm_mode = True

class PaginatedMemoryBlocks(BaseModel):
    items: List[MemoryBlock]
    total_items: int
    total_pages: int

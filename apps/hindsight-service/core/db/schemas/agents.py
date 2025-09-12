import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class AgentBase(BaseModel):
    agent_name: str
    visibility_scope: str | None = 'personal'
    owner_user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    agent_name: str | None = None


class Agent(AgentBase):
    agent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AgentTranscriptBase(BaseModel):
    agent_id: uuid.UUID
    conversation_id: uuid.UUID
    transcript_content: str


class AgentTranscriptCreate(AgentTranscriptBase):
    pass


class AgentTranscriptUpdate(BaseModel):
    transcript_content: str | None = None


class AgentTranscript(AgentTranscriptBase):
    transcript_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


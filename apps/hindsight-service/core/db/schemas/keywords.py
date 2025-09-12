import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class KeywordBase(BaseModel):
    keyword_text: str
    visibility_scope: str | None = 'personal'
    owner_user_id: uuid.UUID | None = None
    organization_id: uuid.UUID | None = None


class KeywordCreate(KeywordBase):
    pass


class KeywordUpdate(BaseModel):
    keyword_text: str | None = None
    visibility_scope: str | None = None


class Keyword(KeywordBase):
    keyword_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


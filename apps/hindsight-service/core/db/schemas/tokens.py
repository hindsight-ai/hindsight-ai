import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import List, Optional


class TokenCreateRequest(BaseModel):
    name: str
    scopes: List[str]
    organization_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None

    @field_validator("scopes")
    @classmethod
    def _validate_scopes(cls, v: List[str]):
        cleaned = [s.strip().lower() for s in (v or [])]
        if not cleaned:
            raise ValueError("At least one scope is required")
        # MVP: only read/write/manage accepted, but we will not enforce manage in v1
        allowed = {"read", "write", "manage"}
        for s in cleaned:
            if s not in allowed:
                raise ValueError(f"Invalid scope: {s}")
        return cleaned


class TokenUpdateRequest(BaseModel):
    name: Optional[str] = None
    expires_at: Optional[datetime] = None


class TokenResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    scopes: List[str]
    organization_id: Optional[uuid.UUID] = None
    status: str
    created_at: datetime
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    prefix: Optional[str] = None
    last_four: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TokenCreateResponse(TokenResponse):
    token: str  # one-time secret string


import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AuditLogBase(BaseModel):
    action_type: str
    status: str
    target_type: Optional[str] = None
    target_id: Optional[uuid.UUID] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLog(AuditLogBase):
    id: uuid.UUID
    organization_id: Optional[uuid.UUID] = None
    actor_user_id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


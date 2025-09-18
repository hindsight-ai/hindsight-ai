import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


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


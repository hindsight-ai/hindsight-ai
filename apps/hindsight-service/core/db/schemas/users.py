import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class UserBase(BaseModel):
    email: str
    display_name: str | None = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: uuid.UUID
    is_superadmin: bool
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    name: str
    slug: str | None = None


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(OrganizationBase):
    pass


class Organization(OrganizationBase):
    id: uuid.UUID
    is_active: bool
    created_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberBase(BaseModel):
    user_id: uuid.UUID
    role: str
    can_read: bool | None = True
    can_write: bool | None = False


class OrganizationMemberCreate(OrganizationMemberBase):
    pass


class OrganizationMemberUpdate(BaseModel):
    role: str | None = None
    can_read: bool | None = None
    can_write: bool | None = None


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
    status: str | None = None
    role: str | None = None


class OrganizationInvitation(OrganizationInvitationBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    invited_by_user_id: uuid.UUID
    status: str
    token: str | None = None
    created_at: datetime
    expires_at: datetime
    accepted_at: datetime | None = None
    revoked_at: datetime | None = None
    model_config = ConfigDict(from_attributes=True)


"""
Organization repository functions.

Implements CRUD for organizations, memberships, and invitations.
"""
from __future__ import annotations

import uuid
from typing import Optional
from datetime import timezone, datetime, timedelta
from sqlalchemy.orm import Session

from core.db import schemas, models


def create_organization(db: Session, organization: schemas.OrganizationCreate, user_id: uuid.UUID):
    db_organization = models.Organization(
        name=organization.name,
        slug=organization.slug,
        created_by=user_id,
    )
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)
    # Add creator as owner
    db_member = models.OrganizationMembership(
        organization_id=db_organization.id,
        user_id=user_id,
        role='owner',
    )
    db.add(db_member)
    db.commit()
    return db_organization


def get_organization(db: Session, organization_id: uuid.UUID):
    return db.query(models.Organization).filter(models.Organization.id == organization_id).first()


def get_organizations(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Organization)
        .join(models.OrganizationMembership)
        .filter(models.OrganizationMembership.user_id == user_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_organization(db: Session, organization_id: uuid.UUID, organization: schemas.OrganizationUpdate):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        update_data = organization.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_organization, key, value)
        db.commit()
        db.refresh(db_organization)
    return db_organization


def delete_organization(db: Session, organization_id: uuid.UUID):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        db.delete(db_organization)
        db.commit()
        return True
    return False


def create_organization_member(db: Session, organization_id: uuid.UUID, member: schemas.OrganizationMemberCreate):
    db_member = models.OrganizationMembership(
        organization_id=organization_id,
        **member.model_dump(),
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


def get_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    return (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.user_id == user_id,
        )
        .first()
    )


def get_organization_members(db: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return (
        db.query(models.OrganizationMembership)
        .filter(models.OrganizationMembership.organization_id == organization_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID, member: schemas.OrganizationMemberUpdate):
    db_member = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.user_id == user_id,
        )
        .first()
    )
    if db_member:
        update_data = member.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_member, key, value)
        db.commit()
        db.refresh(db_member)
    return db_member


def delete_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    db_member = (
        db.query(models.OrganizationMembership)
        .filter(
            models.OrganizationMembership.organization_id == organization_id,
            models.OrganizationMembership.user_id == user_id,
        )
        .first()
    )
    if db_member:
        db.delete(db_member)
        db.commit()
        return True
    return False


def create_organization_invitation(
    db: Session,
    organization_id: uuid.UUID,
    invitation: schemas.OrganizationInvitationCreate,
    invited_by_user_id: uuid.UUID,
):
    import uuid as _uuid
    db_invitation = models.OrganizationInvitation(
        organization_id=organization_id,
        email=invitation.email,
        role=invitation.role,
        invited_by_user_id=invited_by_user_id,
        token=_uuid.uuid4().hex,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    if db_invitation.expires_at and db_invitation.expires_at.tzinfo is None:
        db_invitation.expires_at = db_invitation.expires_at.replace(tzinfo=timezone.utc)
    if db_invitation.created_at and db_invitation.created_at.tzinfo is None:
        db_invitation.created_at = db_invitation.created_at.replace(tzinfo=timezone.utc)
    return db_invitation


def get_organization_invitation(db: Session, invitation_id: uuid.UUID):
    return db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()


def get_organization_invitations(
    db: Session,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    *,
    status: str | None = None,
):
    q = db.query(models.OrganizationInvitation).filter(
        models.OrganizationInvitation.organization_id == organization_id
    )
    if status:
        q = q.filter(models.OrganizationInvitation.status == status)
    return q.offset(skip).limit(limit).all()


def update_organization_invitation(db: Session, invitation_id: uuid.UUID, invitation: schemas.OrganizationInvitationUpdate):
    db_invitation = db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()
    if db_invitation:
        update_data = invitation.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_invitation, key, value)
        db.commit()
        db.refresh(db_invitation)
    return db_invitation


def delete_organization_invitation(db: Session, invitation_id: uuid.UUID) -> bool:
    db_invitation = db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()
    if db_invitation:
        db.delete(db_invitation)
        db.commit()
        return True
    return False

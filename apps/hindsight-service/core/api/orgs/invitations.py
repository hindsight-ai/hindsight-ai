"""
Organization invitation endpoints.

Handles creating, listing, resending, declining, revoking, and accepting
organization invitations, including both token-based and OAuth-based flows.
"""
from typing import Optional, List
import uuid
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models, schemas, crud
from core.api.deps import get_current_user_context
from core.api.auth import get_or_create_user
from core.api.permissions import can_manage_org
from core.utils.role_permissions import get_allowed_roles, get_role_permissions
from core.audit import log, AuditAction, AuditStatus


router = APIRouter()

logger = logging.getLogger(__name__)


@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED, response_model=schemas.OrganizationInvitation)
def create_invitation(
    org_id: uuid.UUID,
    invitation: schemas.OrganizationInvitationCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Prevent duplicate pending invitation for the same email/org
    # Strong duplicate guard at DB level
    dup = db.query(models.OrganizationInvitation).filter(
        models.OrganizationInvitation.organization_id == org_id,
        models.OrganizationInvitation.email == (invitation.email or '').lower(),
        models.OrganizationInvitation.status == 'pending',
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Pending invitation already exists for this email")
    # Prevent invite for users who are already members
    # Find user by email and check membership
    existing_user = db.query(models.User).filter(models.User.email == (invitation.email or '').lower()).first()
    if existing_user:
        membership = db.query(models.OrganizationMembership).filter(
            models.OrganizationMembership.organization_id == org_id,
            models.OrganizationMembership.user_id == existing_user.id,
        ).first()
        if membership:
            raise HTTPException(status_code=409, detail="User is already a member of this organization")
    db_invitation = crud.create_organization_invitation(db, organization_id=org_id, invitation=invitation, invited_by_user_id=user.id)

    log(
        db,
        action=AuditAction.INVITATION_CREATE,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=db_invitation.id,
        actor_user_id=user.id,
        organization_id=org_id,
        metadata={"email": invitation.email, "role": invitation.role},
    )

    # Send notification to invitee (email always; in-app if user exists)
    try:
        from core.services.notification_service import NotificationService

        # Get organization details
        organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()

        # Check if invitee has an account
        invitee_user = db.query(models.User).filter(models.User.email == invitation.email).first()

        if organization:
            from core.utils.urls import build_login_invite_link
            accept_url = build_login_invite_link(
                invitation_id=str(db_invitation.id), org_id=str(org_id), email=invitation.email, action="accept", token=db_invitation.token
            )
            decline_url = build_login_invite_link(
                invitation_id=str(db_invitation.id), org_id=str(org_id), email=invitation.email, action="decline", token=db_invitation.token
            )

            notification_service = NotificationService(db)
            notification_service.notify_organization_invitation(
                invitee_user_id=invitee_user.id if invitee_user else None,
                invitee_email=invitation.email,
                inviter_name=user.display_name or user.email,
                inviter_user_id=user.id,
                organization_name=organization.name,
                invitation_id=db_invitation.id,
                accept_url=accept_url,
                decline_url=decline_url,
                role=invitation.role
            )
    except Exception as e:
        # Log error but don't fail the invitation creation
        logger.error(f"Failed to send notification for invitation {db_invitation.id}: {str(e)}")

    return db_invitation

@router.post("/{org_id}/invitations/{invitation_id}/decline")
def decline_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
    token: str | None = None,
):
    user = user_context.user
    current_user = user_context.current

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Allow decline either by email match or valid token
    if not (token and db_invitation.token and token == db_invitation.token):
        if (db_invitation.email or '').lower() != (user.email or '').lower():
            raise HTTPException(status_code=403, detail="Invitation is for a different user")

    if (db_invitation.status or '').lower() != 'pending':
        raise HTTPException(status_code=400, detail=f"Invitation is already {db_invitation.status}")

    db_invitation.status = 'revoked'
    try:
        db_invitation.revoked_at = datetime.now(timezone.utc)
    except Exception:
        pass
    db.commit()

    # Notify inviter
    try:
        from core.services.notification_service import NotificationService
        inviter = db.query(models.User).filter(models.User.id == db_invitation.invited_by_user_id).first()
        org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        if inviter and org:
            NotificationService(db).notify_invitation_declined(
                inviter_user_id=inviter.id,
                inviter_email=inviter.email,
                organization_name=org.name,
                invitee_email=(db_invitation.email or ''),
            )
    except Exception:
        pass

    log(
        db,
        action=AuditAction.INVITATION_DECLINE,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=invitation_id,
        actor_user_id=user.id,
        organization_id=org_id,
    )
    return {"status": "revoked"}

@router.get("/{org_id}/invitations", response_model=List[schemas.OrganizationInvitation])
def list_invitations(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
    status: Optional[str] = 'pending',
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    effective_status = None if (status is None or str(status).lower() == 'all') else status
    invitations = crud.get_organization_invitations(db, organization_id=org_id, status=effective_status)
    return invitations

@router.post("/{org_id}/invitations/{invitation_id}/resend", response_model=schemas.OrganizationInvitation)
def resend_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    db_invitation.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    # rotate token on resend to invalidate old links
    try:
        import uuid as _uuid
        db_invitation.token = _uuid.uuid4().hex
    except Exception:
        pass
    db.commit()
    db.refresh(db_invitation)

    # Send the invitation email
    try:
        organization = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        invitee_user = db.query(models.User).filter(models.User.email == db_invitation.email).first()

        if organization:
            from core.utils.urls import build_login_invite_link
            accept_url = build_login_invite_link(
                invitation_id=str(db_invitation.id), org_id=str(org_id), email=db_invitation.email, action="accept", token=db_invitation.token
            )
            decline_url = build_login_invite_link(
                invitation_id=str(db_invitation.id), org_id=str(org_id), email=db_invitation.email, action="decline", token=db_invitation.token
            )

            from core.services.notification_service import NotificationService
            notification_service = NotificationService(db)
            notification_service.notify_organization_invitation(
                invitee_user_id=invitee_user.id if invitee_user else None,
                invitee_email=db_invitation.email,
                inviter_name=user.display_name or user.email,
                inviter_user_id=user.id,
                organization_name=organization.name,
                invitation_id=db_invitation.id,
                accept_url=accept_url,
                decline_url=decline_url,
                role=db_invitation.role
            )
    except Exception as e:
        # Log error but don't fail the resend operation
        logger.error(f"Failed to send notification for invitation resend {db_invitation.id}: {str(e)}")

    log(
        db,
        action=AuditAction.INVITATION_RESEND,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=db_invitation.id,
        actor_user_id=user.id,
        organization_id=org_id,
        metadata={"new_expires_at": db_invitation.expires_at.isoformat() if db_invitation.expires_at else None},
    )
    return db_invitation

@router.delete("/{org_id}/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    db_invitation.status = 'revoked'
    db_invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()

    log(
        db,
        action=AuditAction.INVITATION_REVOKE,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=invitation_id,
        actor_user_id=user.id,
        organization_id=org_id,
    )

@router.post("/{org_id}/invitations/{invitation_id}/accept", response_model=schemas.OrganizationMember)
def accept_invitation(
    org_id: uuid.UUID,
    invitation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
    token: str | None = None,
):
    user = user_context.user
    current_user = user_context.current

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Validate status and expiry first
    if (db_invitation.status or '').lower() != 'pending':
        raise HTTPException(status_code=400, detail=f"Invitation is already {db_invitation.status}")
    now_utc = datetime.now(timezone.utc)
    expires_at = db_invitation.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        try:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    if expires_at and expires_at < now_utc:
        db_invitation.status = 'expired'
        db.commit()
        raise HTTPException(status_code=400, detail="Invitation has expired")

    # Determine acceptance mode
    accept_user_id = None
    if token and db_invitation.token and token == db_invitation.token:
        invited_user = get_or_create_user(db, email=db_invitation.email)
        accept_user_id = invited_user.id
    else:
        if (db_invitation.email or '').lower() != (user.email or '').lower():
            raise HTTPException(status_code=403, detail="Invitation is for a different user")
        accept_user_id = user.id

    # Add member
    # Validate role on the invitation and use role defaults for can_read/can_write
    allowed_roles = get_allowed_roles()
    if (db_invitation.role or "") not in allowed_roles:
        raise HTTPException(status_code=422, detail="Invalid role on invitation")

    role_perms = get_role_permissions(db_invitation.role)
    member_data = schemas.OrganizationMemberCreate(
        user_id=accept_user_id,
        role=db_invitation.role,
        can_read=role_perms.get("can_read", True),
        can_write=role_perms.get("can_write", False),
    )
    db_member = crud.create_organization_member(db, organization_id=org_id, member=member_data)

    # Update invitation
    db_invitation.status = 'accepted'
    db_invitation.accepted_at = now_utc
    db.commit()

    # Notify inviter
    try:
        from core.services.notification_service import NotificationService
        inviter = db.query(models.User).filter(models.User.id == db_invitation.invited_by_user_id).first()
        org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        if inviter and org:
            NotificationService(db).notify_invitation_accepted(
                inviter_user_id=inviter.id,
                inviter_email=inviter.email,
                organization_name=org.name,
                invitee_email=(db_invitation.email or ''),
            )
    except Exception:
        pass

    log(
        db,
        action=AuditAction.INVITATION_ACCEPT,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=invitation_id,
        actor_user_id=accept_user_id,
        organization_id=org_id,
    )

    return db_member

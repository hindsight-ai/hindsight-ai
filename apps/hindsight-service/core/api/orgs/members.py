"""
Organization membership endpoints.

Handles listing, adding, updating, and removing members from organizations.
"""
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models
from core.api.deps import get_current_user_context
from core.api.auth import get_or_create_user
from core.api.permissions import can_manage_org
from core.utils.role_permissions import get_allowed_roles, get_role_permissions
from core.audit import log, AuditAction, AuditStatus


router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/{org_id}/members")
def list_members(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user) and not current_user.is_superadmin and str(org_id) not in current_user.memberships_by_org:
        raise HTTPException(status_code=403, detail="Forbidden")

    members = (
        db.query(models.OrganizationMembership, models.User)
        .join(models.User, models.User.id == models.OrganizationMembership.user_id)
        .filter(models.OrganizationMembership.organization_id == org_id)
        .all()
    )
    return [
        {
            "user_id": str(u.id),
            "email": u.email,
            "display_name": u.display_name,
            "role": m.role,
            "can_read": bool(m.can_read),
            "can_write": bool(m.can_write),
        }
        for m, u in members
    ]


@router.post("/{org_id}/members", status_code=status.HTTP_201_CREATED)
def add_member(
    org_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    email = (payload.get("email") or "").strip().lower()
    role = (payload.get("role") or "viewer")
    # Pre-validate role against allowed set to avoid DB integrity errors
    allowed_roles = get_allowed_roles()
    if role not in allowed_roles:
        raise HTTPException(status_code=422, detail="Invalid role")

    # Derive default permissions from role configuration unless explicitly provided
    role_perms = get_role_permissions(role)
    can_read = bool(payload.get("can_read", role_perms.get("can_read", True)))
    can_write = bool(payload.get("can_write", role_perms.get("can_write", False)))
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")
    # Pre-validate role against allowed set to avoid DB integrity errors
    allowed_roles = get_allowed_roles()
    if role not in allowed_roles:
        raise HTTPException(status_code=422, detail="Invalid role")

    member_user = get_or_create_user(db, email=email)
    exists = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user.id,
    ).first()
    if exists:
        # For legacy /organizations endpoints, preserve behavior: conflict on duplicate add
        raise HTTPException(status_code=409, detail="User already a member")

    m = models.OrganizationMembership(
        organization_id=org_id,
        user_id=member_user.id,
        role=role,
        can_read=can_read,
        can_write=can_write,
    )
    db.add(m)
    db.commit()

    log(
        db,
        action=AuditAction.MEMBER_ADD,
        status=AuditStatus.SUCCESS,
        target_type="user",
        target_id=member_user.id,
        actor_user_id=user.id,
        organization_id=org_id,
        metadata={"role": role},
    )

    # Send notification to the new member using the central NotificationService
    try:
        from core.services.notification_service import NotificationService

        org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        notification_service = NotificationService(db)
        notification_service.notify_membership_added(
            user_id=member_user.id,
            user_email=member_user.email,
            organization_name=(org.name if org else ''),
            role=role,
            added_by_name=(user.display_name or user.email),
            organization_id=org.id if org else None,
            added_by_user_id=user.id
        )
    except Exception as e:
        logger.error(f"Failed to send membership notification for user {member_user.id}: {str(e)}")

    return {"status": "added"}


@router.put("/{org_id}/members/{member_user_id}")
def update_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    m = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user_id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")

    old_role = m.role
    if "role" in payload and payload["role"]:
        # Validate role
        allowed_roles = get_allowed_roles()
        if payload["role"] not in allowed_roles:
            raise HTTPException(status_code=422, detail="Invalid role")
        m.role = payload["role"]
    if "can_read" in payload:
        m.can_read = bool(payload["can_read"])
    if "can_write" in payload:
        m.can_write = bool(payload["can_write"])
    # If role changed and explicit can_write/can_read not provided, apply role defaults
    if old_role != (payload.get("role") or old_role):
        # role was changed by payload; apply defaults if not explicitly overridden
        if "can_read" not in payload or "can_write" not in payload:
            try:
                role_perms = get_role_permissions(m.role)
                if "can_read" not in payload:
                    m.can_read = bool(role_perms.get("can_read", True))
                if "can_write" not in payload:
                    m.can_write = bool(role_perms.get("can_write", False))
            except ValueError:
                # Shouldn't happen because we validated above, but guard anyway
                raise HTTPException(status_code=422, detail="Invalid role")

    db.commit()

    if old_role != m.role:
        log(
            db,
            action=AuditAction.MEMBER_ROLE_CHANGE,
            status=AuditStatus.SUCCESS,
            target_type="user",
            target_id=member_user_id,
            actor_user_id=user.id,
            organization_id=org_id,
            metadata={"old_role": old_role, "new_role": m.role},
        )
        # Notify the affected user about role change
        try:
            from core.services.notification_service import NotificationService
            member = db.query(models.User).filter(models.User.id == member_user_id).first()
            org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
            if member and org:
                NotificationService(db).notify_role_changed(
                    user_id=member_user_id,
                    user_email=member.email,
                    organization_name=org.name,
                    old_role=old_role,
                    new_role=m.role,
                    changed_by_name=(user.display_name or user.email)
                )
        except Exception:
            pass


@router.delete("/{org_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    deleted = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user_id,
    ).delete(synchronize_session=False)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.commit()

    log(
        db,
        action=AuditAction.MEMBER_REMOVE,
        status=AuditStatus.SUCCESS,
        target_type="user",
        target_id=member_user_id,
        actor_user_id=user.id,
        organization_id=org_id,
    )

    # Notify the removed user
    try:
        from core.services.notification_service import NotificationService
        member = db.query(models.User).filter(models.User.id == member_user_id).first()
        org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
        if member and org:
            NotificationService(db).notify_membership_removed(
                user_id=member_user_id,
                user_email=member.email,
                organization_name=org.name,
                removed_by_name=(user.display_name or user.email)
            )
    except Exception:
        pass

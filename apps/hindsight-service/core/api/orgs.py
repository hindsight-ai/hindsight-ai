"""
Organizations API endpoints.

Manage organizations and memberships with admin/owner role enforcement and
audited lifecycle actions.
"""
from typing import Optional, List
import uuid
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models, schemas
from core.api.deps import get_current_user_context
from core.api.auth import get_or_create_user
from core.api.permissions import can_manage_org
from core.utils.role_permissions import get_allowed_roles, get_manage_roles, get_role_permissions


router = APIRouter(prefix="/organizations", tags=["organizations"])


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    name = (payload.get("name") or "").strip()
    slug = (payload.get("slug") or None)
    if not name:
        raise HTTPException(status_code=422, detail="Organization name is required")

    user, current_user = user_context

    # Unique checks
    if db.query(models.Organization).filter(models.Organization.name == name).first():
        raise HTTPException(status_code=409, detail="Organization name already exists")
    if slug and db.query(models.Organization).filter(models.Organization.slug == slug).first():
        raise HTTPException(status_code=409, detail="Organization slug already exists")

    org = models.Organization(name=name, slug=slug, created_by=user.id)
    db.add(org)
    db.flush()

    # Creator becomes owner
    mem = models.OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
        can_read=True,
        can_write=True,
    )
    db.add(mem)
    db.commit()
    db.refresh(org)

    from core.audit import log, AuditAction, AuditStatus
    log(
        db,
        action=AuditAction.ORGANIZATION_CREATE,
        status=AuditStatus.SUCCESS,
        target_type="organization",
        target_id=org.id,
        actor_user_id=user.id,
        organization_id=org.id,
    )

    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "is_active": org.is_active,
    }


@router.get("/")
def list_organizations(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    """List organizations where the user has membership (for organization switcher)."""
    user, current_user = user_context
    # Always return only orgs where the user has membership, even for superadmins
    # This endpoint is used for the organization switcher dropdown
    raw_ids = [m.get("organization_id") for m in current_user.get("memberships", [])]
    org_ids = []
    for rid in raw_ids:
        if not rid:
            continue
        if isinstance(rid, uuid.UUID):
            org_ids.append(rid)
        else:
            try:
                org_ids.append(uuid.UUID(rid))
            except ValueError:
                pass
    
    if not org_ids:
        orgs = []
    else:
        orgs = db.query(models.Organization).filter(models.Organization.id.in_(org_ids)).all()

    return [
        {
            "id": str(o.id),
            "name": o.name,
            "slug": o.slug,
            "is_active": o.is_active,
        }
        for o in orgs
    ]


@router.get("/manageable")
def list_manageable_organizations(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    """List organizations that the user can manage (own/admin role) or all organizations for superadmins."""
    user, current_user = user_context
    
    if current_user.get("is_superadmin"):
        # Superadmins can manage all organizations
        orgs = db.query(models.Organization).all()
    else:
        # Regular users can only manage organizations where they have owner or admin role
        orgs = db.query(models.Organization).join(
            models.OrganizationMembership,
            models.Organization.id == models.OrganizationMembership.organization_id
        ).filter(
            models.OrganizationMembership.user_id == user.id,
            models.OrganizationMembership.role.in_(list(get_manage_roles()))
        ).all()
    
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "slug": o.slug,
            "is_active": o.is_active,
            "created_by": str(o.created_by) if o.created_by else None,
        }
        for o in orgs
    ]

@router.get("/admin")
def list_organizations_admin(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    """List all organizations for administration purposes (superadmin only)."""
    user, current_user = user_context
    
    # Only superadmins can access this endpoint
    if not current_user.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Superadmin access required")
    
    # Return all organizations for management purposes
    orgs = db.query(models.Organization).all()
    
    return [
        {
            "id": str(o.id),
            "name": o.name,
            "slug": o.slug,
            "is_active": o.is_active,
            "created_by": str(o.created_by) if o.created_by else None,
        }
        for o in orgs
    ]


@router.get("/{org_id}")
def get_organization(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not (current_user.get("is_superadmin") or str(org_id) in current_user.get("memberships_by_org", {})):
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"id": str(org.id), "name": org.name, "slug": org.slug, "is_active": org.is_active}


@router.put("/{org_id}")
def update_organization(
    org_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    new_name = payload.get("name")
    new_slug = payload.get("slug")
    new_active = payload.get("is_active")

    old_data = {"name": org.name, "slug": org.slug, "is_active": org.is_active}
    changed = False

    if new_name and new_name != org.name:
        # Check conflict
        if db.query(models.Organization).filter(models.Organization.name == new_name, models.Organization.id != org_id).first():
            raise HTTPException(status_code=409, detail="Organization name already exists")
        org.name = new_name
        changed = True

    if new_slug is not None and new_slug != org.slug:
        if new_slug and db.query(models.Organization).filter(models.Organization.slug == new_slug, models.Organization.id != org_id).first():
            raise HTTPException(status_code=409, detail="Organization slug already exists")
        org.slug = new_slug
        changed = True

    if new_active is not None and new_active != org.is_active:
        org.is_active = bool(new_active)
        changed = True

    if changed:
        db.commit()
        db.refresh(org)

        from core.audit import log, AuditAction, AuditStatus
        log(
            db,
            action=AuditAction.ORGANIZATION_UPDATE,
            status=AuditStatus.SUCCESS,
            target_type="organization",
            target_id=org.id,
            actor_user_id=user.id,
            organization_id=org.id,
            metadata={"old_data": old_data, "new_data": {"name": org.name, "slug": org.slug, "is_active": org.is_active}},
        )

    return {"id": str(org.id), "name": org.name, "slug": org.slug, "is_active": org.is_active}


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Refuse delete if resources still reference the org
    has_agents = db.query(models.Agent).filter(models.Agent.organization_id == org_id).first() is not None
    has_memories = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).first() is not None
    has_keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).first() is not None
    if has_agents or has_memories or has_keywords:
        raise HTTPException(status_code=409, detail="Organization not empty; empty it before deletion")

    # Log the deletion BEFORE actually deleting the organization to avoid foreign key constraint issues
    from core.audit import log, AuditAction, AuditStatus
    log(
        db,
        action=AuditAction.ORGANIZATION_DELETE,
        status=AuditStatus.SUCCESS,
        target_type="organization",
        target_id=org_id,
        actor_user_id=user.id,
        organization_id=org_id,
    )

    # Delete memberships explicitly (even though they could be handled by CASCADE if configured)
    db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == org_id).delete(synchronize_session=False)
    
    # Delete any pending invitations explicitly (these have CASCADE but being explicit is safer)
    db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.organization_id == org_id).delete(synchronize_session=False)
    
    # Now delete the organization itself
    db.delete(org)
    db.commit()

    return {"status": "deleted"}


@router.get("/{org_id}/members")
def list_members(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    if not can_manage_org(org_id, current_user) and not current_user.get("is_superadmin") and str(org_id) not in current_user.get("memberships_by_org", {}):
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
    user, current_user = user_context
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

    from core.audit import log, AuditAction, AuditStatus
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
        import logging
        logger = logging.getLogger(__name__)
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
    user, current_user = user_context
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
        from core.audit import log, AuditAction, AuditStatus
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
    user, current_user = user_context
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    deleted = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user_id,
    ).delete(synchronize_session=False)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.commit()

    from core.audit import log, AuditAction, AuditStatus
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

@router.post("/{org_id}/invitations", status_code=status.HTTP_201_CREATED, response_model=schemas.OrganizationInvitation)
def create_invitation(
    org_id: uuid.UUID,
    invitation: schemas.OrganizationInvitationCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, current_user = user_context
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    from core.db import crud
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

    from core.audit import log, AuditAction, AuditStatus
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
        import logging
        logger = logging.getLogger(__name__)
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
    user, current_user = user_context

    from core.db import crud
    from datetime import datetime, timezone

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    # Allow decline either by email match or valid token
    if not (token and db_invitation.token and token == db_invitation.token):
        if (db_invitation.email or '').lower() != (user.email or '').lower():
            raise HTTPException(status_code=403, detail="Invitation is for a different user")

    if (db_invitation.status or '').lower() != 'pending':
        raise HTTPException(status_code=400, detail=f"Invitation is already {db_invitation.status}")

    from datetime import datetime, timezone as _tz
    db_invitation.status = 'revoked'
    try:
        db_invitation.revoked_at = datetime.now(_tz.utc)
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

    from core.audit import log, AuditAction, AuditStatus
    actor_id = user.id
    log(
        db,
        action=AuditAction.INVITATION_DECLINE,
        status=AuditStatus.SUCCESS,
        target_type="invitation",
        target_id=invitation_id,
        actor_user_id=actor_id,
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
    user, current_user = user_context
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    from core.db import crud
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
    user, current_user = user_context
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    from core.db import crud
    from datetime import datetime, timedelta, timezone

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
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send notification for invitation resend {db_invitation.id}: {str(e)}")

    from core.audit import log, AuditAction, AuditStatus
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
    user, current_user = user_context
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    from core.db import crud
    from datetime import datetime, timezone

    db_invitation = crud.get_organization_invitation(db, invitation_id=invitation_id)
    if not db_invitation or db_invitation.organization_id != org_id:
        raise HTTPException(status_code=404, detail="Invitation not found")

    db_invitation.status = 'revoked'
    db_invitation.revoked_at = datetime.now(timezone.utc)
    db.commit()

    from core.audit import log, AuditAction, AuditStatus
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
    user, current_user = user_context

    from core.db import crud
    from datetime import datetime, timezone
    from core.api.auth import get_or_create_user

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
            from datetime import timezone as _tz
            expires_at = expires_at.replace(tzinfo=_tz.utc)
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
    from core.db import schemas
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

    from core.audit import log, AuditAction, AuditStatus
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

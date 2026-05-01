"""
Organization CRUD endpoints.

Handles create, read, update, and delete for Organization resources,
including both user-scoped and superadmin-scoped list views.
"""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models
from core.api.deps import get_current_user_context
from core.api.permissions import can_manage_org
from core.utils.role_permissions import get_manage_roles
from core.audit import log, AuditAction, AuditStatus


router = APIRouter()


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

    user = user_context.user
    current_user = user_context.current

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
    user = user_context.user
    current_user = user_context.current
    # Always return only orgs where the user has membership, even for superadmins
    # This endpoint is used for the organization switcher dropdown
    raw_ids = [m.get("organization_id") for m in current_user.memberships]
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
    user = user_context.user
    current_user = user_context.current

    if current_user.is_superadmin:
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
    user = user_context.user
    current_user = user_context.current

    # Only superadmins can access this endpoint
    if not current_user.is_superadmin:
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
    user = user_context.user
    current_user = user_context.current
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not (current_user.is_superadmin or str(org_id) in current_user.memberships_by_org):
        raise HTTPException(status_code=403, detail="Forbidden")

    return {"id": str(org.id), "name": org.name, "slug": org.slug, "is_active": org.is_active}


@router.put("/{org_id}")
def update_organization(
    org_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user = user_context.user
    current_user = user_context.current
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
    user = user_context.user
    current_user = user_context.current
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

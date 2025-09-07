from typing import Optional, List
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_manage_org


router = APIRouter(tags=["organizations"])


def _require_current_user(db: Session,
                          x_auth_request_user: Optional[str],
                          x_auth_request_email: Optional[str],
                          x_forwarded_user: Optional[str],
                          x_forwarded_email: Optional[str]):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_or_create_user(db, email=email, display_name=name)
    # Build a compact context with memberships_by_org
    memberships = get_user_memberships(db, user.id)
    memberships_by_org = {m["organization_id"]: m for m in memberships}
    current_user = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(user.is_superadmin),
        "memberships": memberships,
        "memberships_by_org": memberships_by_org,
    }
    return user, current_user


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_organization(
    payload: dict,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    name = (payload.get("name") or "").strip()
    slug = (payload.get("slug") or None)
    if not name:
        raise HTTPException(status_code=422, detail="Organization name is required")

    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)

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
    return {
        "id": str(org.id),
        "name": org.name,
        "slug": org.slug,
        "is_active": org.is_active,
    }


@router.get("/")
def list_organizations(
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    # Return orgs where the user has membership; superadmin can see all
    if current_user.get("is_superadmin"):
        orgs = db.query(models.Organization).all()
    else:
        org_ids = [m["organization_id"] for m in current_user["memberships"]]
        orgs = db.query(models.Organization).filter(models.Organization.id.in_(org_ids)).all()
    return [
        {"id": str(o.id), "name": o.name, "slug": o.slug, "is_active": o.is_active}
        for o in orgs
    ]


@router.get("/{org_id}")
def get_organization(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
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
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    org = db.query(models.Organization).filter(models.Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    new_name = payload.get("name")
    new_slug = payload.get("slug")
    if new_name:
        exists = db.query(models.Organization).filter(models.Organization.name == new_name, models.Organization.id != org_id).first()
        if exists:
            raise HTTPException(status_code=409, detail="Organization name already exists")
        org.name = new_name
    if new_slug is not None:
        if new_slug:
            exists = db.query(models.Organization).filter(models.Organization.slug == new_slug, models.Organization.id != org_id).first()
            if exists:
                raise HTTPException(status_code=409, detail="Organization slug already exists")
        org.slug = new_slug
    db.commit()
    db.refresh(org)
    return {"id": str(org.id), "name": org.name, "slug": org.slug, "is_active": org.is_active}


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
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

    # Delete memberships first (ondelete=cascade for memberships but be explicit)
    db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == org_id).delete(synchronize_session=False)
    db.delete(org)
    db.commit()
    return {"status": "deleted"}


@router.get("/{org_id}/members")
def list_members(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
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
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    email = (payload.get("email") or "").strip().lower()
    role = (payload.get("role") or "viewer")
    can_read = bool(payload.get("can_read", True))
    can_write = bool(payload.get("can_write", False))
    if not email:
        raise HTTPException(status_code=422, detail="Email is required")

    member_user = get_or_create_user(db, email=email)
    exists = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user.id,
    ).first()
    if exists:
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
    return {"status": "added"}


@router.put("/{org_id}/members/{member_user_id}")
def update_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    m = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user_id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Membership not found")

    if "role" in payload and payload["role"]:
        m.role = payload["role"]
    if "can_read" in payload:
        m.can_read = bool(payload["can_read"])
    if "can_write" in payload:
        m.can_write = bool(payload["can_write"])
    db.commit()
    return {"status": "updated"}


@router.delete("/{org_id}/members/{member_user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    org_id: uuid.UUID,
    member_user_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    deleted = db.query(models.OrganizationMembership).filter(
        models.OrganizationMembership.organization_id == org_id,
        models.OrganizationMembership.user_id == member_user_id,
    ).delete(synchronize_session=False)
    if deleted == 0:
        raise HTTPException(status_code=404, detail="Membership not found")
    db.commit()
    return {"status": "removed"}


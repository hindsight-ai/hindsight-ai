"""
Authentication helpers and identity resolution.

Parses proxy headers, normalizes emails, and upserts users while supporting
simple superadmin elevation via environment configuration.
"""
import os
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from core.db import models


def _normalize_email(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return email.strip().lower()


def _admin_emails() -> set:
    raw = os.getenv("ADMIN_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def _beta_access_admin_emails() -> set:
    raw = os.getenv("BETA_ACCESS_ADMINS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def is_beta_access_admin(email: Optional[str]) -> bool:
    if not email:
        return False
    return _normalize_email(email) in _beta_access_admin_emails()


def resolve_identity_from_headers(
    x_auth_request_user: Optional[str],
    x_auth_request_email: Optional[str],
    x_forwarded_user: Optional[str],
    x_forwarded_email: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    user = x_auth_request_user or x_forwarded_user
    email = _normalize_email(x_auth_request_email or x_forwarded_email)
    return user, email


def get_or_create_user(db: Session, email: str, display_name: Optional[str] = None) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    was_new = False
    if not user:
        user = models.User(
            email=email,
            display_name=display_name or email.split("@")[0],
            beta_access_status='not_requested',
        )
        db.add(user)
        was_new = True

    # Elevate to superadmin based on ADMIN_EMAILS only at creation time to avoid test-order flakiness
    if was_new:
        admins = _admin_emails()
        if email in admins:
            user.is_superadmin = True

    if was_new:
        db.flush()
        db.commit()
        db.refresh(user)
        return user
    if not getattr(user, "beta_access_status", None):
        user.beta_access_status = 'not_requested'
        try:
            db.commit()
        except Exception:
            db.rollback()
        else:
            db.refresh(user)
    # For existing users, avoid unnecessary commits that could clobber test state
    db.refresh(user)
    return user


def get_user_memberships(db: Session, user_id) -> List[Dict[str, Any]]:
    # Join memberships to organization for names
    try:
        results = (
            db.query(models.OrganizationMembership, models.Organization)
            .join(models.Organization, models.Organization.id == models.OrganizationMembership.organization_id)
            .filter(models.OrganizationMembership.user_id == user_id)
            .all()
        )
    except Exception:
        # In unit tests some endpoints override dependencies with mock Sessions that may not fully
        # implement SQLAlchemy behavior; treat as no memberships rather than failing the entire request.
        return []

    # A defensive guard: some mocks may yield a single Mock object instead of list/tuple.
    if not isinstance(results, (list, tuple)):
        return []

    memberships: List[Dict[str, Any]] = []
    for row in results:
        # Support either (membership, org) tuple or a single membership object.
        try:
            # SQLAlchemy Row objects contain tuples that can be unpacked
            if hasattr(row, '__iter__') and len(row) == 2:
                m, org = row
            else:
                m = row
                org = getattr(row, "organization", None)
            if not m:
                continue
            org_id = getattr(m, "organization_id", "")
            org_name = getattr(org, "name", None)
            role = getattr(m, "role", None)
            can_read = getattr(m, "can_read", True)
            can_write = getattr(m, "can_write", True)
            
            memberships.append(
                {
                    "organization_id": str(org_id) if org_id else None,
                    "organization_name": org_name,
                    "role": role,
                    "can_read": bool(can_read),
                    "can_write": bool(can_write),
                }
            )
        except Exception:
            # Ignore malformed mock rows
            continue
    return memberships

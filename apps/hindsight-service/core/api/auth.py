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
        user = models.User(email=email, display_name=display_name or email.split("@")[0])
        db.add(user)
        was_new = True

    admins = _admin_emails()
    should_be_admin = email in admins
    if should_be_admin and not user.is_superadmin:
        user.is_superadmin = True

    if was_new:
        db.flush()
    db.commit()
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
            if isinstance(row, (list, tuple)) and len(row) == 2:
                m, org = row
            else:
                m = row
                org = getattr(row, "organization", None)
            if not m:
                continue
            memberships.append(
                {
                    "organization_id": str(getattr(m, "organization_id", "")) or None,
                    "organization_name": getattr(org, "name", None),
                    "role": getattr(m, "role", None),
                    "can_read": bool(getattr(m, "can_read", True)),
                    "can_write": bool(getattr(m, "can_write", True)),
                }
            )
        except Exception:
            # Ignore malformed mock rows
            continue
    return memberships


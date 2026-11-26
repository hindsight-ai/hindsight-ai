"""
Permission checks for resource access control.

Key helpers:
- can_read(resource, current_user)
- can_write(resource, current_user)
- can_manage_org(org_id, current_user)
- can_move_scope(resource, target_scope, target_org_id, current_user)
"""
from typing import Optional, Dict, Any
from core.utils.role_permissions import (
    role_allows_write as _role_allows_write,
    role_allows_manage as _role_allows_manage,
)
from core.utils.scopes import (
    SCOPE_PUBLIC,
    SCOPE_PERSONAL,
    SCOPE_ORGANIZATION,
)

# Optional import for DB fallback; keep local to avoid heavy module load at import time
try:  # pragma: no cover - safe import for runtime
    from core.db import models as _db_models
except Exception:  # pragma: no cover - tests may import without DB wired
    _db_models = None
def get_org_membership(org_id, current_user: Optional[Dict[str, Any]]):
    """Get organization membership for a user with proper error handling."""
    if not current_user:
        return None

    if org_id is None:
        return None

    try:
        str_id = str(org_id)
        by_org = current_user.memberships_by_org or {}
        m = by_org.get(str_id) or by_org.get(org_id)
        if m:
            return m

        for item in current_user.memberships or []:
            try:
                if item and item.get("organization_id") in (str_id, org_id, getattr(org_id, "hex", None)):
                    return item
            except (AttributeError, TypeError):
                continue
    except (TypeError, ValueError):
        pass
    
    return None


# Public API delegates to role and scope utilities where appropriate.


def can_read(resource, current_user: Optional[Dict[str, Any]]) -> bool:
    """Check if user can read a resource with proper validation."""
    if resource is None:
        return False
        
    try:
        # Public data is always readable
        if getattr(resource, "visibility_scope", None) == SCOPE_PUBLIC:
            return True

        if current_user is None:
            return False

        if current_user.is_superadmin:
            return True

        uid = current_user.id
        visibility_scope = getattr(resource, "visibility_scope", None)
        
        if visibility_scope == SCOPE_PERSONAL:
            return getattr(resource, "owner_user_id", None) == uid

        if visibility_scope == SCOPE_ORGANIZATION:
            org_id = getattr(resource, "organization_id", None)
            if not org_id:
                return False
            
            membership = get_org_membership(org_id, current_user)
            return bool(membership and (
                membership.get("can_read") or 
                _role_allows_write(membership.get("role", "viewer"))
            ))

        return False
    except (AttributeError, TypeError):
        return False


def can_write(resource, current_user: Optional[Dict[str, Any]]) -> bool:
    """Check if user can write to a resource with proper validation."""
    if resource is None or current_user is None:
        return False

    try:
        if current_user.is_superadmin:
            return True

        uid = current_user.id
        visibility_scope = getattr(resource, "visibility_scope", None)
        
        if visibility_scope == SCOPE_PERSONAL:
            return getattr(resource, "owner_user_id", None) == uid
            
        if visibility_scope == SCOPE_ORGANIZATION:
            org_id = getattr(resource, "organization_id", None)
            if not org_id:
                return False
                
            membership = get_org_membership(org_id, current_user)
            return bool(membership and (
                _role_allows_write(membership.get("role", "viewer")) or 
                membership.get("can_write")
            ))
            
        # Public is not editable except by superadmin
        return False
    except (AttributeError, TypeError):
        return False


def can_manage_org(org_id, current_user: Optional[Dict[str, Any]]) -> bool:
    """Check if user can manage an organization. Simplified wrapper around can_manage_org_effective."""
    return can_manage_org_effective(org_id, current_user, allow_db_fallback=False)


def is_member_of_org(org_id, current_user: Optional[Dict[str, Any]], *, db=None, user_id=None, allow_db_fallback: bool = True) -> bool:
    """Return True if user is member of org. Simplified with optional DB fallback."""
    if not current_user or org_id is None:
        return False

    # Superadmin bypass - superadmins are considered members of all orgs
    if current_user.is_superadmin:
        return True
        
    # Check in-memory membership first
    if get_org_membership(org_id, current_user):
        return True
        
    # Optional DB fallback
    if allow_db_fallback and db is not None and user_id is not None and _db_models is not None:
        try:
            mem = db.query(_db_models.OrganizationMembership).filter(
                _db_models.OrganizationMembership.organization_id == org_id,
                _db_models.OrganizationMembership.user_id == user_id,
            ).first()
            return bool(mem)
        except Exception:
            pass
            
    return False


def can_manage_org_effective(org_id, current_user: Optional[Dict[str, Any]], *, db=None, user_id=None, allow_db_fallback: bool = True) -> bool:
    """Check if user can manage organization with optional DB fallback. Replaces can_manage_org for all uses."""
    if current_user is None or org_id is None:
        return False

    try:
        if current_user.is_superadmin:
            return True
            
        # Check in-memory membership first
        membership = get_org_membership(org_id, current_user)
        if membership and _role_allows_manage(membership.get("role", "viewer")):
            return True
            
        # Optional DB fallback
        if allow_db_fallback and db is not None and user_id is not None and _db_models is not None:
            try:
                mem = db.query(_db_models.OrganizationMembership).filter(
                    _db_models.OrganizationMembership.organization_id == org_id,
                    _db_models.OrganizationMembership.user_id == user_id,
                ).first()
                return bool(mem and _role_allows_manage(getattr(mem, "role", "viewer")))
            except Exception:
                pass
                
        return False
    except (AttributeError, TypeError):
        return False


def can_move_scope(resource, target_scope: str, target_org_id, current_user: Optional[Dict[str, Any]]) -> bool:
    """Check if user can move a resource to a target scope with proper validation."""
    if current_user is None or resource is None or not target_scope:
        return False

    try:
        if current_user.is_superadmin:
            return True

        if target_scope == SCOPE_ORGANIZATION:
            if target_org_id is None:
                return False
            # Require admin (or owner) of target org
            return can_manage_org(target_org_id, current_user)

        if target_scope == SCOPE_PERSONAL:
            # Only the resource owner can move to personal scope
            return getattr(resource, "owner_user_id", None) == current_user.id
            
        if target_scope == SCOPE_PUBLIC:
            # Only superadmin can move to public (handled above)
            return False
            
        return False
    except (AttributeError, TypeError):
        return False


def ensure_can_publish(
    current_user,
    target_scope,
    *,
    db=None,
    target_type: Optional[str] = None,
    target_id=None,
    audit_action=None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Single gate for every write that would make content publicly visible.

    Raises HTTP 403 unless ``target_scope`` is non-public or the caller is a
    superadmin. When a non-superadmin is refused and ``db`` plus ``audit_action``
    are supplied, a failure audit row is recorded (best effort; skipped for
    anonymous callers because audit_logs.actor_user_id is NOT NULL).
    """
    from fastapi import HTTPException

    scope_value = getattr(target_scope, "value", target_scope)
    if scope_value != SCOPE_PUBLIC:
        return
    if current_user is not None and getattr(current_user, "is_superadmin", False):
        return
    actor_id = getattr(current_user, "id", None)
    if db is not None and audit_action is not None and actor_id is not None:
        try:
            from core.audit import log, AuditStatus

            md = {"to_scope": SCOPE_PUBLIC, "reason": "only superadmin can publish"}
            if metadata:
                md.update(metadata)
            log(
                db,
                action=audit_action,
                status=AuditStatus.FAILURE,
                target_type=target_type or "unknown",
                target_id=target_id,
                actor_user_id=actor_id,
                metadata=md,
            )
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    raise HTTPException(status_code=403, detail="Only superadmin can publish to public")


def ensure_can_write_memory_block(current_user, block, *, db=None, audit_action=None) -> bool:
    """Return True if ``current_user`` may modify ``block``.

    On refusal, records a failure audit row (best effort) and returns False so
    callers can raise 403 or skip-and-report per item. Public rows are
    superadmin-only (see can_write).
    """
    if can_write(block, current_user):
        return True
    actor_id = getattr(current_user, "id", None)
    if db is not None and audit_action is not None and actor_id is not None and block is not None:
        try:
            from core.audit import log, AuditStatus

            log(
                db,
                action=audit_action,
                status=AuditStatus.FAILURE,
                target_type="memory_block",
                target_id=block.id,
                actor_user_id=actor_id,
                metadata={"scope": block.visibility_scope, "reason": "no write permission"},
            )
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass
    return False

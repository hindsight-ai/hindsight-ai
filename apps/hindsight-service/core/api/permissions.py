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
        by_org = current_user.get("memberships_by_org", {}) or {}
        m = by_org.get(str_id) or by_org.get(org_id)
        if m:
            return m
            
        for item in current_user.get("memberships", []) or []:
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
            
        if current_user.get("is_superadmin"):
            return True

        uid = current_user.get("id")
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
        if current_user.get("is_superadmin"):
            return True
            
        uid = current_user.get("id")
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
    if current_user.get("is_superadmin"):
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
        if current_user.get("is_superadmin"):
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
        if current_user.get("is_superadmin"):
            return True
            
        if target_scope == SCOPE_ORGANIZATION:
            if target_org_id is None:
                return False
            # Require admin (or owner) of target org
            return can_manage_org(target_org_id, current_user)
            
        if target_scope == SCOPE_PERSONAL:
            # Only the resource owner can move to personal scope
            return getattr(resource, "owner_user_id", None) == current_user.get("id")
            
        if target_scope == SCOPE_PUBLIC:
            # Only superadmin can move to public (handled above)
            return False
            
        return False
    except (AttributeError, TypeError):
        return False

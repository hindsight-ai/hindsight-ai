from typing import Optional, Dict, Any


def _role_allows_write(role: str) -> bool:
    return role in ("owner", "admin", "editor")


def _role_allows_manage(role: str) -> bool:
    return role in ("owner", "admin")


def can_read(resource, current_user: Optional[Dict[str, Any]]) -> bool:
    # Public data is always readable
    if getattr(resource, "visibility_scope", None) == "public":
        return True
    if current_user is None:
        return False
    if current_user.get("is_superadmin"):
        return True

    uid = current_user.get("id")
    if getattr(resource, "visibility_scope", None) == "personal":
        return getattr(resource, "owner_user_id", None) == uid

    if getattr(resource, "visibility_scope", None) == "organization":
        org_id = getattr(resource, "organization_id", None)
        if not org_id:
            return False
        m = current_user.get("memberships_by_org", {}).get(str(org_id))
        return bool(m and (m.get("can_read") or _role_allows_write(m.get("role", "viewer"))))

    return False


def can_write(resource, current_user: Optional[Dict[str, Any]]) -> bool:
    if current_user is None:
        return False
    if current_user.get("is_superadmin"):
        return True
    uid = current_user.get("id")
    if getattr(resource, "visibility_scope", None) == "personal":
        return getattr(resource, "owner_user_id", None) == uid
    if getattr(resource, "visibility_scope", None) == "organization":
        org_id = getattr(resource, "organization_id", None)
        if not org_id:
            return False
        m = current_user.get("memberships_by_org", {}).get(str(org_id))
        return bool(m and (_role_allows_write(m.get("role", "viewer")) or m.get("can_write")))
    # Public is not editable except by superadmin
    return False


def can_manage_org(org_id, current_user: Optional[Dict[str, Any]]) -> bool:
    if current_user is None:
        return False
    if current_user.get("is_superadmin"):
        return True
    m = current_user.get("memberships_by_org", {}).get(str(org_id))
    return bool(m and _role_allows_manage(m.get("role", "viewer")))


def can_move_scope(resource, target_scope: str, target_org_id, current_user: Optional[Dict[str, Any]]) -> bool:
    if current_user is None:
        return False
    if current_user.get("is_superadmin"):
        return True
    if target_scope == "organization":
        # Require admin (or owner) of target org
        return can_manage_org(target_org_id, current_user)
    if target_scope == "personal":
        # Only the personal owner can move to self
        return getattr(resource, "owner_user_id", None) == current_user.get("id")
    if target_scope == "public":
        # Only superadmin handled above
        return False
    return False


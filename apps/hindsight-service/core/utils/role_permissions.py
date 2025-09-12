"""
Role-based permission utilities for organization members.

This module provides dynamic role-based permission management that can be easily
configured and extended without modifying core business logic.
"""

from typing import Dict, Set


# Role-based permission configuration
# This defines what permissions each role should have by default
ROLE_PERMISSIONS = {
    "owner": {
        "can_read": True,
        "can_write": True,
    },
    "admin": {
        "can_read": True,
        "can_write": True,
    },
    "editor": {
        "can_read": True,
        "can_write": True,
    },
    "viewer": {
        "can_read": True,
        "can_write": False,
    },
}

ALLOWED_ROLES = set(ROLE_PERMISSIONS.keys())


def get_role_permissions(role: str) -> Dict[str, bool]:
    """
    Get the default permissions for a given role.

    Args:
        role: The role name (owner, admin, editor, viewer)

    Returns:
        Dict with can_read and can_write boolean values

    Raises:
        ValueError: If role is not recognized
    """
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {role}. Allowed roles: {list(ROLE_PERMISSIONS.keys())}")

    return ROLE_PERMISSIONS[role].copy()


def get_allowed_roles() -> Set[str]:
    """Get the set of all allowed roles."""
    return ALLOWED_ROLES.copy()


def validate_role(role: str) -> None:
    """
    Validate that a role is allowed.

    Args:
        role: The role name to validate

    Raises:
        ValueError: If role is not allowed
    """
    if role not in ALLOWED_ROLES:
        raise ValueError(f"Invalid role '{role}'. Allowed roles: {sorted(ALLOWED_ROLES)}")


def update_permissions_for_role(role: str, can_read: bool = None, can_write: bool = None) -> Dict[str, bool]:
    """
    Get permissions for a role, with optional overrides.

    Args:
        role: The role name
        can_read: Optional override for can_read permission
        can_write: Optional override for can_write permission

    Returns:
        Dict with final permissions
    """
    permissions = get_role_permissions(role)

    if can_read is not None:
        permissions["can_read"] = can_read
    if can_write is not None:
        permissions["can_write"] = can_write

    return permissions

"""
Role-based permission utilities for organization members.

This module provides dynamic role-based permission management that can be easily
configured and extended without modifying core business logic.
"""

from typing import Dict, Set, FrozenSet
from enum import Enum


# Role-based permission configuration
# This defines what permissions each role should have by default
# Central role constants to ensure consistency across the codebase
ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "viewer"
ROLE_PERMISSIONS = {
    ROLE_OWNER: {
        "can_read": True,
        "can_write": True,
    },
    ROLE_ADMIN: {
        "can_read": True,
        "can_write": True,
    },
    ROLE_EDITOR: {
        "can_read": True,
        "can_write": True,
    },
    ROLE_VIEWER: {
        "can_read": True,
        "can_write": False,
    },
}

ALLOWED_ROLES = set(ROLE_PERMISSIONS.keys())

# Derived role groups
WRITE_ROLES: FrozenSet[str] = frozenset({ROLE_OWNER, ROLE_ADMIN, ROLE_EDITOR})
MANAGE_ROLES: FrozenSet[str] = frozenset({ROLE_OWNER, ROLE_ADMIN})


class RoleEnum(str, Enum):
    """Enum for organization roles used in schemas and validation."""
    owner = ROLE_OWNER
    admin = ROLE_ADMIN
    editor = ROLE_EDITOR
    viewer = ROLE_VIEWER


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

def get_manage_roles() -> Set[str]:
    """Get the set of roles allowed to manage an organization."""
    return set(MANAGE_ROLES)

def get_write_roles() -> Set[str]:
    """Get the set of roles allowed to write within an organization."""
    return set(WRITE_ROLES)


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


def role_allows_write(role: str) -> bool:
    """Return True if the role implies write permissions by default."""
    return role in WRITE_ROLES


def role_allows_manage(role: str) -> bool:
    """Return True if the role implies organization management permissions."""
    return role in MANAGE_ROLES

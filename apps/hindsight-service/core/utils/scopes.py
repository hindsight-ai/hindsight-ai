"""
Visibility scope constants and helpers.

Centralized definitions for resource visibility scopes to eliminate
string literals scattered across the codebase.
"""

from typing import FrozenSet
from enum import Enum

# Canonical scope values stored in the database
SCOPE_PUBLIC = "public"
SCOPE_ORGANIZATION = "organization"
SCOPE_PERSONAL = "personal"

# All valid scopes
ALL_SCOPES: FrozenSet[str] = frozenset({SCOPE_PUBLIC, SCOPE_ORGANIZATION, SCOPE_PERSONAL})


def is_valid_scope(scope: str) -> bool:
    """Return True if the provided scope is one of the supported values."""
    return scope in ALL_SCOPES


class VisibilityScopeEnum(str, Enum):
    """Enum for visibility scopes used in schemas and validation."""
    public = SCOPE_PUBLIC
    organization = SCOPE_ORGANIZATION
    personal = SCOPE_PERSONAL

# Dynamic Role-Based Permission System

This system provides a flexible way to manage organization member permissions based on their roles. Instead of hardcoding permission logic throughout the codebase, permissions are defined in a central configuration that can be easily modified.

## Overview

The system consists of:

1. **Role Permissions & Enums** (`core/utils/role_permissions.py`)
2. **Visibility Scopes & Enums** (`core/utils/scopes.py`)
3. **API Integration** (e.g., `core/api/orgs.py`, `core/api/permissions.py`)
4. **Query Filtering Utilities** (`core/db/scope_utils.py`)

## How It Works

### Role Permissions Configuration

The `ROLE_PERMISSIONS` dictionary defines the default permissions for each role:

```python
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
```

### API Usage

When adding or updating members, APIs should validate roles via the enum and derive defaults via the central permissions:

```python
from core.utils.role_permissions import get_role_permissions, RoleEnum

# Example: in add_member
role = RoleEnum.viewer  # validated by Pydantic in schemas
role_permissions = get_role_permissions(role.value)
can_read = payload.get("can_read", role_permissions["can_read"])
can_write = payload.get("can_write", role_permissions["can_write"])
```

For resource scopes, use shared constants/enums instead of string literals:

```python
from core.utils.scopes import (
    SCOPE_PUBLIC, SCOPE_ORGANIZATION, SCOPE_PERSONAL, VisibilityScopeEnum
)

scope = VisibilityScopeEnum.personal
if scope == VisibilityScopeEnum.organization:
    # apply org-specific logic
    ...

# Or compare using string constants
if resource.visibility_scope == SCOPE_PUBLIC:
    ...
```

## Benefits

1. **Centralized Configuration**: All role permissions are defined in one place
2. **Easy to Modify**: Change permissions without touching business logic
3. **Extensible**: Add new roles or modify existing ones easily
4. **Consistent**: Same permission logic used across all endpoints
5. **Override Support**: Still allows explicit permission overrides when needed

## Adding a New Role

To add a new role (e.g., "moderator"):

1. Add it to the `ROLE_PERMISSIONS` dictionary:
   ```python
   "moderator": {
       "can_read": True,
       "can_write": False,  # Can read but not write
   },
   ```

2. The system will automatically handle it in all API endpoints

If you add a new role, also update tests if needed and ensure any business logic that checks management rights imports `role_allows_manage`.

## Modifying Existing Permissions

To change what an existing role can do:

1. Update the `ROLE_PERMISSIONS` dictionary
2. If needed, run any data migration scripts to normalize existing rows (none required by default in dev/testing).

## Testing

Execute the service test suite (unit + non‑e2e integration):

```bash
cd apps/hindsight-service
uv run --isolated --extra test pytest -q -m "not e2e"
```

Key tests covering permissions and roles:
- `tests/unit/test_role_permissions.py`
- `tests/unit/test_permissions.py`
- `tests/unit/test_permissions_helpers.py`

Integration paths also exercise permission enforcement via the APIs.

## Visibility Scopes (Centralized)

- Constants: `core/utils/scopes.py` exports `SCOPE_PUBLIC`, `SCOPE_ORGANIZATION`, `SCOPE_PERSONAL` and `ALL_SCOPES`.
- Enum: `VisibilityScopeEnum` for schema fields and comparisons.
- Query helpers: `core/db/scope_utils.py` applies scope filters consistently across models.

Do:
- Import and compare against the shared constants/enums.
- Use `ALL_SCOPES` to validate inputs.

Don’t:
- Hardcode strings like `"public"`, `"organization"`, or `"personal"` in new code.

## Files Modified

- `core/utils/role_permissions.py` - Role config + RoleEnum + helpers
- `core/utils/scopes.py` - Scope constants + VisibilityScopeEnum
- `core/api/orgs.py` - Uses centralized roles for validation/queries
- `core/api/permissions.py` - Delegates to role helpers; uses scope constants
- `core/db/scope_utils.py` - Uses scope constants for filtering
- `tests/unit/test_role_permissions.py` - Covers role behaviors

# Security Model (Roles & Scopes)

This service enforces access controls via organization roles and resource visibility scopes.

## Roles

- Defined centrally in `core/utils/role_permissions.py` with `RoleEnum` and `ROLE_PERMISSIONS`.
- Roles: `owner`, `admin`, `editor`, `viewer`.
- Helpers:
  - `role_allows_manage(role)`: owners/admins can manage org resources/members.
  - `role_allows_write(role)`: owners/admins/editors can write.

## Scopes

- Defined in `core/utils/scopes.py` with constants and `VisibilityScopeEnum`.
- Scopes: `personal`, `organization`, `public`.
- Helpers in `core/db/scope_utils.py` apply scope filters to queries and validate access.

## Permission Checks

- `core/api/permissions.py` exposes:
  - `can_read(resource, user_ctx)`
  - `can_write(resource, user_ctx)`
  - `can_manage_org(org_id, user_ctx)` (wrapper)
  - `can_manage_org_effective(org_id, user_ctx, *, db=None, user_id=None, allow_db_fallback=True)`
  - `can_move_scope(resource, target_scope, target_org_id, user_ctx)`

Notes:
- Superadmins (flag on user) bypass checks appropriately.
- Endpoints narrow queries with `scope_utils.apply_scope_filter()` and optional user-requested narrowing.
- Pydantic schemas validate roles/scopes using `RoleEnum` and `VisibilityScopeEnum`.

## Where to Import

- Use `core.utils.role_permissions` for roles and helpers.
- Use `core.utils.scopes` for scope constants/enums.
- Avoid string literals for roles/scopes in new code.


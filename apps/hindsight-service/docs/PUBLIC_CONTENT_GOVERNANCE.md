# Public content governance

Rule: only a superadmin can make memory blocks, agents or keywords publicly
visible (`visibility_scope = 'public'`), and every public publication or scope
change is written to `audit_logs`.

## Single gate

`core.api.permissions.ensure_can_publish(current_user, target_scope, *, db, target_type, target_id, audit_action, metadata)`
raises HTTP 403 for any non-superadmin when `target_scope == 'public'`. When
`db` and `audit_action` are given it also records a **failure** audit row for
the refused actor ("who tried to publish"). Anonymous callers are not logged
(`audit_logs.actor_user_id` is NOT NULL). Every public-producing endpoint calls
it; do not re-implement the check inline.

## Audit rows

| Event | action_type | status | metadata |
|---|---|---|---|
| Public create allowed | `memory_create` / `agent_create` / `keyword_create` | success | `from_scope: null, to_scope: public` |
| Public create refused | same | failure | `to_scope: public, reason` |
| Scope change allowed | `memory_scope_change` / `agent_scope_change` | success | `from_scope, to_scope` (plus legacy `old_scope/new_scope`, org/owner ids) |
| Scope change to public refused | same | failure | `from_scope, to_scope: public` |
| Keyword update body requesting a scope refused | `keyword_update` | failure | `from_scope, to_scope` |

Non-public memory creates are not audited (hot path); agent and keyword creates
are always audited.

## Inventory of write paths

All tests are in `tests/integration/permissions/test_public_publish_governance.py`.

| Path | Can it produce public? | Guard | Proving test(s) |
|---|---|---|---|
| `POST /memory-blocks/`, `/agents/`, `/keywords/` | Only via request scope (header `X-Active-Scope` or `?scope=`); body `visibility_scope` is overwritten | `ensure_can_publish` | `test_create_public_refused_for_non_superadmin`, `..._via_query_param_...`, `test_body_visibility_scope_cannot_force_public`, `test_create_public_allowed_for_superadmin_*` |
| `POST /memory-blocks/{id}/change-scope`, `/agents/{id}/change-scope` | Yes (`payload.visibility_scope`) | `ensure_can_publish`; PAT write scope required for every target | `test_change_scope_to_public_*`, `test_every_scope_change_is_audited_with_from_and_to`, `test_change_scope_public_refused_for_read_only_pat_of_superadmin` |
| `PUT /keywords/{id}` | Body `KeywordUpdate.visibility_scope` was an open path | `ensure_can_publish`, then any other scope change is 422 | `test_keyword_update_*` |
| `PUT /memory-blocks/{id}`, `PUT /agents/{id}` | No: update schemas have no scope fields; extra fields are dropped | schema + `can_write` (public rows are superadmin-only) | `test_update_body_visibility_scope_is_ignored`, `test_non_superadmin_cannot_edit_public_content` |
| Keyword auto-creation on memory create | Inherits the memory block's scope; personal/org never becomes public | `crud.create_memory_block` uses block scope | `test_public_memory_create_keywords_inherit_public_scope`, `test_personal_memory_create_never_creates_public_keywords` |
| `POST /consolidation-suggestions/{id}/validate/` | Merged block copies originals' scope; originals must share scope/owner/org and caller needs write on all | `can_write` (public: superadmin only), mismatch check | `test_consolidation_*` |
| Bulk move (`/bulk-operations/.../bulk-move`, `core/async_bulk_operations.py`) | No: destination scope is only organization or personal | `_destination_visibility_scope` | `test_bulk_move_destination_scope_is_never_public` |
| `/memory-blocks/bulk-*`, compress, prune, optimization execute, suggest-keywords, consolidation reject/delete | No: only a `scope` hint, no scope write | none needed | `test_scope_hint_on_other_write_routes_cannot_publish` |
| PAT-authenticated calls to any of the above | Same code paths; PAT never widens permissions | `ensure_pat_allows_write` + `ensure_can_publish` | `*_pat*` parametrizations |
| MCP-facing endpoints | They call the same REST endpoints with a PAT | as above | PAT tests |

## CI guard

`test_every_write_route_exposing_a_scope_field_is_governed` enumerates all
POST/PUT/PATCH/DELETE routes of the FastAPI app and fails if a route whose body
model or query params contain `visibility_scope`, `scope` or `target_scope`
(or whose body is an untyped dict) is missing from `PUBLISH_ROUTE_ALLOWLIST`.
A stale allowlist entry also fails. New endpoint: route public decisions through
`ensure_can_publish`, add a test, list the route, add a row above.

## Known adjacent gaps (not visibility, not changed)

- `POST /memory-blocks/{id}/compress/apply`, `/memory/prune/confirm` and
  `/memory-blocks/bulk-apply-keywords` do not check `can_write` on the target
  block (content tampering, including of public blocks, by any authenticated user).
- `bulk-apply-keywords` creates a keyword without an owner, which violates
  `ck_keywords_personal_owner` and fails.

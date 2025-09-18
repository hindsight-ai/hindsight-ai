# Test Coverage Plan

Goal: build a pragmatic roadmap toward ~90 % coverage for `apps/hindsight-service`
and confidence-check the MCP server. This document captures the highest-impact
areas (modules with most uncovered logic) and specifies concrete test scenarios
sufficiently detailed to start implementing immediately.

## Current Snapshot (pytest --no-cov tests/unit/test_beta_access.py)

Global coverage ≈78 %. The largest gaps come from API orchestration modules and
long services:

| Module | Coverage | Missing stmts | Missing branches |
|--------|----------|---------------|------------------|
| `core/api/bulk_operations.py` | 54 % | 106 | 59 |
| `core/services/notification_service.py` | 75 % | 121 | 60 |
| `core/api/main.py` (routing glue) | 70 % | 166 | 56 |
| `core/api/memory_optimization.py` | 61 % | 48 | 21 |
| `core/workers/consolidation_worker.py` | 62 % | 72 | 18 |
| `core/db/repositories/organizations.py` | 64 % | 40 | 10 |
| `core/api/deps.py` | 76 % | 52 | 22 |
| `core/services/beta_access_service.py` | 83 % | 15 | 13 |
| `core/api/beta_access.py` | 81 % | 13 | 7 |
| `core/async_bulk_operations.py` | 79 % | 48 | 12 |

## Prioritisation Rationale

1. **Bulk operations + consolidation worker**: complex control flow, heavy
   branching; bugs here are high risk (data deletion/merge). Tests currently hit
   only happy paths.
2. **Notification service**: 120+ missing lines covering template dispatch,
   tokenized links, and error handling. These support user onboarding (beta
   access) and invites, so regressions would be visible.
3. **Beta-access flow**: new token logic recently added; we already touched unit
   tests but coverage is still <85 %. Branch coverage in both service and API is
   missing for denial flows, expired tokens, etc.
4. **Organization repository**: data-layer invariants (pending-invite checks,
   resends) underpin the dashboard UX; add tests to prevent DB regressions.
5. **Memory optimisation API**: numerous branches for pruning/compression; vital
   to verify both success/error flows.
6. **`core/api/deps.py`**: gatekeeper for auth/scope; untested branches for PAT
   restrictions, invalid header combos.
7. **MCP server**: currently lacks automated tests despite being a publishable
   package.

## Test Work Items

Each section describes: purpose, new test targets, scenarios, involved fixtures,
expected assertions, and coverage impact.

### 1. Bulk Operations API (`core/api/bulk_operations.py`)

**Purpose**: exercise queueing, preview, and pruning endpoints across success,
validation, and permission errors.

**Tests to add** (FastAPI `TestClient`, existing `db_session` fixture, mark
`integration` where DB is needed):

1. `test_bulk_delete_preview_requires_write` — create a memory block with
   `can_write=False` membership; expect 403.
2. `test_bulk_delete_preview_success` — set up agent + memories, call preview
   with filters, assert payload contains expected IDs and 202 response.
3. `test_bulk_delete_execute_invalid_request_id` — call `DELETE /bulk-operations/delete/{id}` with unknown ID; expect 404.
4. `test_bulk_delete_execute_success` — end-to-end: preview, capture job ID,
   execute deletion, assert memories removed and asynchronous task enqueued
   (poke `AsyncBulkOperationsService` test double to verify `enqueue_delete`).
5. `test_bulk_merge_preview_conflict_scope` — attempt to merge memories from
   different scopes -> expect 409.
6. `test_bulk_merge_execute_success` — verify consolidation suggestions are
   produced and worker receives job.
7. `test_bulk_operations_requires_scope_headers` — ensure missing scope triggers
   422/403 as appropriate.

**Impact**: reduce missing statements/branches by ~70 lines.

**Progress (2025-09-13)**
- Added integration tests covering: preview without write access (`test_bulk_delete_preview_allows_member_without_write`), execution forbidden for non-managers (`test_bulk_delete_requires_manage_permission_for_execution`), async dispatch for execute path (`test_bulk_delete_start_triggers_async_task`), admin status 404 path (`test_get_operation_status_not_found_for_superadmin` via direct call).
- Coverage gain pending full suite run.

### 2. Consolidation Worker (`core/workers/consolidation_worker.py`)

**Purpose**: cover consolidation job paths (success, empty payload, invalid
status transitions).

**Tests** (unit tests with `pytest.mark.asyncio`):

1. `test_worker_handles_empty_suggestions` — call worker entry point with empty
   suggestion list; assert no DB writes.
2. `test_worker_applies_suggestion` — seed two memories and a suggestion; run
   worker; assert merged memory saved, originals archived, audit log generated.
3. `test_worker_marks_failure_on_exception` — monkeypatch repository to raise;
   worker should mark suggestion `failed` and log error.
4. `test_worker_respects_scope_headers` — ensure `ScopeContext` is applied (set
   org ID, check query uses RLS).

**Impact**: cover 50+ missing lines and branch cases.

### 3. Async Bulk Operations Service (`core/async_bulk_operations.py`)

Add unit tests for helper functions used by API/controller:

1. `test_enqueue_delete_persists_job` — ensure job row stored with `status='queued'`.
2. `test_enqueue_merge_validates_payload` — invalid payload raises `ValueError`.
3. `test_run_pending_jobs_handles_unknown_type` — unknown `operation_type` marks
   job failed.
4. `test_run_pending_jobs_dispatches_delete` / `..._merge` — patch worker methods
   to assert proper invocation and job status transitions.

### 4. Notification Service (`core/services/notification_service.py`)

Focus on beta-access and invitation workflows:

1. `test_notify_beta_access_request_confirmation_handles_render_failure` — mock
   `render_template` to raise; ensure result `success=False` and error captured
   without blowing up.
2. `test_notify_beta_access_admin_notification_builds_token_links` — pass
   `review_token`; assert accept/deny URLs use `APP_BASE_URL` and include token.
3. `test_notify_beta_access_admin_notification_no_token` — ensure fallback URL.
4. `test_notify_beta_access_acceptance_sends_email` — asynchronous `send_email`
   path; result `success=True`.
5. `test_notify_beta_access_denial_handles_async_send` — cover awaitable send.
6. `test_notify_beta_access_request_confirmation_async_function` — patch
   `send_email` to be async, ensure run via `asyncio.run` and success result.
7. Similar tests for organization invitation helpers: resend updates token,
   failure handling logs status.

**Progress (2025-09-13)**
- Added unit coverage for render failures, tokenized link generation (with explicit `APP_BASE_URL`), async send behaviour for acceptance/denial handlers, and ensured admin notifications without tokens fall back to default URLs.
- All new tests pass (`UV_PROJECT_ENVIRONMENT=system uv run --extra test pytest --no-cov tests/unit/test_beta_access.py`).


### 5. Beta Access Service & API

Complement existing unit tests:

1. `test_review_beta_access_with_token_sets_actor_from_user_email` — ensure audit
   log actor is derived when `actor_user_id` absent.
2. `test_request_beta_access_duplicate_returns_message` — already partially
   covered but add `accepted` path.
3. `test_review_beta_access_request_denied_updates_user_and_sends_email` — patch
   notification service.
4. API: `test_review_beta_access_token_invalid_payload` (missing token).
5. API: `test_request_beta_access_requires_auth` (missing headers -> 401).

### 6. Memory Optimisation API (`core/api/memory_optimization.py`)

Tests for pruning/compression endpoints: success + error states.

1. `test_generate_pruning_suggestions_success` — stub service to return fixed
   suggestions; assert 200 and response structure.
2. `test_generate_pruning_suggestions_requires_write_scope` — non-writer -> 403.
3. `test_apply_pruning_suggestions_forbidden` — ensure permission check.
4. `test_compress_memory_block_invalid_id` — 404 path.
5. `test_compress_memory_block_success` — patch compression service.

### 7. Organization Repository (`core/db/repositories/organizations.py`)

Unit tests (SQLAlchemy session fixture) to cover complex logic:

1. `test_create_invitation_prevents_duplicate_pending` — call twice, expect
   second raises.
2. `test_create_invitation_allows_after_status_change` — pending -> revoked ->
   new invite allowed.
3. `test_update_invitation_refreshes_token_on_resend` — verify token rotation.
4. `test_get_invitation_with_status_all` — ensure filtering works as expected.

### 8. Auth Dependencies (`core/api/deps.py`)

Add tests for scope calculation and PAT enforcement:

1. `test_get_scope_context_pat_restricted_org` — PAT with org -> forced org scope.
2. `test_get_scope_context_pat_allows_personal` — PAT without org + no hints ->
   default personal.
3. `test_get_scope_context_headers_override` — `X-Active-Scope=organization`
   and `X-Organization-Id` -> ScopeContext reflects hint.
4. `test_get_current_user_context_or_pat_invalid_token` — invalid PAT raises.
5. `test_get_scoped_user_and_context_token_org_mismatch` — query `organization_id`
   conflicting with PAT -> 403.

### 9. MCP Server (`mcp-servers/hindsight-mcp`)

Add a minimal test harness using `jest` (already available) for the client:

1. Mock axios, instantiate `MemoryServiceClient` with scope/organization, verify
   headers and payload transformation (`metadata_col`, keywords CSV).
2. Test `reportMemoryFeedback` maps values and returns response.

For end-to-end tool tests, plan separate tasks after client-level coverage.

## Implementation Order (recommended)

1. Bulk operations API + async service (highest uncovered lines, high risk).
2. Notification service + beta-access flow.
3. Memory optimisation API.
4. Auth/Scope helpers.
5. MCP client tests.

After each batch, run targeted pytest suites (`pytest tests/unit/test_bulk_ops.py
...`) before full `run_tests.sh` to monitor coverage gains. Update this plan with
actual coverage numbers after each milestone.

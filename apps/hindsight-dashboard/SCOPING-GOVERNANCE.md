# Scope Governance Plan (Personal / Organization / Public)

Status: Phase 1 & 2 largely complete; Phase 3 in progress
Owner: Engineering
Last Updated: 2025-09-15

## Goals

- Ensure reads and writes honor the active scope (personal, organization, public).
- Prevent cross‑scope and cross‑environment data leakage by design.
- Centralize scope handling in a single HTTP layer; remove ad‑hoc code.
- Server is authoritative: client is advisory; server enforces scope and membership.

## Principles

- Single source of truth for active scope and org ID (one context, one storage scheme).
- One HTTP client (`apiFetch`) injects scope metadata on every request (all verbs).
- Prefer request headers for scope; include query/body where needed for legacy endpoints.
- No direct `fetch` in components/services. All network I/O flows through the scoped HTTP client.
- Backend validates scope and membership and sets scope server‑side on writes.

## Frontend Plan

1) Consolidate scope context
- Keep a single context (recommend: `OrgContext`).
- Persist to `sessionStorage` keys: `ACTIVE_SCOPE` and `ACTIVE_ORG_ID`.
- Remove duplication with `OrganizationContext` or make one a thin wrapper.

2) Centralize scope injection (HTTP client)
- Implemented: `src/api/http.ts` `apiFetch` attaches scope for ALL methods:
  - Headers: `X-Active-Scope`, `X-Organization-Id` (when scope is `organization`).
  - Query: `scope`, `organization_id` to support legacy endpoints.
  - Add optional `scopeOverride` in `ApiFetchInit` to snapshot scope for long‑running UI flows.
- Keep `credentials: 'include'`.
- Absolute API base URLs are respected for both authenticated and guest mode; relative base uses `/api` or `/guest-api`.

3) Remove bypasses and direct fetches
- Replace any `fetch()` calls with `apiFetch`.
- Remove custom base URL handling in services (prefer `apiFetch`).
- Optional: Add ESLint rule to disallow `fetch` usage outside `src/api/http.ts`.

4) UX guarantees for create flows
- Show current scope pill in create modals.
- Snapshot scope when opening a modal; if user switches scope before submit, warn or refresh the modal to the new scope.

5) Auditing & telemetry (dev‑time)
- In development, log a warning if a modifying request (POST/PUT/DELETE) goes out without scope headers.
- Add ESLint rule to disallow `fetch` usage outside `src/api/http.ts` (todo).

## Backend Plan

1) Middleware enforcement
- Read `X-Active-Scope` and `X-Organization-Id`.
- For modifications, reject if scope missing/invalid (400) or user not a member (403).
- For reads, default to personal for authenticated users and public for guests when unspecified.

### Backend Middleware Spec (current)
- Headers:
  - `X-Active-Scope`: one of `personal`, `organization`, `public`.
  - `X-Organization-Id`: required when scope is `organization`.
- Write requests (POST/PUT/PATCH/DELETE):
  - If `X-Active-Scope` missing → 400 `scope_required`.
  - If `X-Active-Scope=organization` but `X-Organization-Id` missing → 400 `organization_id_required`.
  - Resolve authenticated user from session/cookie/token; verify membership in org (or superadmin).
    - If not a member → 403 `not_an_org_member`.
  - Attach resolved scope to request context for handlers: `{ scope, organization_id, user_id }`.
- Read requests (GET/HEAD):
  - If `X-Active-Scope` missing, treat as personal by default for authenticated users and public for guests (unless endpoint opt-in requires explicit scope).
  - Attach scope context similarly.
- Handler guidelines:
  - On create/update: ignore client body fields for `organization_id`/`visibility_scope` and use context values.
  - On queries: always filter by context scope (`WHERE organization_id = :orgId` for org, or `owner_user_id = :userId` for personal). Public scope only for explicitly public resources.
- Response hardening:
  - Never include data from other scopes; always enforce `LIMIT` and `ORDER BY` to avoid accidental scans.
  - Log anomalies: requests with query/body scope but missing headers.

2) Server‑side scope setting
- On create/update: set `organization_id`/`visibility_scope` from validated request context; ignore conflicting client body values.
- On reads: always filter queries by scope.

3) Compatibility window
- Accept both header and query scope during transition; prefer headers; log when only query/body is used.

## Data Model & DB Safeguards

- Ensure scoped tables have `organization_id`, `visibility_scope`, and `owner_user_id` (for personal).
- Row‑Level Security (RLS) policies defined; enabled conditionally via session GUC `hindsight.enable_rls` and related `user_id`/`org_id` (feature‑flagged per env).
- Indexes per org for performance and isolation.
- Backfill migration implemented; Postgres‑compatible UUID aggregation.
- Scope constraints added as NOT VALID to avoid upgrade failures; can be VALIDATEd after data cleanup.
- Alembic heads merged; revision IDs normalized to fit `alembic_version` limits.

## Validation & Tests

Frontend
- Unit: `apiFetch` injects headers/params for all verbs, honors `scopeOverride`, guest behavior.
- Integration: service calls for agents, keywords, memory blocks respect scope.
- E2E: Create/update/delete in personal vs. org; verify isolation and route refresh behavior.

Backend
- Middleware unit tests: missing headers → 400; invalid membership → 403; role checks.
- Integration: CRUD across scopes; cross‑scope attempts blocked.

## Operational Safeguards

- Nginx: SPA routes served by `index.html`; API under `/api` and `/guest-api`; Docker DNS resolver added to avoid stale upstream resolution.
- Environment isolation: distinct base URLs by env; strict CORS/CSRF policies; optional `X-Environment` header.
- Local dev auth: `DEV_MODE=true` and `ALLOW_LOCAL_DEV_AUTH=true` allow seamless dev bootstrap; guest mode is read‑only.

## Rollout Strategy

Phase 1 – Frontend centralization (this PR)
- Update `apiFetch` to inject scope for all methods (headers + query). (DONE)
- Audit services; eliminate direct `fetch`; update create flows (keywords, memory blocks, etc.). (DONE)
- Quick unit checks/build. (DONE)

Phase 2 – Backend enforcement (follow‑up)
- Add middleware; set scope server‑side; reject missing/invalid scope on write. (DONE)
- Compatibility logging for query/body scoping. (IN PROGRESS)

Phase 3 – DB hardening
- Migrations for constraints/RLS after backfill. (IN PROGRESS)

Phase 4 – Tests + monitoring
- Add tests and monitor logs for anomalies. (IN PROGRESS)

## Immediate Fix Targets

- Ensure `memoryService.createKeyword/updateKeyword/deleteKeyword` use scoped `apiFetch` (covered by Phase 1 change). (DONE)
- Add `memoryService.createMemoryBlock` and switch `AddMemoryBlockModal` to use it (no direct `fetch`). (DONE)
- Verify `agentService.createAgent` includes scope (already updated). (DONE)

## Next Steps

- Backend: ensure remaining endpoints (users, invitations, support) consistently apply `get_scope_context`; add explicit 400s for invalid/missing read scope where endpoints require it.
- RLS: wire optional `HINDSIGHT_ENABLE_RLS=true` in non‑prod to exercise policies; prepare a follow‑up to VALIDATE constraints and enable RLS by default post‑cleanup.
- Data: use `scripts/scope_audit.py` in staging; add targeted cleanup/backfill where audits fail; then VALIDATE constraints.
- Frontend: add ESLint rule to block direct `fetch`; extend tests for guest flows and scope pill UX; re‑verify all services use `apiFetch`.
- Ops: add backend healthcheck/readiness gating for dashboard proxy to avoid startup 502s; add “latest backup” default/non‑interactive mode to `restore_db.sh`.
- Monitoring: server logs for missing scope headers/body hints; dashboard telemetry for scope switches.

---

## Progress Log

- [x] Init: Plan drafted and checked in
- [x] Phase 1: `apiFetch` injects scope on all methods
- [x] Phase 1: Services audited; removed direct fetch in AddMemoryBlockModal
- [x] Phase 1: Keyword & memory block create flows scoped
- [x] Build (vite) passes locally
- [x] Phase 1: Migrated ProfilePage save to apiFetch
- [x] Phase 1: Snapshot + scope pill in AddAgent, AddKeyword, AddMemoryBlock modals; use scopeOverride on create
- [x] Phase 1: Audit — remaining direct fetch only for auth bootstrap (intentional)
- [x] Phase 2: Backend — scope headers supported (get_scope_context reads X-Active-Scope/X-Organization-Id)
- [x] Phase 2: Backend — write endpoints (agents, keywords, memory blocks) now derive scope from context and ignore conflicting body hints
- [x] Phase 1: Added Switch Scope control to create modals (agents, keywords, memory blocks)
- [x] Phase 1: Added unit tests for HTTP scoping injection
- [x] Phase 1: Added component test for modal scope override
- [x] Phase 2: Backend — middleware requires explicit scope on writes (400 on missing scope/org id) for scoped resources
- [x] Phase 2: Consolidation apply preserves scope (block + keywords)
- [x] Phase 2: Repository SQL scoping for consolidation suggestions
- [x] Phase 2: PAT tests for consolidation (list restricted, validate requires write)
- [x] Phase 3: DB hardening — NOT NULL visibility_scope and partial org indexes
- [x] Phase 2: Added DB scope audit tool (scripts/scope_audit.py)
- [ ] Phase 2+: Server‑side enforcement proposal prepared
- [x] Backend: Alembic heads merged; revision IDs normalized; PG13 policy syntax compatibility
- [x] Backend: Backfill UUID aggregation fixed (array_agg) for Postgres
- [x] Backend: Scope constraints added as NOT VALID to avoid upgrade failures
- [x] Dashboard: Nginx Docker DNS resolver; `/guest-api` proxy finalized
- [x] Client: `apiFetch` respects absolute API base in guest mode
- [x] Infra: `restore_db.sh` runs Alembic outside entrypoint to avoid dev‑reset during restore

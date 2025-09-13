# Data Governance Plan — Scope-First Access Control

Last Updated: 2025-09-14

## Purpose
Guarantee that every read/write in the platform is governed by a single, explicit scope (personal, organization, or public), enforced automatically across backend and frontend. The design should be robust-by-default so new endpoints and views inherit correct behavior without relying on humans to remember filters.

## Principles
- Single Source of Truth: Scope is derived once per request and propagated to all data access.
- Default-Deny for Broad Access: Access to resources is limited to the derived scope unless explicitly and safely broadened.
- Token-Enforced: PATs define max capability and (optionally) organization restriction; server-side always honors PAT constraints.
- Layered Enforcement: App-layer + optional DB Row-Level Security (RLS) for defense-in-depth.
- Observability: Scope context recorded in logs/audits for verification and incident response.
- Developer Ergonomics: Helpers and lint rules make “the right thing” the easy thing.

## Scope Model
- personal: resources owned by a user (owner_user_id set).
- organization: resources belonging to an organization (organization_id set).
- public: resources accessible without membership; writes limited to superadmins.

Tokens (PAT):
- Scopes: read, write (write implies read for server checks).
- Optional organization_id: hard restriction; any mismatch → 403.

## Backend Design

### 1) Scope Context Dependency (FastAPI)
- Add `get_scope_context()` dependency that returns a canonical `ScopeContext`:
  - If PAT present: derive from PAT (org restriction enforced); else fall back to query params (`scope`, `organization_id`) validated against current user membership/superadmin.
  - If unspecified: default to personal.
- ScopeContext (example):
  ```python
  @dataclass
  class ScopeContext:
      scope: Literal['personal','organization','public']
      organization_id: Optional[uuid.UUID]
  ```

### 2) Repository Contract — Always Require Scope
- Every repository read/list/search method signature becomes:
  ```python
  def get_X(db: Session, *, current_user: dict|None, scope_ctx: ScopeContext, ...)
  ```
- Internally call existing helpers:
  - `apply_scope_filter(query, current_user, Model)`
  - `apply_optional_scope_narrowing(query, scope_ctx.scope, scope_ctx.organization_id, Model)`
- Endpoint code no longer passes raw `scope`/`organization_id`; it injects `scope_ctx` and `current_user`.

### 3) Endpoint Helper/Decorator
- Optional lightweight decorator `@scoped_endpoint` to attach both `current_user` (PAT-aware) and `scope_ctx` and pass into handlers. Reduces boilerplate and makes scope mandatory by design.

### 4) PAT Enforcement (already present)
- `get_current_user_context_or_pat` validates PAT; `ensure_pat_allows_read/write` enforce scopes and org.
- Continue to use these for write endpoints; add read enforcement via `ensure_pat_allows_read` when a resource org is known.

### 5) Optional DB RLS (Defense-in-Depth)
- Introduce Postgres Row-Level Security policies for core tables (memory_blocks, agents, keywords):
  - Enforce visibility_scope and organization_id membership at the DB-level.
  - Map app user → DB role/session variables (e.g., `set local app.user_id`, `app.org_ids`).
- Benefit: even if an app layer filter is missed, DB denies cross-scope rows.
- Rollout: staged, with feature flag per environment.

### 6) Auditing & Logging
- Add scope fields to key audit events (e.g., `scope_ctx.scope`, `scope_ctx.organization_id`).
- Optionally log anonymized aggregate of scoped reads for observability.

## Frontend Design

### 1) Unified Scope Injection in API Client
- Centralize scoping in `apiFetch` (or a request interceptor):
  - For GET/HEAD, always append `scope` and `organization_id` from `sessionStorage` (`ACTIVE_SCOPE`, `ACTIVE_ORG_ID`).
  - For POST creates, provide a helper that defaults body to org scope when in org mode unless explicitly overridden in UI.
  - Allow opt-out (rare) via an explicit `noScope` option for system endpoints.

### 2) Single Scope Context in UI
- Keep `OrganizationContext` as the authoritative source for active scope; persists to session/local storage and dispatches a global `orgScopeChanged` event.
- Views should never read storage directly; they listen to `orgScopeChanged` or consume context.

### 3) Linting Guardrails
- ESLint rule to disallow raw `fetch` in `src/` with a whitelist; require `apiFetch` so scope injection always occurs.

### 4) Developer UX
- Visual scope indicator (we added: Personal/Org/Public with colors) and quick actions (Copy Org ID) help reduce operator error.
- Add a small debug card (optional) showing active scope and org ID (reads from context) for clarity.

## Testing & CI

### 1) Integration Tests (Server)
- Seed personal/org/public data and test these endpoints under different `scope_ctx`:
  - Memory Blocks: list/get/search
  - Agents: list/get/search
  - Keywords: list
  - Consolidation suggestions: list
  - Optimization suggestions: list
  - Analytics (e.g., conversations count)
- Validate: with PAT org A, reads never include org B or unrelated personal rows.

### 2) Frontend E2E/Component Tests
- Simulate `orgScopeChanged` and assert panels refetch and show only scoped data.
- Verify `apiFetch` adds scope params by default and that views don’t call raw fetch.

### 3) Static Checks
- ESLint rule prevents raw `fetch`.
- Optional script to grep for `fetch(` in CI and fail on hits outside an allowlist.

## Rollout Plan

### Phase 1 — Backend ScopeContext
- Add `get_scope_context()`; use it in a representative set of endpoints and repositories (memory blocks, agents).
- Verify with integration tests.

### Phase 2 — Frontend API Injection
- Update `apiFetch` to append scope/org automatically.
- Remove per-service ad-hoc scope injection gradually.
- Ensure all panels listen to `orgScopeChanged` (done for MB, Archived, Keywords, Agents, Consolidation, Optimization, Analytics).

### Phase 3 — Repository Sweep
- Migrate remaining repositories and endpoints to require `scope_ctx`.
- Kill direct header/param reads for scope in routes; rely on `scope_ctx`.

### Phase 4 — Lint & CI
- Add ESLint rule and a CI script to guard against raw `fetch`.
- Add coverage tests to ensure scope enforcement across representative endpoints.

### Phase 5 — Optional RLS
- Prototype RLS policies on staging; validate behavior under failure injection.
- Roll out with feature flag to production.

## Current State (today)
- PAT-aware backend auth with read/write enforcement; many endpoints accept PAT; middleware allows PAT writes.
- Frontend maintains global scope in `OrganizationContext`; `orgScopeChanged` listeners wired for Memory Blocks, Archived, Keywords, Agents, Consolidation, Optimization, Analytics; services inject scope/org in query params for these areas.
- MCP server supports PAT, org pinning, and whoami.

## Acceptance Criteria
- No unaudited/raw data access to cross-scope rows under any org/personal/public view.
- All repositories accept and enforce `scope_ctx`.
- All frontend reads include `scope` + `organization_id` by default via API client.
- CI tests pass for scope isolation; lint forbids raw fetch.

## Risks & Mitigations
- Missed endpoints during migration → Decorator/dependency pattern + repo contract reduces per-route burden.
- Perf overhead of extra joins/filters → Indexing and careful query composition; RLS evaluated for performance.
- Developer bypasses client → ESLint/CI guardrails.

## TODO (tracked)
- [ ] Implement `get_scope_context()` and apply to memory blocks + agents repos.
- [ ] Update remaining repos to require `scope_ctx`.
- [ ] Elevate `apiFetch` to inject scope by default for GET; add helper for scoped POST creates.
- [ ] Add ESLint rule and CI grep for raw `fetch`.
- [ ] Add integration tests for scope isolation across representative endpoints.
- [ ] Evaluate and prototype Postgres RLS for memory_blocks/agents/keywords.


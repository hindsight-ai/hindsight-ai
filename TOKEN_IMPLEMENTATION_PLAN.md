# Personal Access Tokens (PAT) — Implementation Plan

Last Updated: 2025-09-13

## Purpose
Enable secure, public API access for MCP and external clients via Personal Access Tokens (PATs), with a first‑class token management experience similar to GitHub/OpenAI.

## Goals & Non‑Goals
- Goals:
  - Create, rotate, revoke, and list tokens per user
  - Enforce scopes (`read`, `write`, optionally `manage`) and optional `organization_id` scoping
  - Token usage for public API (Authorization: Bearer …), integrated into existing auth
  - Visibility: last used time; optional expiry
  - UI for token management under user profile (one-time show of secrets)
  - Complete audit (create/rotate/revoke)
- Non‑Goals:
  - OAuth device flows or 3rd‑party OAuth clients
  - Fine‑grained per‑resource scopes beyond `read/write/manage` in MVP

## Design Overview
- Token string format: `hs_pat_<token_id>_<secret>`
  - `token_id`: short, urlsafe ID (e.g., base62 of a UUID segment)
  - `secret`: high‑entropy urlsafe string (24–32 chars)
- Storage
  - Never store full token or secret
  - Store `token_id` and a hashed secret (Argon2id preferred, PBKDF2‑HMAC‑SHA256 as fallback)
  - Store metadata: name, scopes, optional organization_id, status, timestamps, prefix/last4 for UI
- Auth integration
  - New dependency accepts PAT via `Authorization: Bearer <token>` or `X-API-Key: <token>`
  - Validates status, expiry, hash, and scopes; builds `current_user` context for the token’s user and updates `last_used_at`
  - Existing permission helpers (`can_read/can_write`, org checks) continue to apply
- Scope model
  - `read`: GET endpoints
  - `write`: mutation endpoints (POST/PUT/PATCH/DELETE)
  - `manage`: org‑level actions (optional, can be deferred)
  - Optional organization scoping: token restricted to that org’s resources

## Data Model
Table: `personal_access_tokens`
- id: UUID (PK)
- user_id: UUID (FK users.id ON DELETE CASCADE)
- token_id: String(32) — urlsafe id segment; indexed; unique
- token_hash: Text — hash of secret (includes algorithm prefix/params)
- name: String(100) — user label
- scopes: JSONB (array of strings)
- organization_id: UUID (FK organizations.id) NULLABLE
- status: String(20) — `active`, `revoked`, `expired`
- created_at: timestamptz
- last_used_at: timestamptz NULLABLE
- expires_at: timestamptz NULLABLE
- revoked_at: timestamptz NULLABLE
- prefix: String(10) — for UI identification (first N chars)
- last_four: String(4) — for UI identification (last 4 chars)
Indexes:
- ix_pat_token_id (unique)
- idx_pat_user_created (user_id, created_at)
- idx_pat_status (status)

## Hashing
- Preferred: Argon2id with sensible defaults; store encoded hash string
- Fallback: PBKDF2‑HMAC‑SHA256 with per‑token random salt and 100k+ iterations
- Use constant‑time compare; never log secrets

## API Endpoints (Backend)
Under `/users/me/tokens`:
- `GET /users/me/tokens`
  - List all tokens for current user (id, name, scopes, org, status, created_at, last_used_at, expires_at, prefix/last4)
  - Never returns token secret
- `POST /users/me/tokens`
  - Input: name, scopes (array), organization_id (optional), expires_at (optional)
  - Output: metadata AND full token string (only once). Audit: TOKEN_CREATE
- `DELETE /users/me/tokens/{id}`
  - Revoke (status=revoked, revoked_at). Audit: TOKEN_REVOKE
- `POST /users/me/tokens/{id}/rotate`
  - Rotate secret (invalidate old), returns new token string once. Audit: TOKEN_ROTATE
- `PATCH /users/me/tokens/{id}` (optional)
  - Update name/expires_at (no broadening scopes in MVP)

## Public API via PAT
- Auth header: `Authorization: Bearer <token>` (preferred) or `X-API-Key: <token>`
- Validate:
  - Parse token format, find by token_id, check status/expiry, validate hash
  - Enforce scopes per route (read/write) and optional `organization_id` narrowing
  - Update `last_used_at`
- Errors
  - 401: token missing/invalid
  - 403: insufficient scopes or org mismatch
  - 400: token expired/revoked

## UI (Dashboard)
- Location: Profile → “API Tokens” (new tab/section)
- List tokens: name, prefix…last4, scopes, org, status, created/last used/expires, actions
- Create token form: name, scopes (multi‑select), organization (optional), expiry (optional)
- One‑time reveal: show full token once with copy to clipboard; warn user it won’t be shown again
- Actions: revoke (immediate), rotate (shows new secret once)
- Optional: filter/search; link to audit entries for each token

## Audit
- TOKEN_CREATE, TOKEN_ROTATE, TOKEN_REVOKE with metadata `{scopes, organization_id, name, expires_at}`
- Consider logging sensitive fields only as necessary; never the secret

## Rate Limiting & Safety (Phase 7)
- (Optional) simple sliding window rate limit for PAT‑based calls
- Alerting on repeated invalid token attempts

## Documentation
- README/API docs: how to create and use tokens; MCP setup snippet
- Security notes: one‑time reveal, revocation best practices

## Phased Plan & Status

### Phase 0 — Planning & Design
- Status: Completed
- Actions:
  - Captured goals, data model, API, UI, auth integration, hashing, audit, tests & rollout.

### Phase 1 — DB Schema & Model
- Status: Completed (migration + model present)
- Actions completed:
  - SQLAlchemy model `PersonalAccessToken` implemented in `apps/hindsight-service/core/db/models/tokens.py`.
  - Alembic migration `migrations/versions/7c1a2b3c4d5e_add_personal_access_tokens_table.py` added.
  - Indexes and constraints created in the migration (ix_pat_token_id, idx_pat_user_created, idx_pat_status).
- Next verification tasks:
  - Ensure the migration is applied in target environments (dev/staging) during rollout.
  - Confirm `core.db.models` aggregator imports `PersonalAccessToken` so the model is available via imports used across the codebase.

### Phase 2 — Hashing Utilities
- Status: Partial (utilities implemented; confirm runtime deps)
- What exists today:
  - `apps/hindsight-service/core/utils/token_crypto.py` implements token parsing/generation, `hash_secret`, and `verify_secret` with Argon2id preferred and PBKDF2 as fallback.
- Remaining tasks:
  - Verify Argon2 runtime dependency (`argon2-cffi`) is present in the Python environment and declared in `pyproject.toml`/lockfile; if not, add it.
  - Add unit tests to exercise both Argon2 and PBKDF2 verification paths and a constant-time compare assertion for the verification function.

### Phase 3 — Repositories & CRUD
- Status: Planned
- Actions:
  - Repos + CRUD for PATs (create/list/revoke/rotate/update)
  - Audit logging hooks
- Acceptance:
  - Unit tests for CRUD and audit

### Phase 4 — Auth Integration
- Status: In Progress (core pieces present)
- What exists today:
  - `apps/hindsight-service/core/api/deps.py` contains `get_current_user_context_or_pat` that accepts `Authorization: Bearer <token>` and `X-API-Key`, parses tokens, looks up token by `token_id`, validates status/expiry, verifies secret via `token_crypto.verify_secret`, loads the token's user, and builds a `current_user` context similar to the oauth2-proxy flow.
  - `core/db/repositories/tokens.py` provides `get_by_token_id`, `mark_used_now`, `create_token`, `rotate_token`, `revoke_token`, and list/update helpers.
- Remaining tasks:
  - Audit `get_current_user_context_or_pat` thoroughly and add unit tests covering valid token, invalid secret, revoked, expired, and org mismatch cases.
  - Ensure `mark_used_now` (last_used_at) is invoked for successful PAT authentication (ideally inside the dependency so all routes benefit).
  - Confirm the dependency returns the same shaped `current_user` as the oauth2-proxy flow so permission helpers work unchanged.

### Phase 5 — API Endpoints for Tokens
- Status: Implemented (endpoints present)
- What exists today:
  - `apps/hindsight-service/core/api/users.py` exposes `GET /users/me/tokens`, `POST /users/me/tokens`, `DELETE /users/me/tokens/{id}`, `POST /users/me/tokens/{id}/rotate`, and `PATCH /users/me/tokens/{id}` wired to repository functions and audit logging in most flows.
- Remaining tasks:
  - Add unit and integration tests for these endpoints (create returns one-time token, rotate returns new token once, revoke marks token revoked, patch preserves no scope widening).
  - Validate responses and error codes match the plan (401, 403, 400 where appropriate).

### Phase 6 — UI: Profile → API Tokens
- Status: Planned
- Actions:
  - Token list, create, revoke, rotate; one‑time reveal flow; copy to clipboard
- Acceptance:
  - Jest/react‑testing‑library tests for render and actions

### Phase 7 — Hardening & Rate Limit
- Status: Planned (not implemented)
- Recommended next steps:
  - Implement optional per-token rate limiting or platform-side limits (e.g., Redis sliding window, Traefik rate-limits) and alerts for repeated invalid token attempts.
  - Audit logging to ensure token secrets are never written; audit entries should include metadata only (no secret).
## Interim findings and immediate actions

- Summary of what is present (confirmed by a code scan):
  - Model + migration: `core/db/models/tokens.py`, migration exists.
  - Crypto: `core/utils/token_crypto.py` implements parse/generate/hash/verify with Argon2 preferred and PBKDF2 fallback.
  - Repositories: `core/db/repositories/tokens.py` CRUD implemented.
  - API endpoints: `core/api/users.py` includes management endpoints.
  - Auth dependency: `core/api/deps.py` includes `get_current_user_context_or_pat` (PAT-aware dependency).
  - Frontend: token UI in the dashboard exists (`apps/hindsight-dashboard/src/components/ProfilePage.tsx` and `src/api/tokenService.ts`).

- Shortcomings discovered (these must be addressed to make the API public via PATs):
  1. Middleware that enforces read-only for unauthenticated mutating requests may block requests authenticated only by PAT headers; middleware must detect PAT header presence and allow those requests through to route deps.
 2. Many API routes still use the oauth-only `get_current_user_context` dependency; they must be switched to `get_current_user_context_or_pat` or otherwise accept PATs where appropriate.
 3. Global enforcement of scopes (read/write) across endpoints needs audit and explicit checks added where missing (helpers exist, but not necessarily used at every route).
 4. Argon2 runtime package presence needs verification and tests for both hashing modes must be added.
 5. Tests (unit + integration) for token flows are missing or incomplete: hashing, repo CRUD, dependency verification, route-level integration.

## Updated short-term roadmap (next milestones)

1. Verify Argon2 availability and add token_crypto unit tests (fast, low-risk). (Phase 2)
2. Update ASGI middleware to allow PAT-authenticated mutating requests (important blocker). (Phase 4/5)
3. Replace or augment route dependencies so PAT is accepted across intended endpoints; add scope checks. (Phase 4/5)
4. Add tests covering dependency behavior and a representative set of endpoints (read/write + org scoping). (Phase 8)
5. Update docs and CI to validate migrations and run token tests in pipeline. (Phase 9/11)

If you want, I will start with step 1 (verify Argon2 presence and add token_crypto tests) and then proceed to the middleware fix. Indicate "go" to begin and I'll implement the first change and run the tests locally.

### Phase 8 — Docs & Rollout
- Status: Planned
- Actions:
  - README/API docs; MCP instructions; feature flag env; release notes
- Acceptance:
  - Docs published; feature enabled in dev; validated in staging

## Testing Plan
- Unit: hashing, CRUD, token string parsing, error codes
- Integration: PAT auth on key endpoints, scope enforcement, org restrictions, rotate/revoke behavior
- UI: token lifecycle flows, one‑time reveal, error handling

## Risks & Mitigations
- Token leakage: one‑time reveal; no logging; prefix/last4 only
- Scope inflation: restrict PATCH; validate scopes
- Orphan tokens: show last used; encourage cleanup


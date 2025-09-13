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
- Status: In Progress
- Actions:
  - Add SQLAlchemy model `PersonalAccessToken`
  - Add Alembic migration for `personal_access_tokens`
- Acceptance:
  - Migrations apply; model imported in `core.db.models`

### Phase 2 — Hashing Utilities
- Status: Planned
- Actions:
  - Implement Argon2id hashing/verification; fallback to PBKDF2; constants
- Acceptance:
  - Unit tests cover hash/verify + constant‑time compare

### Phase 3 — Repositories & CRUD
- Status: Planned
- Actions:
  - Repos + CRUD for PATs (create/list/revoke/rotate/update)
  - Audit logging hooks
- Acceptance:
  - Unit tests for CRUD and audit

### Phase 4 — Auth Integration
- Status: Planned
- Actions:
  - Add `get_current_user_context_or_pat` dependency
  - Enforce scopes/organization gating; update route dependencies where appropriate
- Acceptance:
  - Integration tests: valid PAT can read/write as per scopes, org scoping enforced

### Phase 5 — API Endpoints for Tokens
- Status: Planned
- Actions:
  - `/users/me/tokens` endpoints per above
- Acceptance:
  - Postman/curl tests; unit/integration tests

### Phase 6 — UI: Profile → API Tokens
- Status: Planned
- Actions:
  - Token list, create, revoke, rotate; one‑time reveal flow; copy to clipboard
- Acceptance:
  - Jest/react‑testing‑library tests for render and actions

### Phase 7 — Hardening & Rate Limit
- Status: Planned
- Actions:
  - Optional rate limits; error telemetry; secure logging
- Acceptance:
  - No secrets in logs; automated checks pass

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


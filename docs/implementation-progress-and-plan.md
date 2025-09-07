Title: Hindsight-AI Data Governance Implementation — Progress, Context, and Next Steps
Status: In progress
Last updated: 2025-09-07

Purpose
- This document lets you (or a future maintainer) resume work without prior context. It explains what was done, where, why, and what to do next. It points to the exact files to open and what to verify.

Working guidelines (read this first)
- Update this document regularly as you progress. Treat it as the single source of truth to resume work if context is lost.
- Implement in small, reviewable changes with tests. After each change, re-run the isolated migrations E2E and the service tests.
- Keep behavior aligned with docs/data-governance-orgs-users.md (design source of truth). If you diverge, update both docs.
- When adding permissions or filters, ensure both CRUD and Search paths enforce the same scope rules.
- Prefer forward-compatible migrations; ensure downgrades don’t break on indexes or operator classes (see notes below).

High-level Goal
- Introduce user- and organization-scoped data governance: fixed roles (owner/admin/editor/viewer), personal vs organization vs public scopes, admin workflows (invitations, empty organization, delete), consent-based personal→org moves, and guest-read-only public data.

Anchor Design Doc (read first)
- docs/data-governance-orgs-users.md
  - Contains the complete solution blueprint: schema design, permissions, endpoints, frontend changes, migrations plan, test stories, and rollout phases.

What’s already implemented (code changes in this branch)
- E2E migration tests (isolated DB)
  - apps/hindsight-service/tests/e2e/test_migrations_stepwise.py
    - Spins up a temporary Postgres container (random high port, e.g., 55432), upgrades forward step-by-step to head, validates core tables, and tears down the container. Never touches the running ‘hindsight_db’.
  - apps/hindsight-service/tests/e2e/test_migrations_downgrade_chain.py
    - Repro for downgrade-chain quirk under Py 3.13 + psycopg2 + Alembic; marked xfail to avoid breaking CI while tracking a stable workaround.
  - apps/hindsight-service/tests/e2e/utils_pg.py
    - Helper to spin up/tear down a disposable Postgres container and wait for readiness.
  - apps/hindsight-service/tests/e2e/run_migrations_e2e_ci.sh
    - CI-friendly runner (uv+pytest if available) to execute the forward stepwise test.
  - apps/hindsight-service/tests/__init__.py and apps/hindsight-service/tests/e2e/__init__.py
    - Make tests a package so relative imports work.

- Alembic testability tweaks
  - apps/hindsight-service/migrations/env.py
    - Reads TEST_DATABASE_URL (preferred for tests) before DATABASE_URL/alembic.ini.
    - Optional ALEMBIC_TEST_USE_CREATOR path (psycopg2 creator()) for environments where libpq/auth behaves oddly. Not required with the isolated DB test path.

- Pytest marker registration
  - apps/hindsight-service/pyproject.toml
    - Added markers = ["e2e: …"] to register the e2e mark and remove warnings.

- Documentation updates
  - docs/data-governance-orgs-users.md updated extensively with:
    - Scoping model and RBAC (fixed roles), guest behavior, public publishing workflow (dual control), empty org mechanisms, audits, invitations, background operations, performance and indexes.
    - User stories & E2E scenarios and a consistency check against the current codebase.
    - Migration testing requirements and “How to run” instructions (self-contained, isolated Postgres tests).

- Data governance — application-level enforcement (Phase 2, partial)
  - Agents
    - Read: GET `/agents` and `/agents/search` apply scope rules (public ∪ personal(owner) ∪ member orgs) with optional `scope` and `organization_id` narrowing.
    - Detail: GET `/agents/{id}` enforces read permissions (404 on not allowed).
    - Create: POST `/agents` enforces org write for org scope and superadmin-only for public.
  - Keywords
    - Read: GET `/keywords` applies scope rules with optional `scope` and `organization_id` narrowing.
    - Detail: GET `/keywords/{id}` enforces read permissions.
    - Create: POST `/keywords` enforces org write for org scope and superadmin-only for public; per-scope uniqueness returns 409 on conflict.
    - Associations: POST `/memory-blocks/{memory_id}/keywords/{keyword_id}` returns 409 on scope mismatch and 403 if caller lacks write on the memory.
  - Memory blocks
    - Read: GET `/memory-blocks` and `/memory-blocks/archived` now accept `scope` and `organization_id` to narrow explicitly; baseline scope rules already applied.
    - Create: POST `/memory-blocks` validates org write and superadmin for public (existing).
  - Identity
    - GET `/user-info`: unauthenticated returns 401 with `{authenticated:false}` to drive dashboard guest mode.

- Tests (E2E)
  - Enhanced: tests/e2e/test_permissions_extended.py (explicit narrowing on memory lists; guest behavior for scope filters)
  - New: tests/e2e/test_permissions_agents_keywords.py (agent/keyword scoping, guest reads, association mismatch 409, write 403)

How to run everything locally
- Start the dev stack (for normal development):
  - ./start_hindsight.sh
  - Backend: http://localhost:8000, Dashboard: http://localhost:3000, DB: localhost:5432 (from docker-compose.dev.yml overrides).
- Run isolated E2E migration tests (no dependency on running services):
  - cd apps/hindsight-service
  - uv run --with pytest pytest -m e2e -k migrations_stepwise
  - This will start/stop its own Postgres container.
- Optional: restore script smoke test (requires at least one backup in ./hindsight_db_backups/data):
  - export RUN_RESTORE_SCRIPT_E2E=1
  - uv run --with pytest pytest -m e2e -k restore_db_script

Environment tips
- Set DEV_MODE=true for local development to auto-provision a dev user in /user-info.
- Set ADMIN_EMAILS to a comma-separated list of emails that should be superadmins (e.g., ADMIN_EMAILS=alice@example.com,bob@example.com).
- In tests, modules are reloaded to ensure the app binds to the test DB (see tests/e2e/test_permissions_*.py).

Known issues (and current stance)
- Alembic downgrade chain under Py 3.13 + psycopg2 occasionally triggers a contextlib generator error even when doing useful work. Forward stepwise is robust; downgrade-chain E2E is tracked in a separate xfail test and will be re-enabled when a stable workaround is found.
  - Files to inspect while working on this: apps/hindsight-service/migrations/env.py, the individual migration files in apps/hindsight-service/migrations/versions/*, and the downgrade-chain test.

Next steps (implementation plan)
Note: implement in small PRs with tests. Use docs/data-governance-orgs-users.md as the source of truth for behavior.

1) Schema migrations (Alembic) — Completed
   - Files to add/update:
     - apps/hindsight-service/migrations/versions/<new_revisions>.py
     - apps/hindsight-service/core/db/models.py
     - apps/hindsight-service/core/db/schemas.py
   - Add tables: users, organizations, organization_memberships.
   - Add scoping columns and indexes: to agents, memory_blocks, keywords (and optionally consolidation_suggestions for consistency).
     - visibility_scope TEXT CHECK IN (‘personal’, ‘organization’, ‘public’)
     - owner_user_id UUID FK -> users(id)
     - organization_id UUID FK -> organizations(id)
     - Indexes: (owner_user_id), (organization_id, visibility_scope)
   - Uniqueness adjustments:
     - Agents: drop global unique(agent_name); add per-scope functional uniques on lower(name):
       - (organization_id, lower(agent_name)) for organization
       - (owner_user_id, lower(agent_name)) for personal
       - lower(agent_name) globally for public
     - Keywords: same per-scope uniqueness on lower(keyword_text).
   - Data migration:
     - Leave existing rows unassigned (personal, owner_user_id NULL) and visible only to superadmin until curated.
   - Validate with isolated E2E.
   - Implemented in: apps/hindsight-service/migrations/versions/3f0b9c7a1c00_add_users_orgs_and_scoped_governance.py
   - Models updated: apps/hindsight-service/core/db/models.py (User, Organization, OrganizationMembership; scoping on Agent/MemoryBlock/Keyword)
   - Schemas updated: apps/hindsight-service/core/db/schemas.py (optional scoping fields)
   - E2E: Stepwise forward/backward validation passing (see tests update below)

2) Backend identity and permissions — In progress
   - Files to add:
     - apps/hindsight-service/core/api/auth.py — Added
     - apps/hindsight-service/core/api/permissions.py — Added
     - apps/hindsight-service/core/api/orgs.py — Added (create/list/get/update/delete orgs; members CRUD)
  - Files to update:
     - apps/hindsight-service/core/api/main.py — Updated /user-info to return user_id, is_superadmin, memberships; included orgs router; applied scope filters to list/detail and validated create permissions for agents/memory-blocks; added scope-move endpoints for agents and memory blocks; enforced permissions on update/delete/archive/associations/keywords
     - apps/hindsight-service/core/db/crud.py — Applied scope filters for reads; added scoping to create paths; scoped keyword creation; per-scope agent lookup
     - apps/hindsight-service/core/search/* — Applied scope filters in fulltext/semantic/hybrid via current_user context
   - Behavior to implement:
     - Fixed roles: owner/admin/editor/viewer; owner/admin can move data into org; personal→org moves require personal owner consent; superadmin override allowed.
     - Public scope is read-only except for superadmin; org owners may request enabling public sharing; superadmin approves the toggle; each publish requires superadmin approval.

3) Org admin workflows
   - Invitations by email (pending memberships):
     - DB: organization_invitations
     - API: create/list/resend/revoke/accept
     - On first login for invited email, bind to users.id (case-insensitive email matching).
   - Audits (read-only transparency):
     - DB: audit_logs
     - API: list + filters; log sensitive actions (publish, owner promotion/acceptance, consent approvals/overrides, bulk ops, delete)
   - Background operations (bulk):
     - DB: bulk_operations
     - API: inventory (counts), bulk-move and bulk-delete (dry_run and execute), operation status
     - Implement in-process worker (threadpool/async) for now; future: queue system.
   - Empty organization wizard (frontend) aligning with backend bulk ops.

4) Frontend changes
   - Files to update/add (apps/hindsight-dashboard):
     - src/api/authService.js (consume expanded /api/user-info)
     - Add orgsService for org/membership/invitations/audits/bulk ops
     - Org switcher in UI; member management pages; “Empty organization” wizard
     - Scope selectors on create (Personal, Org, Public for superadmin)
     - Permission-gated actions; publish request flows with strong confirmation UX

5) Search and analytics updates
   - Ensure all SearchService paths apply scope filters (public ∪ personal ∪ member orgs; guest only public).
   - Update analytics endpoints to count only accessible scopes (and exclude archived unless requested).

6) (Deferred) RLS defense-in-depth
   - Add later: GUC + RLS policies for agents/memory_blocks/keywords, including public-read policy. Stage on pre-prod first.

Validation and testing checklist
- Isolated E2E migrations (forward stepwise) must pass.
  - Enhanced to validate backward stepwise and head re-upgrade.
- Unit tests for permissions logic (can_read/can_write/etc.).
- Endpoint integration tests covering list/detail/search filters and permission errors (401/403/409 semantics).
  - Added E2E endpoint tests:
    - apps/hindsight-service/tests/e2e/test_permissions_basic.py (org + member creation, scoped memory creation, guest read behavior)
    - apps/hindsight-service/tests/e2e/test_permissions_extended.py (read filters, consent on personal→org moves, org admin write, keyword rescope via change-scope)
- E2E flows for invites, owner promotions (acceptance), consent-based personal→org moves, publish requests and approvals, empty organization bulk ops, org delete (post-empty) with retention window.
- Performance: validate indexes on (organization_id, visibility_scope) and lower(name/text) uniqueness keep queries fast.

CI integration
- Use apps/hindsight-service/tests/e2e/run_migrations_e2e_ci.sh in your CI workflow to run the isolated forward stepwise migrations test.
- Optionally add a separate job for the downgrade-chain xfail repro to signal when the upstream/platform issue is resolved.
 - Added job: Migrations E2E (isolated Postgres) — runs tests/e2e/run_migrations_e2e_ci.sh on every PR.

Resuming after a long pause — files to read first
1) docs/data-governance-orgs-users.md (design decisions, full plan, stories/tests, rollout)
2) docs/implementation-progress-and-plan.md (this file)
3) apps/hindsight-service/migrations/env.py and migrations/versions/* (current schema + test overrides)
4) apps/hindsight-service/core/db/models.py and schemas.py (data model expectations)
5) apps/hindsight-service/core/db/crud.py and core/api/main.py (current API behavior and where to inject filters/permissions)
6) apps/hindsight-service/tests/e2e/* (how E2E migration tests are structured)

Sanity checklist to resume
- Ensure Docker is available locally for isolated Postgres in E2E.
- Run: cd apps/hindsight-service && uv run --with pytest pytest -m e2e -k migrations_stepwise
- Run all tests: cd apps/hindsight-service && uv run --with pytest pytest -q
- Verify /user-info returns memberships and is_superadmin. If using headers, set x-auth-request-email and optionally ADMIN_EMAILS.

Open items being tracked
- Enable a robust downgrade-chain E2E (once the contextlib/psycopg2 issue is tamed) and wire it into CI.
- Implement full governance features per the design doc (phases above).
- Add CI job(s) to run the isolated E2E migration script on every PR.
- Enforce permissions for all write endpoints (update/delete/associations) and add scope-move endpoints.
- Add endpoint tests for orgs, memberships, and scope filters; add unit tests for permissions helpers.
- Wire CI to run migrations E2E (added) and consider a matrix job to run API E2E tests.

Next small items (queued; do not execute until approved)
- Unit tests: cover permissions helpers (can_read, can_write, can_manage_org, can_move_scope) across edge cases (public, missing org, viewer overrides, superadmin override).
- CI: optionally add a matrix job to run the API E2E tests (pytest) alongside migrations E2E.

Coverage roadmap (target: 100%)
- After completing the “Next small items”, expand unit tests to cover:
  - CRUD scoping (get_all_memory_blocks) positive/negative filters.
  - Search service scope filters for fulltext/hybrid.
  - Scope-move endpoints (agents/memory) including uniqueness conflicts and consent 409s.
  - Organization endpoints (members CRUD) permission boundaries.
- Track coverage locally with: uv run --with pytest --with pytest-cov pytest --cov=core --cov-report=term
- Only start this effort after explicit approval.

Important: keep this document current
- Every time you implement a feature or test, update:
  - “What’s already implemented” with file paths and purpose
  - “Validation and testing checklist” with how to verify
  - “Open items” and “Next small items” with what remains and what’s queued
  - “Recent changes” with a dated, concise log

Recent changes (chronological)
- 2025-09-07: Added users/orgs/memberships schema + scoped columns and per-scope uniques; updated models/schemas; added auth + permissions scaffolding; implemented organizations and memberships endpoints; expanded /user-info; strengthened E2E test to stepwise downgrade/upgrade; fixed search_vector downgrade in migration 251ad5240261.
 - 2025-09-07: Enforced scoped reads for agents/keywords; added create permission checks (org/public); added explicit `scope`/`organization_id` narrowing on `/agents`, `/agents/search`, `/keywords`, `/memory-blocks`, and `/memory-blocks/archived`; `/user-info` unauthenticated -> 401; added E2E tests covering guest mode, narrowing, and association scope mismatch.

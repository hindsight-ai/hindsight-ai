Title: Hindsight AI data governance: users, organizations, and permissions
Status: Draft for review
Last updated: 2025-09-07

Summary
- Current system exposes all data to everyone who can reach the API. There is no user or organization concept in the database, and read endpoints do not filter by identity.
- Backend already implements GET /user-info and the dashboard calls it to determine auth status; oauth2-proxy forwards auth headers to the backend via Nginx.
- Goal: add user-, organization-, and public-scoped access control so members of an organization can see that org’s data, users can create private data, and admins can manage orgs and set member permissions. Support moving data between private and org scopes and between individuals (admin-controlled). Guests can read only public demo data.

Current state (what’s implemented today)
- DB (PostgreSQL via Alembic in apps/hindsight-service):
  - Tables: agents, agent_transcripts, memory_blocks (+ keywords and associations), feedback_logs, consolidation_suggestions.
  - No users or organizations tables. No owner_user_id/organization_id on resources.
  - No row-level security (RLS) policies. Access is not restricted by user.
  - Alembic present with multiple revisions; schema managed in apps/hindsight-service/migrations.
- Backend (FastAPI in apps/hindsight-service):
  - Middleware blocks write methods (POST/PUT/PATCH/DELETE) for unauthenticated requests by checking presence of auth-related headers (X-Auth-Request-User/Email). GET endpoints do not filter by identity; all data returned.
  - GET /user-info exists and is used by the dashboard for auth state; the response can be extended to include organizations and roles.
  - CRUD and search functions ignore user identity; memory and agent data is effectively global.
- Dashboard (apps/hindsight-dashboard):
  - Calls GET /api/user-info (authService.getCurrentUser). If non-200, treats as unauthenticated. UI supports a “guest mode” that routes to /guest-api (Nginx removes auth headers).
  - No organization selection or member management UI.
- Infra (docker-compose + oauth2-proxy + Nginx):
  - oauth2-proxy forwards identity headers; Nginx proxies /api/* to backend and forwards X-Auth headers.

Requirements distilled
- Users can create data “personally” (not attributed to any organization).
- Organizations can be created/edited/deleted. Members of an organization can view that org’s data. Admin can set member permissions (e.g., read-only vs edit).
- Only an admin can change data visibility to an organization (i.e., moving data into or out of an org scope is admin-controlled).
- Support moving data from personal to organization, and between individuals (admin-controlled).
- The backend should identify the current authenticated user. The dashboard’s /api/user-info path should return identity and memberships.

Proposed data model
- New tables
  - users
    - id UUID PK
    - email TEXT UNIQUE NOT NULL
    - display_name TEXT NULL
    - is_superadmin BOOLEAN NOT NULL DEFAULT FALSE
    - auth_provider TEXT NULL (e.g., google)
    - external_subject TEXT NULL (provider-specific subject/ID)
    - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    - updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    - indexes: (email)
  - organizations
    - id UUID PK
    - name TEXT UNIQUE NOT NULL
    - slug TEXT UNIQUE NULL (optional, for URLs)
    - is_active BOOLEAN NOT NULL DEFAULT TRUE
    - created_by UUID FK -> users(id) NULL
    - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    - updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
  - organization_memberships
    - organization_id UUID FK -> organizations(id) ON DELETE CASCADE
    - user_id UUID FK -> users(id) ON DELETE CASCADE
    - role TEXT NOT NULL CHECK (role IN ('owner','admin','editor','viewer'))
    - can_read BOOLEAN NOT NULL DEFAULT TRUE       (optional override)
    - can_write BOOLEAN NOT NULL DEFAULT FALSE     (optional override)
    - created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    - PRIMARY KEY (organization_id, user_id)
    - index on (user_id)

- Scope and ownership on resources
  - Add to agents and memory_blocks:
    - visibility_scope TEXT NOT NULL DEFAULT 'personal' CHECK (visibility_scope IN ('personal','organization','public'))
    - owner_user_id UUID NULL FK -> users(id)
    - organization_id UUID NULL FK -> organizations(id)
    - indexes: (owner_user_id), (organization_id, visibility_scope)
  - Keywords and associations become scoped (sensitive data):
    - keywords: add visibility_scope ('personal'|'organization'|'public'), owner_user_id, organization_id; unique constraint on (organization_id, lower(keyword_text)) for organization scope; for personal scope, consider unique on (owner_user_id, lower(keyword_text)); for public scope, global unique on lower(keyword_text).
    - memory_block_keywords: continue as (memory_id, keyword_id) but enforce same-scope linkage in application (optionally add a trigger to verify memory_block.organization_id matches keyword.organization_id and visibility_scope compatibility).
  - Agents uniqueness scoped: replace global unique(agent_name) with per-scope uniqueness
    - For organization scope: unique (organization_id, lower(agent_name))
    - For personal scope: unique (owner_user_id, lower(agent_name))
    - For public scope: unique lower(agent_name) globally
  - Consolidation suggestions: add visibility_scope, organization_id, owner_user_id for consistent filtering, or derive via referenced memory blocks; add index on (organization_id, visibility_scope).
  - Derive scope for dependent tables via their parent:
    - agent_transcripts: scope via agent
    - feedback_logs: scope via memory_block

- Ownership rules
  - personal: organization_id NULL, owner_user_id = creator; only owner can read/write unless explicitly reassigned by superadmin.
  - organization: organization_id set; visibility_scope = 'organization'; members with read permission can read; members with write permission (or roles owner/admin/editor) can create/edit.
  - public: visibility_scope = 'public'; readable by everyone including guests; write operations restricted to superadmin (or a designated maintainer service account) to protect demo data.
  - Movement of scope: only superadmin or org owner/admin may move data into/out of an organization; moving between individuals is superadmin-only. Moving to public is superadmin-only.

- Organization ownership and safety
  - Allow multiple owners for redundancy.
  - Invariant: an organization must always have at least one owner. Block role changes/removals that would leave zero owners. Enforce at application level (and optionally via a deferred constraint/trigger in Postgres).

Authentication and identity
- Keep oauth2-proxy in front; backend reads identity from headers set by the proxy:
  - X-Auth-Request-Email (primary), X-Auth-Request-User as fallback.
- GET /user-info (already implemented):
  - Extend to upsert a users row by email on first sight; mark is_superadmin when email is included in ADMIN_EMAILS env var.
  - Response should include: { authenticated: true, user_id, email, display_name, is_superadmin, organizations: [{ id, name, role, can_read, can_write }...] }.

Authorization (RBAC)
- Roles per organization: owner > admin > editor > viewer.
  - owner: manage org (rename/delete), manage members/roles, full read/write on org data, move data into/out of org.
  - admin: manage members/roles, full read/write on org data, move data into/out of org.
  - editor: read + write org data, cannot manage org/members.
  - viewer: read-only org data.
- Superadmin: full power across all orgs and personal data.
- Personal data: only the owner_user_id can read/write. Moving to another user or org is admin/superadmin only.

Where to enforce
- Application-level filtering in all queries and mutations (SQLAlchemy):
  - Every GET must constrain results to current_user’s accessible scopes: public ∪ personal (owner_user_id = current_user.id) ∪ org (organization_id in memberships with read access). For guests, only public.
  - Every POST/PUT/DELETE must check that current_user has rights to the target scope and object; guests can never write.
- Optional defense-in-depth: enable Postgres RLS for agents, memory_blocks, and keywords using a per-session GUC (see “Optional Postgres RLS” below).

Database migration plan (Alembic)
1) Create new entities
   - New Alembic revision to add: users, organizations, organization_memberships.
   - Backfill step: optionally create a “System” user and/or a “Default Organization” depending on migration strategy (see open questions).
2) Add scope/ownership columns
   - Add visibility_scope, owner_user_id, organization_id to agents, memory_blocks, keywords, consolidation_suggestions; create indexes and scoped uniqueness for keywords and agents; drop global unique(agent_name) and re-create scoped uniques.
   - Set defaults for existing rows: visibility_scope = 'personal', owner_user_id = NULL (or mapped to a chosen user); organization_id = NULL.
3) Foreign keys and cascade
   - FKs to users and organizations; ON DELETE SET NULL for owner_user_id/organization_id on agents, memory_blocks, keywords, consolidation_suggestions.
4) Data migration strategy
   - Do not assign existing data to superadmin. Safest default: leave all existing data as personal with no owner_user_id (unassigned) and visible only to superadmin until claimed/moved by superadmin. Optionally tag a subset as public demo to keep guest experience intact. For agents and keywords, adjust uniqueness to per-scope constraints and allow duplicates across scopes.
5) Future-proofing
   - If needed, add a simple audit table for “scope changes” (who moved what and when) to track visibility changes.

Backend changes (FastAPI service)
- New modules
  - core/api/auth.py: utilities to read identity headers; dependency get_current_user(db) that upserts/loads users and memberships; admin checks.
  - core/api/permissions.py: helper functions like can_read(resource, user), can_write(resource, user), can_manage_org(org, user), can_move_scope(resource, user).
  - core/api/orgs.py: APIRouter for organizations and memberships.
- New endpoints
  - GET /user-info: already exists; extend response to include memberships/roles and is_superadmin; ensure 401 with { authenticated:false } when unauthenticated.
  - Organizations
    - POST /organizations: any authenticated user can create; creator becomes owner.
    - GET /organizations, GET /organizations/{id}
    - PUT /organizations/{id}: update name/slug (owner/admin/superadmin only)
    - DELETE /organizations/{id}: owner or superadmin only
  - Memberships
    - POST /organizations/{id}/members: add user with role; only owner/admin/superadmin
    - PUT /organizations/{id}/members/{user_id}: change role/overrides
    - DELETE /organizations/{id}/members/{user_id}
    - GET /organizations/{id}/members
    - Ownership transfer: owners can promote others to owner; an owner may demote self only if at least one other owner remains.
  - Scope moves
    - POST /agents/{id}/change-scope
    - POST /memory-blocks/{id}/change-scope
      - Request supports: visibility_scope ('personal'|'organization'), organization_id (when 'organization'), new_owner_user_id (for moving between individuals).
      - Only superadmin or org owner/admin of the target org can move to org; moving between individuals or to 'public' is superadmin-only.

- Modify existing endpoints
  - All list/detail/search endpoints must apply scope filters using current_user:
    - Basic path: personal (owner_user_id = current_user.id) OR organization_id IN memberships with read = TRUE.
    - Add optional query params: scope ('personal'|'organization'|all) and organization_id to narrow explicitly.
  - Create endpoints (agents, memory-blocks): accept optional visibility_scope and organization_id; default to personal for the current user. Validate user has write permission to the chosen scope.
  - Update/delete endpoints: ensure user has write permission on the target resource.
  - Search services: pass current_user and incorporate the same filters in fulltext/semantic/hybrid queries.

- Data model updates (SQLAlchemy)
  - Add models: User, Organization, OrganizationMembership.
  - Update Agent, MemoryBlock, and Keyword with owner_user_id, organization_id, visibility_scope + relationships; ensure Keyword uniqueness per scope.
  - Update MemoryBlockKeyword logic/validation to link only to compatible-scope keywords.
  - Update Pydantic schemas to include these fields.

- Identity integration
  - Use X-Auth-Request-Email (and X-Auth-Request-User) from oauth2-proxy.
  - For local/dev, support an override env var to treat a fixed email as authenticated.
  - Superadmin assignment via ADMIN_EMAILS env var.

- Guest mode behavior
  - Keep middleware: unauthenticated requests remain read-only for writes.
  - For reads, guests can access only 'public' scope data. Provide seed “public demo” data to ensure a functional guest experience.

Frontend/dashboard changes
- Authentication
  - Keep using GET /api/user-info. Update UI to consume expanded response: user_id, is_superadmin, organizations[] (id, name, role, can_*).
- Organization UI
  - Add an organization switcher (e.g., in header sidebar) to filter views by active context: Personal vs Organization X.
  - New admin pages:
    - Organization list and detail
    - Member management (add/remove users, set role)
    - Organization settings (rename/delete) visible to owner/admin/superadmin
- Resource creation/edit
  - On create Agent/Memory Block/Keyword: allow user to choose scope (Personal, Organization, or Public for superadmin only). Preselect based on the organization switcher.
  - Hide/disable buttons based on permissions (e.g., viewers don’t see edit/delete actions).
- Bulk operations
  - Add “Move to…” actions in list/detail pages to change scope (only for admins). Show confirmation explaining the implications.
  - Introduce an "Empty organization" wizard for owners/superadmin: choose per-resource handling (move to destination org/personal, or delete), preview impact, then run as a background operation with progress.
- API client
  - Update memoryService and related API calls to send/receive scope fields and organization_id; ensure keyword APIs adopt scoping fields.
  - Add orgsService for org and membership endpoints.

Optional Postgres RLS (defense-in-depth)
- Approach
  - Create custom GUC e.g., hindsight.current_user_id.
  - On each DB connection, set it: SET LOCAL hindsight.current_user_id = '<uuid>'
  - Enable RLS on agents, memory_blocks, and keywords; add policies matching the application rules, including a public-read policy for visibility_scope = 'public'.
- Notes
  - Postponed per decision. When revisited: application-level checks remain the primary enforcement. RLS hardens the DB if a stray query forgets to filter, and requires adding on_connect events to set the GUC per request/transaction.

Best practices
- Minimize overbroad access: default to personal scope; explicit choice for org sharing.
- Prefer role-based permissions with simple overrides (can_read/can_write) over per-resource ACLs.
- Ensure all queries go through centralized helper functions that apply scope filters to avoid drift.
- Log permission denials with user_id and resource identifiers for auditability.
- Add comprehensive tests: unit tests for permissions, integration tests for list/detail/search filters, and admin flows.

Migration and Database Testing Requirements
- E2E requirement: Every change that affects migrations/database must be validated by a dedicated end‑to‑end test that exercises backup/restore and migration flows using the helper script at `./infra/scripts/restore_db.sh`.
  - The test must prove that:
    - A clean database can be migrated step‑by‑step from base to head (forward pass), applying each revision in order without errors.
    - The schema can be downgraded step‑by‑step from head back to base (backward pass) without errors.
    - After downgrade, a final forward upgrade back to head succeeds (idempotency of the chain).
- Execution approach (paired with standard test suite):
    - Prefer to run these E2E migration tests alongside the normal test suite, not as a separate CI job.
    - Locally/CI: Spin up Postgres via docker compose (same files as `restore_db.sh`).
    - From `apps/hindsight-service`, programmatically iterate `alembic upgrade +1` step-by-step to head, then `alembic downgrade -1` step-by-step back to base, then upgrade back to head.
    - A smoke test for `restore_db.sh` can be enabled when a backup artefact is available (non-interactive invocation selects first backup); this remains optional locally and in CI.
- Sanity checks per step (optional but recommended):
  - Verify presence/absence of new columns/tables/indexes.
  - Insert/read a minimal row demonstrating new constraints (e.g., per‑scope uniqueness on agents/keywords).

How to run the E2E migration tests locally
- Easiest path (no manual DB prep):
  - Run from `apps/hindsight-service`:
    - `uv run --with pytest pytest -m e2e -k migrations_stepwise`
  - The test will spin up a temporary Postgres container on an isolated port (e.g., 55432), run stepwise Alembic upgrades on a clean database, validate schema, and then tear down the container.
- Optional (restore script smoke test): ensure at least one backup exists in `./hindsight_db_backups/data` and run:
  - `export RUN_RESTORE_SCRIPT_E2E=1`
  - `uv run --with pytest pytest -m e2e -k restore_db_script`
- Notes:
  - Tests use a dedicated TEST_DATABASE_URL internally and never touch the running `hindsight_db` service.
  - Downgrade chain exhibits a known driver/contextlib quirk on some environments (Py 3.13 + psycopg2). The E2E currently validates forward stepwise migrations; a downgrade chain E2E will be enabled once a stable workaround is in place.

Confirmed decisions
1) Organization creation: any authenticated user can create; creator becomes owner (can transfer ownership later).
2) Organization deletion: allowed to owner or superadmin.
3) Superadmin mapping: use ADMIN_EMAILS env var to grant superadmin.
4) Existing data: do not assign to superadmin; keep unassigned personal by default and let superadmin curate (claim/move or mark some as public demo).
5) Guest access: allow read-only access to 'public' demo data; no modifications allowed.
6) Keywords: scope like other data (personal/organization/public) with per-scope uniqueness.

Additional confirmed policies
- Personal → Organization move: Org owner/admin can initiate, but the personal owner must approve. Superadmin may override with justification; all actions audited.
- Ownership transfer: Requires acceptance by the promoted user within a grace window; superadmin can force-accept. Never allow leaving an org without at least one owner.
- Pending deletion: 14 days default retention (configurable via ORG_DELETION_RETENTION_DAYS). Only empty orgs can enter deletion; restore allowed within window; purge after.
- Public sharing: Org owners may request enabling public sharing; superadmin must approve the toggle. Each publish still requires superadmin approval (dual control). Strong UI guardrails to prevent mistakes.
- Publication metadata: Defer; not included in the initial migrations. Can be added later if/when we expand public publishing audits.
- RLS: Postpone; not part of initial phases. Reconsider in Phase 4+ on staging first.
- Email normalization: Lowercase users.email for uniqueness and ADMIN_EMAILS matching; no provider-specific canonicalization.

Open questions to confirm
- Org owners count: recommend supporting multiple owners and enforcing at least one owner at all times (block last-owner demotion/removal). Confirm this approach.
- Org deletion semantics: prefer requiring organizations to be empty before deletion, or enforce an explicit “data destination” step (e.g., move all data to a chosen owner’s personal scope) during deletion. Which behavior do you prefer?
- Public demo data stewardship: should demo data live under a specific service account user (“System”) for easier provenance, or remain truly ownerless?

Rollout plan
- Phase 0: Add /user-info endpoint (no schema change). Wire dashboard to it and confirm identities flow end-to-end.
- Phase 1: Add users/organizations/memberships tables and scope columns (Alembic). Update models and schemas.
- Phase 2: Implement application-level filtering + permission checks across all existing endpoints. Add org and membership endpoints.
- Phase 3: Update dashboard with org switcher, admin pages, and scope-aware forms. Hide actions by permission.
- Phase 4 (optional): Add DB-level RLS; add on_connect hook to set current_user_id; add policies.
- Phase 5: Data migration for existing rows based on the agreed attribution decision.

Phase 2.1 (Additions): Audits, Invitations, Background Operations
- Audits (read-only transparency)
  - DB: audit_logs(id UUID PK, organization_id UUID NULL, actor_user_id UUID, action_type TEXT, target_type TEXT, target_id UUID NULL, status TEXT, reason TEXT NULL, metadata JSONB NULL, created_at TIMESTAMPTZ DEFAULT now(); indexes on (organization_id, created_at), (actor_user_id, created_at), (action_type)).
  - API: GET /audits (filters: org_id, actor_user_id, action_type, time range, pagination); GET /audits/{id} (detail).
  - Backend: write audit entries for sensitive actions (publish requests/approvals, owner promotions/acceptances, consent approvals/overrides, empty org runs, deletions, role changes).
  - UI: Org-level Audit tab listing recent actions with filters.

- Invitations (pending memberships by email)
  - DB: organization_invitations(id UUID PK, organization_id UUID FK, email TEXT (lowercased), invited_by_user_id UUID, role TEXT CHECK IN ('owner','admin','editor','viewer'), status TEXT CHECK IN ('pending','accepted','revoked','expired'), token TEXT NULL, created_at, expires_at, accepted_at, revoked_at; UNIQUE (organization_id, email) WHERE status='pending').
  - API: POST /organizations/{id}/invitations (create or upsert pending), GET /organizations/{id}/invitations, POST /organizations/{id}/invitations/{inv_id}/resend, DELETE /organizations/{id}/invitations/{inv_id} (revoke), POST /organizations/{id}/invitations/{inv_id}/accept (in-app acceptance).
  - Backend: on first login for invited email, bind membership to users.id and mark invitation accepted. Normalization ensures Foo@Bar equals foo@bar.
  - UI: Invite flow in Members page with resend/revoke; pending entries visible; target user sees notification to accept.

- Background operations (bulk jobs)
  - DB: bulk_operations(id UUID PK, type TEXT, actor_user_id UUID, organization_id UUID NULL, request_payload JSONB, status TEXT CHECK IN ('pending','running','completed','failed','cancelled'), progress INTEGER DEFAULT 0, total INTEGER NULL, started_at, finished_at, error_log JSONB NULL, result_summary JSONB NULL; indexes on (organization_id, created_at), (actor_user_id, created_at)).
  - API: POST inventory/dry-run endpoints already specified; execution endpoints return operation_id; GET /admin/operations/{operation_id} (or /organizations/{id}/operations/{operation_id}) returns state/progress.
  - Backend: simple in-process worker (threadpool/async tasks) to process jobs in batches (idempotent; resume from last completed chunk). Future: pluggable queue (RQ/Celery) behind a feature flag.
  - UI: Operations panel shows progress, errors, and history with links to affected resources.

Organization deletion: industry patterns and recommendation
- What others do
  - GitHub: Organization deletion is owner-only, requires confirmation (type the org name). Repositories typically must be transferred or deleted first; there is no implicit bulk transfer. Two-factor auth may be enforced depending on security settings.
  - GitLab: Group (org) deletion supports “delayed deletion” (retention window, e.g., 7 days) and can be configured. Subgroups and projects have to be handled (deleted/transferred) before deletion or via explicit flows. Restore is possible during the retention window.
  - Atlassian (Jira/Confluence Cloud): Site/org deactivation with a time-bound retention period; administrators can export and then permanently delete. Deletion is multi-step and requires confirmations.

- Recommended for Hindsight-AI
  - Step 1: Archive/Suspend organization (optional but encouraged):
    - Freeze writes; revoke member access except owners and superadmin; search excludes the org by default.
    - Goal: safe staging before destructive operations.
  - Step 2: Deletion prerequisites:
    - V1 (simplest and safest): require the organization to be empty (no agents, memories, keywords, transcripts) before deletion. Provide a bulk-move tool to move data to a destination (another organization or a specific owner’s personal scope). This mirrors GitHub/GitLab safety where resources must be handled deliberately.
    - Superadmin override: allow forced deletion that moves data to a quarantine archive for the retention window.
  - Step 3: Pending deletion window:
    - Mark org as pending_deletion with deleted_at set; retain data for N days (e.g., 14 days). Owners or superadmin can restore within this window.
    - After the window, purge permanently via a background job.
  - UX/safety:
    - Two-step confirmations (type org name), display irreversible consequences, show how many resources remain.
    - If 2FA is present on the account, require re-authentication or 2FA challenge.
    - Full audit log of who initiated, who confirmed, and when.

System/Guest accounts and public data
- Create a System service account (users.is_service_account = true) managed by superadmin. Attribute demo data to this user by default.
- Organization-level setting allow_public_sharing (default false). Only owners can enable/disable.
- Publishing workflow (very restrictive):
  - Only owners/admins can initiate a publish request for specific resources.
  - Require superadmin approval to finalize publishing to 'public' (dual control). Optionally later allow “two distinct owners” approval in lieu of superadmin.
  - On approval, set visibility_scope='public', record published_by_user_id, approved_by_user_id, published_at, published_reason.
  - Provide Unpublish action to revert to previous scope. Keep audit trail.
- UI safeguards:
  - Prominent warnings, re-type prompts (e.g., type PUBLIC), and a dedicated “Publish” dialog separated from normal edit flows.
  - Batch actions disabled for publish; require item-by-item review.
  - Redaction helper: prompt to review/remediate sensitive fields before publishing.

Implementation notes for public scope
- DB: defer publication metadata (published_at/by/approved_by/reason) for a later migration; initial V1 relies on audits and event logs.
- Permissions: guests can read public; writes to public require superadmin; org admins/owners can request publish/unpublish, but finalizing requires superadmin (per policy above).
- Search: include public records for guests; for authenticated users include public ∪ their personal ∪ their orgs.

Mechanisms to empty an organization (safe deletion prep)
- Goals
  - Provide first-class, auditable paths to remove all resources from an org so it can be safely deleted.
  - Avoid accidental data loss; support dry-run previews; provide resumable background jobs for large datasets.

- Inventory and preview
  - GET /organizations/{id}/inventory: counts by resource type (agents, memory_blocks, agent_transcripts, keywords, consolidation_suggestions) and sample IDs/names.
  - POST /organizations/{id}/bulk-move (dry_run=true): simulate moving all or selected resources to a destination (another org or a personal owner); returns a plan including:
    - Affected counts, conflicts (e.g., agent name or keyword collisions in destination), and proposed merges for keywords.
  - POST /organizations/{id}/bulk-delete (dry_run=true): simulate deletions with counts and references that will be removed.

- Execution (background jobs)
  - POST /organizations/{id}/bulk-move (dry_run=false) → returns operation_id
  - POST /organizations/{id}/bulk-delete (dry_run=false) → returns operation_id
  - GET /admin/operations/{operation_id}: progress, current step, errors, final summary.
  - Implementation: chunked processing (e.g., 1k rows per batch) to keep transactions bounded and avoid lock contention. Store job records in bulk_operations table: id, type, actor_user_id, org_id, request_payload JSONB, status, progress, started_at, finished_at, error_log JSONB.

- Move semantics
  - Agents: move with scope change; enforce per-scope unique(agent_name). If dest collision, require rename or auto-suffix per policy; surface conflicts in dry-run.
  - Memory blocks: move to destination scope; maintain FK to agents. If agent is staying in source org, either move that agent too, or reassign memory to an existing agent in destination (explicit mapping provided in request). Default: move agents used by moved memories.
  - Keywords: ensure keywords exist in destination scope by lower(keyword_text). For each association, re-point to destination keyword id; optionally delete source keyword if orphaned.
  - Transcripts and feedback: follow parent (agent or memory) moves automatically.
  - Consolidation suggestions: move or purge depending on whether their referenced memory blocks are moved; default behavior: move with memory, else delete if no longer relevant.

- Delete semantics
  - Respect retention: optionally archive to quarantine space (visibility_scope='organization', status='quarantined') before hard delete after N days.
  - Cascade delete inside the org scope only; do not touch personal/public resources.

- Authorization
  - Only owners and superadmin can run these operations for an org. Force-delete/quarantine requires superadmin.

- UI flows
  - Owners/superadmin access an "Empty organization" wizard:
    - Step 1: Inventory display and destination choice (personal owner or another org).
    - Step 2: Collision preview (agents/keywords), provide rename rules or accept auto-suffix.
    - Step 3: Dry-run summary.
    - Step 4: Execute background job; show progress and history.
  - After successful emptying, the Delete Organization button becomes enabled; deletion still prompts for org-name confirmation and optional 2FA.

- Indexes and performance
  - Add indexes to support fast selection by organization_id and visibility_scope on all scoped tables: agents, memory_blocks, keywords, agent_transcripts, consolidation_suggestions.
  - For memory_block_keywords, keep (memory_id, keyword_id) PK and add index on keyword_id for cleanup tasks.

User Stories & E2E Test Scenarios
- Authentication and identity
  - User story: As an unauthenticated visitor (guest), I can access only public demo data and cannot modify anything.
    - E2E: Call GET /user-info without auth headers → 401 with {authenticated:false}. GET list endpoints return only public records; POST/PUT/DELETE return 401.
  - User story: As an authenticated user, I can retrieve my profile and org memberships.
    - E2E: With X-Auth-Request-Email set, GET /user-info returns {authenticated:true, user_id, email, organizations:[...]}, creating a user row on first access.
  - User story: As a superadmin (email in ADMIN_EMAILS), I can manage anything.
    - E2E: GET /user-info shows is_superadmin:true; superadmin can move/delete regardless of org membership; can publish to public.

- Organization lifecycle
  - User story: As a user, I can create an organization and become its owner.
    - E2E: POST /organizations with name=Acme; response owner includes current user; GET /organizations/{id}/members shows role=owner for current user.
  - User story: As an owner, I can rename my org; as admin/editor/viewer I cannot.
    - E2E: PUT /organizations/{id} as owner → 200; as admin → 200 (if allowed per policy); as editor/viewer → 403.
  - User story: As an owner/superadmin, I can delete my org only when empty.
    - E2E: Attempt DELETE with non-empty → 409 with inventory summary; after emptying via bulk-move/delete, DELETE → 202 (pending deletion). Within retention window, restore possible; after expiration, org is gone.

- Membership and roles
  - User story: As an owner, I can add members with roles (admin/editor/viewer) and multiple owners.
    - E2E: POST /organizations/{id}/members {email, role} → member appears with role.
  - User story: As an owner, I cannot demote/remove the last remaining owner.
    - E2E: With one owner, attempt demote/remove → 409; add second owner then demote first → 200.
  - User story: As an admin, I can manage members (except changing/removing owners unless policy allows); as editor/viewer I cannot.
    - E2E: PUT/DELETE members as admin → 200; as editor/viewer → 403.
  - User story: As a member, my permissions apply immediately to reads/writes.
    - E2E: After role change, subsequent requests reflect new rights (no caching glitches).

- Scoping: create/read/update/delete
  - User story: As a user, I can create agents/memory blocks/keywords in personal scope.
    - E2E: POST create with visibility_scope=personal; owner_user_id set to current user; reads limited to owner (and superadmin).
  - User story: As a member of org with write permission (editor/admin/owner), I can create in that org; viewers cannot.
    - E2E: POST with visibility_scope=organization, organization_id=org → 201 for editor/admin/owner; viewer → 403.
  - User story: Public scope creation is superadmin-only.
    - E2E: POST with visibility_scope=public as superadmin → 201; normal user → 403.
  - User story: Per-scope uniqueness enforced for agents and keywords.
    - E2E: Create agent "Alpha" in personal and again in org → both succeed; duplicate in same scope → 409.
  - User story: Keyword associations must match scope of memory block.
    - E2E: Attempt to link org memory to a personal keyword → 400; correct-scope keyword → 201.

- Read filtering and search
  - User story: As a user, I see my personal data, my orgs’ data (per role), and public data in lists and search.
    - E2E: GET list/search returns union of accessible scopes; switching active org filters to that org (plus public if desired in UI).
  - User story: As a viewer, I cannot edit/delete even if I can see items.
    - E2E: PUT/DELETE by viewer → 403; GET → 200.
  - User story: As a guest, I can search only public data.
    - E2E: GET /memory-blocks?search_query=... returns only public items.

- Scope transitions (move)
  - User story: As an owner/admin of org, I can initiate moving a user’s personal data into my org, requiring their approval.
    - E2E: Admin initiates POST /change-scope-proposal → 202 pending; personal owner receives approval task; approves → 200 and data moves; declines → proposal closed; superadmin override with reason → 200.
  - User story: As superadmin, I can move between individuals or between orgs.
    - E2E: change-scope with new_owner_user_id or new organization_id → 200.
  - User story: Publishing to public requires dual control (owner/admin request + superadmin approval).
    - E2E: Owner requests publish → pending state; superadmin approves → visibility_scope=public; guests can read; non-superadmin cannot edit.
  - User story: Unpublish reverts to prior scope and restores permissions.
    - E2E: Unpublish → visibility_scope restored; access control updated.

- Emptying an organization
  - User story: As an owner, I can preview moving all org data to another destination (org or my personal scope) before deleting the org.
    - E2E: GET inventory → counts; POST bulk-move dry_run → plan with collisions; execute job; monitor progress; verify destination contains moved resources and source is empty.
  - User story: As an owner/superadmin, I can bulk-delete remaining resources (with retention/quarantine) if I choose not to move.
    - E2E: POST bulk-delete dry_run → plan; execute; confirm quarantine; final purge after retention.

- Deletion lifecycle
  - User story: As an owner, I can delete my empty org with strong safeguards.
    - E2E: UI requires typing org name; server records audit; deletion enters pending window; restore works within window; after, 404.

- Safety and audit
  - User story: Sensitive actions require explicit confirmations and are fully audited.
    - E2E: Publish to public prompts re-type “PUBLIC”; audit contains actor, approver (superadmin), timestamps, reason.
  - User story: The system blocks last-owner removal.
    - E2E: Attempt last-owner demotion/removal → 409; add another owner then demote → succeeds.

- Background operations
  - User story: Long-running bulk operations are resumable and observable.
    - E2E: Kill/restart service mid-operation; job state persists; operation resumes or can be retried idempotently.

- Optional RLS defense-in-depth (if enabled)
  - User story: Direct SQL access respecting RLS matches app-level permissions.
    - E2E: With session GUC set to current_user_id, SELECT from tables returns only allowed rows; guests see only public; writes blocked by policies where appropriate.

- Invitations and pending memberships
  - User story: As an owner/admin, I can invite a member by email even if they haven’t logged in before.
    - E2E: POST /organizations/{id}/members {email, role} where email has no user row yet → creates a pending membership keyed by email; when that email logs in later (first-time user), the system binds membership to their user_id.
  - User story: As an owner/admin, I can resend or revoke a pending invite.
    - E2E: POST resend → 200; DELETE pending invite → 200; user logging in after revoke does not gain membership.
  - User story: Email normalization applies to invitations.
    - E2E: Invite Foo@Bar.com then user logs in as foo@bar.com → membership binds successfully.

- Organization settings and slugs
  - User story: As an owner/admin, I can set/change organization slug (unique per system), with safety checks.
    - E2E: PUT /organizations/{id} slug=acme → 200; conflicting slug → 409; slug appears in UI routing where applicable.

- Audits and notifications
  - User story: Sensitive actions (publish request, owner promotion, empty org, delete) are recorded in audit logs.
    - E2E: After each action, GET /audits?org_id=… shows actor, action, target, timestamp, status.
  - User story: Participants receive in-app notifications for approvals (consent to move personal data, owner acceptance, public sharing toggle) with clear CTAs.
    - E2E: After initiation, target sees a notification and approval endpoints function; after completion, both initiator and target see status updates.

- Rate limiting and guest protection
  - User story: As a guest, I cannot overwhelm the service.
    - E2E: Hitting GET endpoints repeatedly as guest respects a rate limit (e.g., 60/min) and returns 429 beyond limits; authenticated users have higher limits; writes require auth and permissions.

- Data export (optional V1.1)
  - User story: As an owner/admin, I can export my organization’s data for compliance/backups.
    - E2E: POST /organizations/{id}/export → generates a downloadable archive or staged export; access controlled to owners/admins; includes agents, memories, keywords, transcripts, and metadata.

Extended Test Matrix and Edge Cases
- Role-permission matrix (CRUD by role)
  - For each resource (organization, member, agent, memory, keyword, transcript, consolidation_suggestion):
    - viewer: Read=Allow (org scope), Write=Deny
    - editor: Read=Allow, Write=Allow (org scope), Manage org/members=Deny
    - admin: Read=Allow, Write=Allow, Manage members=Allow, Delete org=Deny
    - owner: Read/Write=Allow, Manage members/org=Allow, Delete org=Allow (if empty)
    - superadmin: All actions across scopes/orgs=Allow
  - E2E: Assert 403/401/404/409/422 codes are consistent with these permissions for each endpoint.

- Unassigned legacy data visibility
  - E2E: Pre-migration data remains with owner_user_id=NULL. Only superadmin can see/manage these until claimed/moved. Normal users cannot read.

- Default scoping on create
  - E2E: Omitting visibility_scope defaults to personal; owner_user_id set to current user; organization_id NULL. Creating with organization_id without org role → 403.

- Name/keyword collisions during moves
  - Agents: Moving “Alpha” into destination with existing “Alpha” in scope → collision reported in dry-run; rename required or auto-suffix policy applied.
  - Keywords: Merge semantics by lower(keyword_text) within scope; associations re-point; duplicate source keyword removed when orphaned.

- Association scope compatibility
  - Enforce that memory_block and keyword share compatible scopes (same organization_id and visibility_scope except public):
    - E2E: Attempt cross-scope association → 400; after move/merge to compatible scope → 201.

- Search and archived interplay
  - E2E: Fulltext/semantic/hybrid search returns only accessible scopes; include_archived flag restricts to archived within accessible scopes. Pagination totals match filtered set.

- Consolidation suggestions scoping
  - E2E: Suggestions inherit scope of referenced memory blocks or carry their own scope fields; listing respects scope; validate/action endpoints check permissions.

- Background operations resilience
  - E2E: Simulate service restart mid-operation; job resumes or can be retried idempotently using operation_id; no partial duplication or orphaning.

- Org membership edge cases
  - E2E: Owner cannot leave org if they would become the last owner; adding another owner then leaving works.
  - E2E: Admin cannot demote/remove owners unless policy explicitly allows; superadmin can.

- Email normalization and superadmin mapping
  - E2E: User emails treated case-insensitively; ADMIN_EMAILS comparison lowercased; uniqueness constraints on users.email normalized.

- User deactivation/removal
  - E2E: Deactivate a user → their personal data remains but is readable only by superadmin; ownership transfer flow can reassign to another user.

- Public publishing safeguards
  - E2E: Attempt batch publish → blocked; require per-item confirmation; require re-type “PUBLIC”; require dual control with superadmin approval; audit entries created.

- CSRF and CORS
  - E2E: Cross-origin modifying requests blocked per Nginx rules; same-origin flows succeed. GETs unauthenticated return only public data.

- API schema integrity
  - E2E: OpenAPI includes new fields (visibility_scope, organization_id, owner_user_id) and endpoints (orgs/members/bulk operations). Client-generated types align.

- Performance/regression
  - E2E: Large org inventory and moves proceed within acceptable time using batches; indexes on (organization_id, visibility_scope) ensure efficient queries; no N+1 regressions.

Additional Open Questions / Clarifications
The following items are now resolved based on decisions:
- Personal→Organization moves: Owner/admin can initiate; requires personal owner consent; superadmin can override with justification.
- Ownership transfers: Require acceptance by the promoted user; superadmin may force-accept; last-owner invariant enforced.
- Pending deletion window: 14 days default; configurable via ORG_DELETION_RETENTION_DAYS.
- Publication metadata: deferred; not part of initial migrations.
- Org allow_public_sharing: owners request enablement; superadmin approval required; per-item publish still needs superadmin.
- RLS rollout: postponed; not included initially.

Concrete code touchpoints (for future PRs)
- Backend
  - apps/hindsight-service/core/db/models.py: add User, Organization, OrganizationMembership; update Agent, MemoryBlock.
  - apps/hindsight-service/core/db/schemas.py: add Pydantic schemas for the above; extend existing models with scope fields.
  - apps/hindsight-service/core/db/crud.py: apply scope filters in all read queries; enforce permissions in mutations; add org/membership CRUD.
  - apps/hindsight-service/core/api/main.py: add /user-info; include new orgs router; wire get_current_user dependency; pass current_user to search services.
  - New files: core/api/auth.py, core/api/permissions.py, core/api/orgs.py.
  - Alembic: add migrations in apps/hindsight-service/migrations/versions/* for the new tables/columns and indexes.
- Dashboard
  - src/api/authService.js: consume expanded /api/user-info.
  - src/api/*Service.js: add org endpoints; include scope/org_id fields in payloads.
  - src/components: add org switcher, org admin pages, and “Move to…” actions. Gate actions by permissions.
  - src/context/AuthContext.jsx: store memberships from user-info; expose active org selection.
- Infra
  - No mandatory change if backend owns /api/user-info. If you prefer delegating identity to oauth2-proxy’s /oauth2/userinfo, we can add an Nginx route to proxy /api/user-info to /oauth2/userinfo and adapt the dashboard/backend accordingly.

Appendix: example RBAC matrix (organization scope)
- owner: read/write all org data; manage org; move data; manage members; delete org.
- admin: read/write all org data; manage members; move data; rename org.
- editor: read/write org data; no org/member management; cannot move data.
- viewer: read-only org data.

Next steps
- Please confirm the decisions in the “Decisions required” section. Once settled, I can draft the first migration and skeleton endpoints (/user-info, orgs and memberships), followed by the scoped filtering changes.
Optional: Custom Roles (per-organization RBAC)
- Context
  - Current plan uses fixed roles: owner, admin, editor, viewer, with simple can_read/can_write overrides on memberships.
  - If you want org-defined custom roles (e.g., “Analyst” = read + search-only; “Curator” = write keywords only), we can extend to a role-based permission model per organization.

- Data model additions
  - organization_roles
    - id UUID PK, organization_id FK -> organizations(id) ON DELETE CASCADE
    - name TEXT (unique within organization), description TEXT NULL
    - is_system BOOLEAN NOT NULL DEFAULT FALSE (true for built-ins: Owner, Admin, Editor, Viewer)
    - created_by UUID FK -> users(id) NULL, created_at, updated_at
    - UNIQUE (organization_id, lower(name))
  - organization_role_permissions
    - role_id FK -> organization_roles(id) ON DELETE CASCADE
    - permission_key TEXT NOT NULL (from an allowed list)
    - allowed BOOLEAN NOT NULL DEFAULT TRUE
    - PRIMARY KEY (role_id, permission_key)
  - organization_memberships (adjustment)
    - Replace role TEXT with role_id UUID FK -> organization_roles(id)
    - Keep can_read/can_write overrides or fold these into permission keys

- Permission keys (illustrative)
  - org.manage (rename, delete, settings)
  - org.members.manage (invite/remove, set roles)
  - data.read (agents/memories/keywords/transcripts)
  - data.write (create/update/delete)
  - publish.request, publish.approve (request/approve public exposure)
  - bulk.ops (inventory, dry-run, execute bulk move/delete)
  - scope.move (change visibility_scope)
  - Note: Owner role remains a system role with full allow; cannot be edited or deleted.

- Backend impact
  - Models: add OrganizationRole and OrganizationRolePermission; migrate membership.role -> membership.role_id.
  - Permission evaluation: centralize checks (e.g., has_permission(user, org, 'data.write')).
  - Endpoints: CRUD for roles; manage permissions per role; assign role to member.
  - Migrations: seed system roles per org (Owner/Admin/Editor/Viewer) with default permissions; map existing memberships to the appropriate role_id.
  - Auditing: log role changes and permission edits.

- Frontend impact
  - UI: Role management page per org (list roles, create custom, edit permissions); member assignment uses roles instead of fixed options.
  - Safeguards: Prevent editing system roles (except display name descriptions if allowed); clear warnings on permission impacts.

- Effort and rollout
  - Complexity: Moderate–High. Touches DB schema, permission checks, and UI.
  - Recommendation: Keep fixed roles for initial release; introduce custom roles in a later phase behind a feature flag. Estimated 1–2 sprints for full CRUD, migration, and tests after base governance is stable.

- Backward compatibility
  - During migration, keep reading membership.role for a transitional period, populate role_id based on mapping, then remove the legacy field once all services updated.
Consistency Check Against Current Implementation
- Backend endpoints
  - The dashboard calls GET /api/user-info; the backend already implements this endpoint. We will extend its response to include organizations, roles, and is_superadmin, and ensure 401 with {authenticated:false} when unauthenticated.
  - Middleware already blocks writes without auth headers; this aligns with guest read-only.
- Models and CRUD
  - Current models (Agent, MemoryBlock, Keyword, MemoryBlockKeyword, AgentTranscript, FeedbackLog, ConsolidationSuggestion) are global; the plan adds owner_user_id, organization_id, visibility_scope to Agents, MemoryBlocks, Keywords (and optionally ConsolidationSuggestion for consistency). CRUD/search must be updated to enforce scope filters and permission checks.
  - Agent uniqueness: currently global unique(agent_name). We will drop global unique and add per-scope uniqueness (organization_id+lower(name), owner_user_id+lower(name), or global for public). CRUD that searches by agent_name must use scope-aware queries.
  - Keywords: currently global unique(keyword_text). We will scope keywords; CRUD must resolve keywords within the caller’s target scope (not globally) and handle merges on moves.
  - MemoryBlockKeyword: ensure association uses same-scope keyword; enforce in code (and optionally DB triggers). Current CRUD links without scope checks.
  - Search services: must add scope filters to fulltext/semantic/hybrid searches; current services do not consider identity and return all data.
- Dashboard
  - Auth flow GET /api/user-info is present in UI. Add org switcher, member management, publish request, empty org wizard, and per-scope controls. Update API clients to pass visibility_scope and organization_id.
- Infra
  - Nginx proxies /api/* with auth headers and /guest-api/* without; works for public read-only.
- Migrations
  - Alembic is in place. We’ll add new tables (users, organizations, organization_memberships), new columns and indexes, and adjust uniqueness as planned.

Implementation Notes: Case-insensitive uniqueness
- To ensure case-insensitive uniqueness for agent_name and keyword_text per scope without requiring CITEXT, we’ll use functional unique indexes on lower(column). Example: UNIQUE (organization_id, lower(keyword_text)). This avoids introducing extra extensions beyond pg_trgm already used.
Status
- The end-to-end migration tests are now being implemented. The current migrations are expected to pass the forward and backward step-by-step runs when executed against a clean test database using the provided docker-compose Postgres setup.

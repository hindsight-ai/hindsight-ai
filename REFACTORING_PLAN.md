# Refactoring Plan (KISS + YAGNI)

Last Updated: 2025-09-12

## Purpose
Make the codebase simpler to navigate and maintain by:
- Reducing file size and responsibility scope (split big files by domain).
- Removing legacy/duplicate paths and stubs (YAGNI).
- Normalizing patterns (auth, permissions, routing, services).
- Keeping layers minimal and clear (KISS): API → Repositories → (optional) Services → DB.

## Guiding Principles
- KISS: few layers, explicit modules, predictable imports.
- YAGNI: delete unused or legacy modules; add only what’s clearly needed.
- Incremental migration with shims to avoid large-bang changes.

## Target Structure (high-level)
```
core/
  api/                 # FastAPI routers only
    agents.py, keywords.py, memory_blocks.py, organizations.py,
    audits.py, notifications.py, bulk_ops.py, search.py,
    support.py, consolidation.py
  auth/                # Auth utilities
    deps.py, permissions.py, auth.py
  db/
    database.py, scope_utils.py
    models/            # Split by domain
      __init__.py, content.py, governance.py, audit.py, bulk_ops.py, notifications.py, suggestions.py
    repositories/      # Thin query modules per domain
      agents.py, memory_blocks.py, keywords.py, organizations.py, audits.py, bulk_ops.py, notifications.py
  schemas/             # Pydantic split by domain
    __init__.py, agents.py, memory.py, keywords.py, organizations.py, audit.py, bulk_ops.py, notifications.py, search.py
  services/            # Business logic/orchestration that adds value
    notification_service.py, transactional_email_service.py, email_service.py,
    search_service.py, pruning_service.py, compression_service.py, consolidation_service.py
  workers/             # Background/long-running tasks
    consolidation_worker.py, async_bulk_operations.py
app.py                 # App assembly: middleware + router includes
```

## Phased Plan & Status
We will update this file at the start and finish of each phase.

### Phase 0 — Planning & Tracking
- Status: Completed
- Started: 2025-09-12
- Finished: 2025-09-12
- Actions:
  - Authored this plan and defined phases/acceptance criteria.

### Phase 1 — API Cleanup & App Assembly
- Status: Completed
- Started: 2025-09-12
- Finished: 2025-09-12
- Tasks:
  - Create `app.py` to assemble FastAPI, CORS, middleware, router includes.
  - Move `build-info` and `support_contact` from `core/api/main.py` → `core/api/support.py`.
  - Move consolidation trigger/suggestions endpoints from `main.py` → `core/api/consolidation.py`.
  - Normalize prefixes/tags: each router uses `prefix="/resource"` and resource-scoped paths.
  - Replace direct header parsing with `Depends(get_current_user_context)` across routers.
- Acceptance:
  - App boots; existing paths continue to work or are redirected; tests pass.

### Phase 2 — Remove Duplicates/Legacy
- Status: Completed
- Started: 2025-09-12
- Finished: 2025-09-12
- Targets:
  - Remove `core/api/orgs_backup.py`, `core/api/orgs_fixed.py` once parity verified.
  - Remove `core/api/optimization.py` (mock) after merging logic into `memory_optimization.py`.
  - Remove legacy `core/bulk_operations_worker.py` after tests are on `async_bulk_operations.py`.
- Acceptance:
  - No dead imports; tests pass.

Progress:
- 2025-09-12: Removed `core/api/orgs_backup.py`, `core/api/orgs_fixed.py`, and `core/api/optimization.py` (no references in tests). Kept `core/bulk_operations_worker.py` due to active test coverage; will remove in a later phase after tests migrate to async worker.

### Phase 3 — Repositories Split (CRUD → per-domain)
- Status: Completed
- Started: 2025-09-12
- Finished: 2025-09-12
- Tasks:
  - Introduce `core/db/repositories/{agents, memory_blocks, keywords, organizations, audits, bulk_ops, notifications}.py`.
  - Move functions from `core/db/crud.py` gradually; keep `crud.py` as shim importing from repositories.
  - Update imports in API/services module-by-module.
- Acceptance:
  - `crud.py` kept as thin facade; tests pass at each step.

Progress:
- 2025-09-12: Added repositories scaffold delegating to `core.db.crud` for these domains: agents, keywords, memory_blocks, organizations, audits, bulk_ops.
- 2025-09-12: Migrated Agents domain from `crud.py` into `repositories/agents.py` (including transcripts). Updated `crud.py` to delegate to the repository, acting as a facade.
- 2025-09-12: Migrated Keywords domain (including memory-block associations) into `repositories/keywords.py` and updated `crud.py` to delegate.
- 2025-09-12: Migrated Memory Blocks domain into `repositories/memory_blocks.py` (including feedback). Updated `crud.py` to delegate; retained some FeedbackLog helpers in `crud.py` for now.
- 2025-09-12: Migrated Organizations domain into `repositories/organizations.py` (orgs, members, invitations). Updated `crud.py` to delegate.
- 2025-09-12: Migrated Audits and Bulk Operations domains into `repositories/audits.py` and `repositories/bulk_ops.py`. Updated `crud.py` to delegate.
- 2025-09-12: Follow-up cleanup: `crud.create_memory_block` now delegates to `repositories.memory_blocks.create_memory_block` to avoid duplication.

### Phase 4 — Schemas/Models Split by Domain
- Status: Completed
- Started: 2025-09-12
- Finished: 2025-09-12
- Tasks:
  - Split `core/db/models.py` into `core/db/models/*` per domain; add `__init__.py` aggregator to preserve imports.
  - Split `core/db/schemas.py` into `core/db/schemas/*`; add `__init__.py` aggregator.
  - Update imports incrementally.
  - Acceptance:
    - Aggregators allow old imports to keep working; tests pass.

Progress:
- 2025-09-12: Introduced `core/db/models/` package with domain modules: users, organizations, agents, keywords, memory, audit, bulk_ops, notifications; added aggregator re-exporting `Base`, `now_utc`, and all models. Removed legacy `core/db/models.py`.
- 2025-09-12: Introduced `core/db/schemas/` package split by domain with aggregator; removed legacy `core/db/schemas.py`. Existing imports like `from core.db import models, schemas` remain valid. Added forward-ref rebuild for MemoryBlock schemas.
- 2025-09-12: Adjusted CRUD facade to delegate for bulk operations and audits; restored invitation/membership helpers expected by API/tests.
- 2025-09-12: Fixed memory block DELETE route path and a search fallback bug (SQLAlchemy `String` casting) uncovered by integration tests.
- 2025-09-12: Hardened tests DB override to propagate the transactional session across threadpool contexts; corrected one integration test to use the shared transactional fixture to prevent cross-test DB leakage.

Test status:
- Unit + integration (non‑e2e) pass in Dockerized test env using `run_tests.sh`.
- Coverage gate currently below 80% due to new modules; leaving coverage improvements for a follow‑up (adding minimal tests or excluding aggregators from coverage).

### Phase 5 — Services Consolidation (search, consolidation orchestration)
- Status: Not started
- Started: —
- Finished: —
- Tasks:
  - Move `search_service.py` under `core/services/` (if not already).
  - Add repository helpers for search queries; keep SQLite fallback logic in the service.
  - Add `consolidation_service.py` to orchestrate worker + DB writes if needed.
- Acceptance:
  - Search endpoints work; consolidation flows operate via service; tests pass.

### Phase 6 — Workers Isolation
- Status: Not started
- Started: —
- Finished: —
- Tasks:
  - Move/confirm `consolidation_worker.py` under `core/workers/`.
  - Keep `async_bulk_operations.py` in `workers/` and ensure API triggers only orchestrate.
- Acceptance:
  - Background tasks run; API returns 202 for async actions; tests pass.

### Phase 7 — Permissions Normalization
- Status: Not started
- Started: —
- Finished: —
- Tasks:
  - Audit endpoints for duplicated scope checks; rely on `permissions.py` + `scope_utils.py`.
  - Ensure single source of truth for org manage/member checks.
- Acceptance:
  - Permissions behavior unchanged but code paths simplified; tests pass.

### Phase 8 — Clean House (YAGNI)
- Status: Not started
- Started: —
- Finished: —
- Tasks:
  - Remove `core/core/keyword_extraction.py` (disabled) or guard behind feature flag.
  - Remove temporary mocks in favor of real implementations or delete.
- Acceptance:
  - No references to removed code; tests pass.

### Phase 9 — Docs & CI Updates
- Status: Not started
- Started: —
- Finished: —
- Tasks:
  - Update `scripts/generate_architecture_docs.py` paths as needed.
  - Update `README.md` and any developer onboarding notes.
- Acceptance:
  - `docs/architecture.md` reflects new layout; CI green.

## Risks & Mitigations
- Import churn while splitting files → Use aggregator `__init__.py` modules to preserve legacy imports during migration.
- Route path changes → Keep old routes included or provide redirects/aliases until clients updated.
- Test instability with DB shims → Migrate in small PRs; run tests per phase.

## Progress Log
- 2025-09-12: Phase 0 completed — Authored REFACTORING_PLAN.md and phased approach.
- 2025-09-12: Phase 1 started — Added `apps/hindsight-service/app.py` (app assembly re-export), split `build-info` and `support_contact` into `core/api/support.py`, and split consolidation endpoints into `core/api/consolidation.py`. Updated `core/api/main.py` to include the new routers.
  Also began auth dependency cleanup: migrated write endpoints in `core/api/agents.py`, `core/api/keywords.py`, and `core/api/memory_blocks.py` to use `Depends(get_current_user_context)` instead of header parsing (read/list endpoints remain permissive for guests). Normalized router prefixes for `organizations`, `audits`, `bulk-operations`, `notifications`, `agents`, and `memory-blocks` (moved prefixes into routers and simplified includes).
  Moved memory-block keyword association endpoints to `core/api/memory_blocks.py` and set `core/api/keywords.py` router prefix to `/keywords` with paths adjusted accordingly. Updated `core/api/audits.py` to use `Depends(get_current_user_context)`.

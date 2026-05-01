# 06 — Architecture Smells & Refactor Backlog

> A prioritized list of architecture smells, structural drift, and boundary problems found across the Hindsight AI codebase.

This backlog is the synthesis of 7 specialized agent runs: 4 phase-1 fact-gathering agents (dependency-graph-analyzer, module-interface-auditor, api-surface-auditor, state-machine-verifier) and 3 phase-2 critique agents (architecture-smell-scanner, architecture-drift-detector, boundary-critic). Their full reports are in [`findings/`](findings/).

**Drift score (architecture-drift-detector): 47/100, "Stabilize" band.** 0 cycles in either sub-repo, but layer-boundary violations are at the FP002 ceiling — 8 unauthenticated mutating routes plus 4 TS layering violations max out the violation signal.

## How to read this

Each item has:
- **Severity** — Critical / High / Medium / Low.
- **Blast radius** — approximate count of files affected if the smell's contract changes.
- **Effort** — Small (<1d) / Medium (<1w) / Large (>1w).
- **Source** — which agent finding it came from (link to `findings/*.md`).
- **Seam** — the specific abstraction or split that closes it (where applicable).

Items are ordered by **(severity × blast radius) ÷ effort**, with security-relevant smells boosted.

## Recommended sequence

A "do these first" sequence emerged from the boundary-critic and smell-scanner agreeing: each step unlocks or simplifies the next.

```mermaid
flowchart LR
    DC[1. Delete dead code<br/>~2,800 LOC, 12 files] --> Org[2. Consolidate dual<br/>org-context]
    Org --> Ctx[3. Replace current_user<br/>dict with dataclass]
    Ctx --> Auth[4. Auth on 8 mutating<br/>routes + close PAT scope gap]
    Auth --> Main[5. Split core/api/main.py<br/>into resource routers]
    Main --> Crud[6. Finish crud.py →<br/>repositories migration]
    Crud --> Notif[7. Split notification_service.py]
```

Steps 1–4 are <1w each. Steps 5–7 are 1–2w each. Steps 1, 3, and 4 each close a security-relevant gap.

## Critical (security-relevant or load-bearing)

### S-1. Eight mutating backend routes have no auth dependency

**Severity:** Critical | **Blast radius:** 8 routes | **Effort:** Small | **Source:** [api-surface](findings/03-api-surface.md), [drift](findings/06-architecture-drift.md) §B1

`core/api/main.py:458,484,528,642,797,858` and `core/api/consolidation.py:29,325` each accept `request: dict` bodies and have no `Depends(get_current_user_context*)`. They are protected only by the global `enforce_readonly_for_guests` middleware, which checks for header presence but does not validate identity.

**Fix:** Add `Depends(get_current_user_context_or_pat)` and a Pydantic request model to each. Add a pytest fixture that iterates every registered `POST/PUT/PATCH/DELETE` route and asserts at least one auth `Depends(...)` exists. Pre-push hook to run it on every push.

### S-2. Three search endpoints duplicate auth resolution and skip PAT scope narrowing

**Severity:** Critical (security) | **Blast radius:** 3 endpoints | **Effort:** Small | **Source:** [api-surface](findings/03-api-surface.md) §6, [boundary-critique](findings/07-boundary-critique.md) §3.3

`core/api/main.py:1075–1099` (fulltext), `1156–1178` (semantic), `1265–1283` (hybrid) each manually resolve auth in 30+ lines of duplicated code. The manual blocks **do not call `ensure_pat_allows_read`** and **do not apply `apply_optional_scope_narrowing`** — meaning a PAT scoped to org-A can read results owned by org-B via these three endpoints.

**Fix:** Add `get_scoped_user_and_context_optional` to `deps.py` (returns `None` instead of 401 when no auth is present). Replace each inline block with `Depends(get_scoped_user_and_context_optional)`. Then move the endpoints to a proper `core/api/search.py` router. Integration test: PAT scoped to org_a cannot retrieve results owned by org_b via any of the three endpoints.

### S-3. Two backend endpoints called by the dashboard do not exist (404)

**Severity:** Critical (broken features) | **Blast radius:** 2 dashboard features | **Effort:** Medium | **Source:** [api-surface](findings/03-api-surface.md) §3.5,3.6

`memoryService.ts:175` calls `POST /memory-blocks/merge` (no backend route). `memoryService.ts:158` calls `POST /memory-blocks/{id}/suggest-keywords` (no backend route). Both throw "HTTP error 404" silently — the "Merge Memory Blocks" and per-block "Suggest Keywords" UI features are broken.

**Fix:** Either implement both endpoints in the backend (the bulk-keyword endpoint is the nearest existing equivalent), or remove the broken UI surfaces and the dashboard methods. Decide first.

### S-4. Dual organization-context architecture (active write-conflict surface)

**Severity:** Critical | **Blast radius:** 7+ files (all scope-aware UI) | **Effort:** Medium (was Large; smaller after dead-code purge) | **Source:** [structural](../01-structural.md) §"Dual organization-context architecture", [smell-scanner](findings/05-architecture-smells.md) AO-1+SF-1

`App.tsx:342–346` mounts both `<OrgProvider>` (vestigial) and `<OrganizationProvider>` (live). Both manage active scope. They write the same logical keys to **two different browser storages** (`sessionStorage.ACTIVE_SCOPE` vs `localStorage.selectedScope`) and both dispatch `orgScopeChanged`.

**Live consumers of `useOrg()`** (the vestigial path): exactly one — `AddAgentModal.tsx`, mounted from `AgentManagementPage.tsx:291`. The other three (`OrgSwitcher`, `AddKeywordModal`, `AddMemoryBlockModal` via `FloatingActionButton`) are dead code.

**Fix:** Single PR — (a) delete the 4 dead components and `OrgSwitcher.tsx`, `orgsService.ts`, `OrgContext.tsx`; (b) migrate `AddAgentModal.tsx` to `useOrganization()`; (c) remove `<OrgProvider>` from `App.tsx`. Verify only one provider remains. No live behavior change.

### S-5. `core/api/main.py` is a god module (1333 lines, 18 endpoints, embedded helper)

**Severity:** Critical | **Blast radius:** ~25 (routers, deps, schemas, tests) | **Effort:** Large | **Source:** [structural](../01-structural.md), [smell-scanner](findings/05-architecture-smells.md) GM-1, [boundary-critique](findings/07-boundary-critique.md) §1.1

App-factory plumbing + 18 endpoint handlers (8 distinct domains) + a 67-line `extract_keywords_enhanced` text-processing helper at lines 686–752. `main.py:43` even imports the private `_ensure_dev_mode_defaults` from `deps.py` — privacy violation.

**Fix:** Move endpoints to their natural homes:
- `/memory/prune/*`, `/memory-blocks/{id}/compress*` → `core/api/memory_optimization.py` (router exists)
- `/memory-blocks/bulk-*` → `core/api/bulk_operations.py`
- `/memory-blocks/search/{fulltext,semantic,hybrid}` → `core/api/memory_blocks.py` or new `core/api/search.py`
- `/user-info` → `core/api/users.py`
- `extract_keywords_enhanced` → `core/services/keyword_service.py`

Result: `main.py` shrinks to ~150 LOC of pure app assembly. Closes S-2 simultaneously (the search endpoints get proper `Depends(...)` when moved).

### S-6. `core/db/crud.py` is a god module + half-finished repository extraction

**Severity:** Critical | **Blast radius:** 12 importers + nearly all integration tests | **Effort:** Large | **Source:** [structural](../01-structural.md), [smell-scanner](findings/05-architecture-smells.md) GM-2/IA-1/MM-1, [boundary-critique](findings/07-boundary-critique.md) §1.2

943 lines, 75 functions, 8 entity domains. 1-line delegators (`create_agent` line 86) sit next to 60-line business transactions (`apply_consolidation` lines 521–580). `core/db/repositories/` is scaffolded but stalled — for some domains (agents, memory_blocks, keywords) the repos hold real implementations and crud.py delegates; for others (`apply_consolidation`, search, dashboard stats) the logic still lives in crud.py.

**Fix:**
1. Extract `apply_consolidation` to `core/services/consolidation_service.py::apply_consolidation(db, suggestion_id) -> MemoryBlock`. The orchestration of "archive originals + create merged + re-scope keywords" is business logic, not data access.
2. Move the three `search_memory_blocks_*` functions out of `crud.py`; have callers use `search_service` directly. Update `repositories/memory_blocks.py:19` to import from `core.services.search_service` instead of the `core.search` shim (closes S-13).
3. Move remaining domain implementations into per-domain repository files; `crud.py` becomes a thin facade that can be deleted once consumers migrate.
4. **Or roll back the repository scaffolding** — the half-state is the worst option. Pick a direction and commit.

## High

### S-7. `current_user` dict shape leaks across 15 API files (76 reads)

**Severity:** High (security implications) | **Blast radius:** 15 files | **Effort:** Medium | **Source:** [smell-scanner](findings/05-architecture-smells.md) II-1, [boundary-critique](findings/07-boundary-critique.md) §1.4

`core/api/deps.py` returns `Tuple[Any, Dict[str, Any]]`. The dict has seven well-known keys consumed by **76 raw `current_user.get(...)` / `current_user[...]` reads across `core/api/`** (verified count). A typo silently returns `None` and bypasses `is_superadmin` checks. The three search endpoints in `main.py` (S-2) demonstrate the failure mode — they manually rebuild this dict, **omitting two security enforcement steps**.

**Fix:**
```python
@dataclass
class CurrentUserContext:
    id: uuid.UUID
    email: str
    display_name: Optional[str]
    is_superadmin: bool
    memberships: list[OrganizationMembership]
    memberships_by_org: dict[str, OrganizationMembership]
    pat: Optional[PersonalAccessToken] = None
    dev_mode_pat: Optional[str] = None
```
Change `get_current_user_context` and `get_current_user_context_or_pat` to return `Tuple[User, CurrentUserContext]`. Update `ensure_pat_allows_write/read(ctx: CurrentUserContext)`. The change is contained — `deps.py` is the single constructor — but high-leverage.

### S-8. `notification_service.py` is a god module (1277 lines, 30 methods, 8 event flows)

**Severity:** High | **Blast radius:** 10 callers | **Effort:** Large | **Source:** [smell-scanner](findings/05-architecture-smells.md) GM-3 (this was missed by the module-interface-auditor)

Single class handles in-app notifications, user preferences, email-log persistence, async email dispatch, and 7 event-specific flows (org invitation, membership added/removed, role changed, beta-access invitation/confirmation/admin/acceptance/denial). Methods like `notify_membership_added` (lines 863–977) embed nested closures that mix transactional update logic with email transport.

**Fix:** Split into:
- `NotificationDispatcher` — in-app + preference store. ~300 LOC.
- Per-event flow classes (`OrgInvitationFlow`, `MembershipAddedFlow`, `BetaAccessFlow`, …). ~100 LOC each.
- A thin `EmailService` that owns transactional email transport (the existing `transactional_email_service.py` may already be it; consolidate).

### S-9. `notificationService.ts` — 32 dependents on concrete singleton, no interface

**Severity:** High | **Blast radius:** 32 files | **Effort:** Medium | **Source:** [dependency-graph](findings/01-dependency-graph.md), [boundary-critique](findings/07-boundary-critique.md) §2.1

Frontend's highest fan-in (32) and lowest instability (0.00) — maximally stable AND maximally rigid (D-line violation). Three `api/` modules (`agentService`, `memoryService`, `organizationService`) import it directly, inverting the layer order. API modules cannot be reused outside the browser without stubbing the toast bus, and tests of `api/` modules require mocking it.

**Fix:** Define `INotificationService` interface in `src/types/notifications.ts`. API modules throw `ApiError(status, message)` instead of firing toasts. A single React Query `onError` (or context-layer hook) fires the toast. Add an ESLint `no-restricted-imports` rule preventing `src/api/` from importing `services/`.

### S-10. `apply_consolidation` lives in the DB layer (services/db boundary violation)

**Severity:** High | **Blast radius:** 1 (function move + caller update) | **Effort:** Small | **Source:** [boundary-critique](findings/07-boundary-critique.md) §1.2/§5.3

`core/db/crud.py:521–580` orchestrates archive originals + create merged block + re-scope keywords. This is a multi-step business transaction in a CRUD module. The DB layer should not decide business rules.

**Fix:** Move to `core/services/consolidation_service.py::apply_consolidation(db, suggestion_id) -> MemoryBlock`. Close part of S-6.

### S-11. `notifications.py` runtime `metadata` ↔ `metadata_json` patch in 3 handlers

**Severity:** High (silent failure mode) | **Blast radius:** 3 handlers + every future notification handler | **Effort:** Small | **Source:** [api-surface](findings/03-api-surface.md) §3.8, [boundary-critique](findings/07-boundary-critique.md) §3.1

`core/api/notifications.py:48,104` and one more handler do `setattr(n, 'metadata', getattr(n, 'metadata_json', None))` because SQLAlchemy reserves `.metadata` and the column was renamed `metadata_json`. The Pydantic field is `metadata`. Any handler that forgets the patch serializes `metadata` as `null`.

**Fix:** Add a `@property` to the `Notification` SQLAlchemy model:
```python
@property
def metadata(self) -> Optional[dict]:
    return self.metadata_json
```
Or rename the Pydantic field to `metadata_json`. Either eliminates the runtime patch.

### S-12. Bulk operation in-memory state vs DB state can diverge

**Severity:** High | **Blast radius:** 5 files | **Effort:** Medium | **Source:** [state-machines](findings/04-state-machines.md) SM-4, [smell-scanner](findings/05-architecture-smells.md) SF-5

`core/async_bulk_operations.py::_running_tasks` (in-memory) and `bulk_operations.status` (DB) can diverge:
- **Cancel race**: `bulk_operations.py:427` writes `cancelled` if `cancel_task` (in-memory check) succeeds. If the worker has already crossed its terminal `db.commit()`, the DB record is `completed`/`failed` but the API returns success.
- **Worker exception**: `_on_task_complete:329` writes `{status: 'failed'}` to in-memory results on exception, but the DB status update lives inside `_perform_bulk_*`. If an exception escapes those, DB stays `running` while in-memory says `failed`.

**Fix:** After cancellation, re-read the DB row and reconcile. In `_on_task_complete`, if an exception escapes the worker, write `failed` to the DB before returning.

### S-13. `crud.py` and `repositories/memory_blocks.py` import via the `core.search` shim

**Severity:** Medium → High when combined with S-6 | **Blast radius:** 6 import sites | **Effort:** Small | **Source:** [smell-scanner](findings/05-architecture-smells.md) §7

`crud.py:615,738,785,833` and `repositories/memory_blocks.py:19` import `from core.search import get_search_service`. `core/search/__init__.py` is a documented compatibility shim re-exporting from `core.services.search_service`. A DB module thus depends on a service via a migration shim — a two-hop indirection that exists only for migration bookkeeping.

**Fix:** Change the 6 sites to `from core.services.search_service import get_search_service`. Then delete the shim. Closes the AO-5 ambiguous-ownership finding.

### S-14. Three search endpoints in `main.py` envy `deps.py` (manual auth resolution)

**Severity:** High (combines with S-2) | **Blast radius:** 3 endpoints | **Effort:** Small | **Source:** [smell-scanner](findings/05-architecture-smells.md) FE-3

Same root cause as S-2; recorded separately because the structural fix is independent: move the three endpoints to a router file with `Depends(get_scoped_user_and_context)`.

## Medium

### S-15. `core/db/repositories/` Phase 3 extraction is stalled

**Severity:** Medium | **Blast radius:** 8 repository files + 75 crud functions | **Effort:** Large to complete OR Small to roll back | **Source:** [boundary-critique](findings/07-boundary-critique.md) §6.3, [smell-scanner](findings/05-architecture-smells.md) MM-1

`core/db/repositories/__init__.py:4` documents that the repositories "currently delegate to existing functions in `core.db.crud`." Some domains (agents, memory_blocks, keywords) actually have implementations in the repositories with `crud.py` delegating; others (`apply_consolidation`, `search_*`, dashboard stats) still live in `crud.py`. A caller choosing one or the other gets identical behavior — the namespace exists with no isolation.

**Decision required:** Complete the migration (move all logic, deprecate `crud.py`) or roll back the scaffolding. The half-state is indistinguishable from real progress and is not.

### S-16. `HybridRankingConfig` exposes 20 scoring algorithm internals as a public type

**Severity:** Medium | **Blast radius:** every caller that constructs/reads it | **Effort:** Small | **Source:** [boundary-critique](findings/07-boundary-critique.md) §3.2

`core/services/search_service.py:60` declares `HybridRankingConfig` as a public dataclass with 20 fields including `normalization_method`, `reranker_provider`, `scope_personal_bonus`, `recency_half_life_days`. Replacing the scoring algorithm requires touching every caller.

**Fix:** Make `HybridRankingConfig` private. Expose only `SearchOverrides(fulltext_weight, semantic_weight, limit, min_score)` for caller-facing tunables.

### S-17. MCP scope is fixed at construction time

**Severity:** Medium | **Blast radius:** every MCP consumer | **Effort:** Medium | **Source:** [api-surface](findings/03-api-surface.md), [boundary-critique](findings/07-boundary-critique.md) §5.2

`mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts:104–109` sets `X-Active-Scope` and `X-Organization-Id` as static headers at construction time from env vars. Scope cannot change per-request. An LLM agent issuing `create_memory_block` then `advanced_search_memories` with different intended scopes silently uses the first's scope.

**Fix:** Add optional `scope?` and `organizationId?` per-call overrides on each method. Constructor default remains for backward compatibility.

### S-18. `core/api/main.py:43` imports private `_ensure_dev_mode_defaults`

**Severity:** Medium | **Blast radius:** 2 | **Effort:** Small | **Source:** [smell-scanner](findings/05-architecture-smells.md) FE-1, [boundary-critique](findings/07-boundary-critique.md) §4.4

A leading-underscore symbol from `deps.py` is imported by `main.py` — encapsulation broken. **Fix:** make the helper public, or fold the dev-mode branch of `/user-info` into `deps.py` so the helper stays private.

### S-19. `core/db/models/users.py:15` model comment omits the `revoked` beta-access state

**Severity:** Medium | **Blast radius:** documentation | **Effort:** Small | **Source:** [state-machines](findings/04-state-machines.md) SM-2, [drift](findings/06-architecture-drift.md) §A1

Comment lists 4 states; code reaches 5. **Fix:** update the comment AND add a unit test that asserts `allowed_statuses` matches the comment.

### S-20. `consolidation_suggestions.status` has no DB-level CHECK constraint

**Severity:** Medium | **Blast radius:** 1 (table) | **Effort:** Small | **Source:** [state-machines](findings/04-state-machines.md) SM-5, [data](../04-data.md) §"State columns at a glance"

Migration `975d4a80651a` declared the column without a CHECK constraint. Only the SQLAlchemy default and Python guards enforce the value set. **Fix:** new migration to add `CHECK status IN ('pending','validated','rejected')`.

### S-21. `OrganizationContext` mixes scope state with org-management state

**Severity:** Medium | **Blast radius:** 1 (context split) | **Effort:** Small | **Source:** [boundary-critique](findings/07-boundary-critique.md) §1.5

11-item context value mixes scope switching and org-management state. After S-4 (consolidation), extract a dedicated `ScopeContext` with only active scope + org ID + switch functions; leave management state behind.

### S-22. `docs/architecture.md` is auto-generated and stale (14 modules undocumented)

**Severity:** Medium | **Blast radius:** documentation only | **Effort:** Small | **Source:** [drift](findings/06-architecture-drift.md) §A "Critical"

The auto-generator script was not re-run after beta_access, PAT tokens, embedding service, query expansion, feature flags, runtime, and token crypto modules were added. **Fix:** Regenerate, then add a pre-push hook: `python scripts/generate_architecture_docs.py && git diff --exit-code docs/architecture.md` to fail on staleness.

## Low / cleanup

### S-23. Delete `core/api/orgs_fixed.py` (566 lines, dead code)

**Severity:** Low | **Effort:** Trivial | Verified zero importers; never registered. Its docstring even says "prefer `orgs.py`".

### S-24. Delete dead frontend modules (~2,800 LOC, 12 files)

**Severity:** Low (cognitive surface area) | **Effort:** Trivial | **Source:** [dependency-graph](findings/01-dependency-graph.md), [smell-scanner](findings/05-architecture-smells.md) §9

Verified dead: `MemoryBlockList.tsx` (719), `MemoryCompressionModal.tsx` (381), `AddMemoryBlockModal.tsx` (319, only consumer is dead `FloatingActionButton`), `AddKeywordModal.tsx` (143), `FloatingActionButton.tsx` (68), `AddAgentDialog.tsx` (63), `OrgSwitcher.tsx` (60), `MemoryBlockTable_new.tsx`, `MemoryBlockTable_old.tsx`, `QuickCreateTokenModal.tsx`, `utils/devMode.ts`. Add `ts-prune` or `knip` to CI to flag future unused exports.

### S-25. Delete `core/workers/async_bulk_operations.py` shim

**Severity:** Low | **Effort:** Trivial | **Source:** [smell-scanner](findings/05-architecture-smells.md) §7

Zero production importers. The "compat shim" is dead; the root `core/async_bulk_operations.py` is canonical. Delete the shim and drop the misleading docstring on the root file.

### S-26. Migrate `core.core.consolidation_worker` test patches and delete the namespace

**Severity:** Low | **Effort:** Small | **Source:** [smell-scanner](findings/05-architecture-smells.md) §7

7 lines in `tests/integration/memory_blocks/test_consolidation_worker.py` patch `@patch('core.core.consolidation_worker.X')`. Production does not use this namespace. Re-target the patches to `core.workers.consolidation_worker`, then delete `core/core/`.

### S-27. Move `CurrentUserInfo` type from `api/authService.ts` to `types/domain.ts`

**Severity:** Low | **Effort:** Trivial | **Source:** [dependency-graph](findings/01-dependency-graph.md) Class 2 violation

`utils/featureFlags.ts:1` imports it from `api/`, inverting the foundation/transport layer order. Add ESLint `no-restricted-imports` rule on `src/utils/`.

### S-28. `core/services/__init__.py` partial re-exports

**Severity:** Low | **Effort:** Small | **Source:** [module-interfaces](findings/02-module-interfaces.md) §2.2

Re-exports only 2 of 7 services and exports `reset_*_for_tests` helpers in the production package surface. Make it complete (all 7) or empty (force submodule imports). Move test helpers to a `_testing.py` module.

### S-29. ADR 0001 split — `viteEnv.ts` vs `http.ts`

**Severity:** Low | **Effort:** Trivial | **Source:** [drift](findings/06-architecture-drift.md) §"Minor / Cosmetic"

ADR 0001 says "single env accessor that reads runtime first." Today, `src/lib/viteEnv.ts` reads only `import.meta.env`; `src/api/http.ts:41` reads `window.__ENV__`. Consolidate into `viteEnv.ts`.

### S-30. `MemoryBlock` type mismatch (5-field stub vs 19-field backend, MCP missing scored fields)

**Severity:** Low (cosmetic until consumed) | **Effort:** Small | **Source:** [api-surface](findings/03-api-surface.md) §3.1

Dashboard `memoryService.ts:50` declares 5 fields. Backend returns 19. MCP client `MemoryBlock` types `id` as optional. **Fix:** Generate types from the OpenAPI spec, or hand-mirror the backend `schemas/memory.py` shape on both consumers.

## Prevention measures

Suggested CI / pre-push hooks to keep these problems from recurring:

1. **Auth-on-mutating-routes test** — pytest fixture iterating every registered FastAPI route and asserting `POST/PUT/PATCH/DELETE` has at least one `Depends(...)` arg that calls `get_current_user_context*`. Closes the regression path of S-1.
2. **Architecture-doc regeneration** — pre-push hook: `python scripts/generate_architecture_docs.py && git diff --exit-code docs/architecture.md`. Closes S-22's recurrence.
3. **File-size watcher** — `find apps/hindsight-service/core/{api,services,db} -name '*.py' | xargs wc -l | awk '$1 > 800 {exit 1}'`. Catches new god modules.
4. **ESLint layering rules** — `no-restricted-imports` in `src/api/` (no `services/`), `src/utils/` (no `api/`). Catches the recurrence of S-9 and S-27.
5. **`ts-prune` or `knip`** in CI — flags new unused exports (S-24 prevention).
6. **State-column CHECK constraints** — every status column in a new migration must have a CHECK or be discussed in the PR (S-20 prevention).

## Findings index

Raw agent reports preserved verbatim:

- [`findings/01-dependency-graph.md`](findings/01-dependency-graph.md) — TS dependency graph (95 files, 262 edges, 0 cycles).
- [`findings/02-module-interfaces.md`](findings/02-module-interfaces.md) — frontend + backend module API quality.
- [`findings/03-api-surface.md`](findings/03-api-surface.md) — 82 HTTP routes + 11 MCP tools, contract drift.
- [`findings/04-state-machines.md`](findings/04-state-machines.md) — 9 state machines, doc-vs-code drift.
- [`findings/05-architecture-smells.md`](findings/05-architecture-smells.md) — 24 smells across 7 categories.
- [`findings/06-architecture-drift.md`](findings/06-architecture-drift.md) — drift score 47/100 with rationale.
- [`findings/07-boundary-critique.md`](findings/07-boundary-critique.md) — top 5 boundary problems with proposed seams.

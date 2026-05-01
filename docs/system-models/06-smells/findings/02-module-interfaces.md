# Module Interface Audit — Hindsight AI Monorepo

**Audited**: 2026-04-29
**Scope**: `apps/hindsight-dashboard/src/` (frontend) + `apps/hindsight-service/core/` (backend)

---

## Part 1: Frontend — `apps/hindsight-dashboard/src/`

### 1.1 Module Catalog

| Module Group | Files | Purpose | Approx. Public Exports |
|---|---|---|---|
| `src/api` | 10 files | HTTP client layer: per-resource CRUD wrappers over `apiFetch` | ~80 (functions + types) |
| `src/context` | 5 files | React Context providers for auth, org scope, notifications, page header | ~15 (hooks + providers) |
| `src/services` | 1 file | In-process singleton notification bus (toast queue) | ~12 (methods on class) |
| `src/hooks` | 3 files | Reusable React hooks (modal state, page header, token creation) | 3 |
| `src/utils` | 3 files | Feature flags, dev-mode auth shim, UUID generator | ~12 (functions + types) |
| `src/types` | 1 file | Shared domain types for UI layer | 8 types |
| `src/lib` | 1 file | Vite environment variable reader | 0 (internal only) |
| `src/components` | ~75 files | Page components, modals, UI widgets | 1 per file (default exports) |

---

### 1.2 Public API Quality — Top 8 Frontend Modules

#### `src/api/memoryService.ts`
- **Cohesion**: Poor. Handles memory blocks, keywords, consolidation suggestions, pruning, compression, bulk operations, support contact, and build-info in one object. These are 7 distinct backend resource groups.
- **Interface narrowness**: Wide. 30+ named method exports on a single default object, plus duplicate named re-exports on line 187.
- **Abstraction level**: Mixed. `getMemoryBlocks` (list query) sits next to `bulkGenerateKeywordsBatched` (multi-batch orchestration logic with `onProgress` callback) and `contactSupport` (unrelated resource). The batch methods implement retry/progress orchestration that belongs in a higher-level service layer, not a raw API wrapper.
- **Leaky abstractions**: `base()` function (line 26-47) duplicates URL resolution logic already in `http.ts::apiBase()`, including a hardcoded `:3000` dev check. The function also emits `console.log('[DEBUG]...')` on every call. Scope injection (lines 141-142, 166-167) is re-implemented manually instead of delegating to `apiFetch`'s built-in scope injection.
- **Score**: 2/5.

#### `src/api/http.ts`
- **Cohesion**: Reasonable. Three exported helpers (`isGuest`, `apiBasePath`/`apiBase`/`apiUrl`/`apiUrlDir`, `apiFetch`) plus one type. All serve the same concern: building authenticated fetch calls.
- **Interface narrowness**: 6 exports is moderate. `apiBasePath`, `apiBase`, `apiUrl`, `apiUrlDir` are four overlapping URL-builder variants — a consumer must understand the difference to pick the right one.
- **Abstraction level**: Leaks. `ApiFetchInit` exposes `noScope`, `scopeOverride` — internal session-storage plumbing visible in the public type. Consumers must understand scope-injection internals to use `noScope` correctly.
- **Score**: 3/5.

#### `src/api/organizationService.ts`
- **Cohesion**: Good. Covers all CRUD operations for organizations, members, and invitations — one domain.
- **Interface narrowness**: 16+ methods on a default export. Moderate, but all org-related.
- **Leaky abstractions**: None significant. Types are clean. Inconsistency: `addMember` takes inline `{ email, role }` (not `AddMemberData`), while `updateMember` takes `UpdateMemberData`. Both types are exported but not used symmetrically.
- **Score**: 3.5/5.

#### `src/api/orgsService.ts`
- **Cohesion**: Extremely narrow — one method (`listOrganizations`).
- **Duplicate**: Functionally overlaps with `organizationService.getOrganizations()`. Both call `GET /organizations/`. The distinction is: `orgsService` is consumed by `OrgContext` (the lean scope switcher), while `organizationService` is consumed by `OrganizationContext` (the richer management context). Neither module makes this distinction visible in its name or type.
- **Score**: 3/5 in isolation; 1/5 for the system because it creates dual-registration.

#### `src/context/OrgContext.tsx`
- **Cohesion**: Good. Manages active scope selection (personal/org/public) and persists choice to sessionStorage.
- **Interface narrowness**: 6-item context value. Tight.
- **Leaky abstractions**: `useOrg` exposes `activeScope` as a raw string union, requiring consumers to understand `ScopeType` semantics.
- **Duplicate**: Parallel to `OrganizationContext`. Both providers are mounted in `App.tsx` as nested wrappers (lines 355-359), both synchronize to `sessionStorage.ACTIVE_SCOPE/ACTIVE_ORG_ID`, creating the risk of divergent writes.
- **Score**: 3/5 individually; system-level concern is critical.

#### `src/context/OrganizationContext.tsx`
- **Cohesion**: Mixes scope switching (personal/org/public) with full org management state (`currentOrganization`, `currentUserMembership`, `loading`, `error`). That is two concerns.
- **Interface narrowness**: 11-item context value — wide for a context.
- **Leaky abstractions**: `switchToOrganization` internally calls `organizationService.getMembers()` to verify membership, which couples the context to the member-fetching pattern on every scope switch.
- **Duplicate**: Uses `localStorage` for persistence while `OrgContext` uses `sessionStorage` for the same keys (`ACTIVE_SCOPE`, `ACTIVE_ORG_ID`). Both dispatch `window.dispatchEvent(new Event('orgScopeChanged'))`. They can diverge silently.
- **Score**: 2/5.

#### `src/utils/featureFlags.ts`
- **Cohesion**: Good. One concern: reading/merging/deriving feature flags.
- **Interface narrowness**: 7 exports (2 types, 2 constants, 3 functions). Slightly wide but all related.
- **Abstraction level**: Consistent — all at the feature-flag config level.
- **Score**: 4/5.

#### `src/services/notificationService.ts`
- **Cohesion**: Good. Manages a live notification queue with debouncing and listener dispatch.
- **Interface narrowness**: Exposes 12+ public methods. The `showXxxError()` family (5 methods) could be replaced by a single `showError(code, action?)` but this is minor.
- **Naming note**: `addNotification` vs `showSuccess`/`showError` — two vocabularies for the same action.
- **Score**: 4/5.

---

### 1.3 Smells

#### Grab-bag export
- `src/api/memoryService.ts` — 30+ methods spanning 7 backend resource domains plus batched orchestration logic. The double-export pattern on line 187 (default export re-destructured as named exports) means every import sees both the object and its individual methods.

#### Duplicate modules (structural debt)

| Pair | Files | Overlap |
|---|---|---|
| Org context | `context/OrgContext.tsx` + `context/OrganizationContext.tsx` | Both manage personal/org/public scope; both write `sessionStorage.ACTIVE_SCOPE`; both provide `switchToPersonal/Organization/Public` semantics (different names: `setActiveScope` vs `switchToPersonal`). |
| Org API client | `api/orgsService.ts` + `api/organizationService.ts` | Both call `GET /organizations/`. |
| Org switcher component | `components/OrgSwitcher.tsx` (uses `useOrg`) + `components/OrganizationSwitcher.tsx` (uses `useOrganization`) | Two UI components for the same user action, backed by two different context systems. |
| MemoryBlockTable variants | `MemoryBlockTable.tsx`, `MemoryBlockTable_new.tsx`, `MemoryBlockTable_old.tsx` | Three files with near-identical first 5 lines. `_new` and `_old` are not imported anywhere in production code. They are dead files that inflate the component count. |

#### Mixed abstraction levels
- `memoryService.ts` exposes `getMemoryBlocks` (thin fetch wrapper), `bulkGenerateKeywordsBatched` (loop + aggregation logic), and `contactSupport` (support form POST). These belong at different layers.
- `context/OrganizationContext.tsx::switchToOrganization` performs a two-request sequence (get org, get members) for membership verification — business logic in a context layer.

#### Debug leak
- `api/memoryService.ts` line 46: `console.log('[DEBUG] memoryService base URL:...')` in production code path, triggered on every API call.

---

## Part 2: Backend — `apps/hindsight-service/core/`

### 2.1 Module Catalog

| Module Group | Files | Purpose | Approx. Public Exports |
|---|---|---|---|
| `core/api` | 18 files | FastAPI routers (one per resource) + `deps.py` (auth dependencies) + `main.py` (app assembly + overflow endpoints) | ~100 route handlers + ~10 dependency functions |
| `core/db/models` | 11 files | SQLAlchemy ORM models, split by domain | 20 model classes |
| `core/db/schemas` | 11 files | Pydantic request/response schemas | ~65 schema classes |
| `core/db/repositories` | 9 files | Per-domain DB access layer (in-progress extraction from `crud.py`) | — (not yet a stable public API) |
| `core/db/crud.py` | 1 file | Monolithic CRUD facade (975 lines, 75 functions) | 75 functions |
| `core/db/database.py` | 1 file | SQLAlchemy engine/session factory | 2-3 functions |
| `core/services` | 7 files | Embedding, search, notification, email, query expansion, beta access | ~10 via `__init__.py` |
| `core/workers` | 2 files | Async bulk operations + consolidation worker | 7 via shim |
| `core/pruning` | 2 files | LLM-backed pruning and compression services | 2 service factories |
| `core/search` | 2 files | Search compatibility shim (re-exports from `services`) + evaluation helper | 2 via shim |
| `core/utils` | 6 files | Feature flags, role permissions, scopes, token crypto, URL helpers, runtime detection | ~15 |
| `core/core` | 1 file | Internal namespace description only (empty `__init__.py` effectively) | 0 |
| `core/__init__.py` | 1 file | Empty (1 line) | 0 |

---

### 2.2 Public API Quality — Top 10 Backend Modules

#### `core/db/crud.py`
- **Cohesion**: Poor. Single file handles CRUD for agents, transcripts, keywords, memory blocks, feedback, consolidation, organizations, invitations, audit logs, bulk operations, search, and dashboard stats.
- **Interface narrowness**: 75 public functions. Wide grab-bag.
- **Abstraction level**: Mixed. `create_agent` (thin model insert) coexists with `search_memory_blocks_hybrid` (calls `SearchService`, handles query expansion, scoring), `apply_consolidation` (multi-step business transaction with keyword re-scoping), and `_get_or_create_keyword` (private helper exposed with leading underscore but called by `main.py`).
- **Leaky abstractions**: `get_all_memory_blocks` takes 19 parameters including `scope_ctx: ScopeContext` and `filter_organization_id` — SQL-layer filtering details surface at the API caller level.
- **Note**: The repository split is in progress (`core/db/repositories/__init__.py` says "Phase 3 scaffolding") but incomplete; repositories currently delegate back to the same implementations.
- **Score**: 1.5/5.

#### `core/api/main.py`
- **Cohesion**: Very poor. Serves as both the app factory (router wiring, middleware, CORS, exception handlers) and a direct endpoint host for: scope change, user-info, conversations count, pruning suggest/confirm, memory compression, bulk keyword generation/apply, bulk compaction, and three search endpoints. These should be in their respective resource routers.
- **Interface narrowness**: 1353 lines, 18 function/endpoint definitions. The bulk keyword generation endpoint (lines 642-704) even embeds a 130-line `extract_keywords_enhanced()` helper function inline.
- **Abstraction level**: Mixed. App-assembly code (middleware registration, CORS configuration) is interspersed with business-logic endpoint handlers.
- **Score**: 1/5.

#### `core/db/schemas/__init__.py`
- **Cohesion**: Aggregator, not a grab-bag. All schemas are Pydantic types for API I/O. Exposing 65+ names is typical for a schema package and follows the "compatibility aggregator" pattern documented in the file header.
- **Interface narrowness**: Wide by count (65+ names), but all are type definitions, not behavior. Each consumer uses only the schemas relevant to its resource.
- **Leaky abstractions**: Exports `FulltextSearchRequest`, `SemanticSearchRequest`, `HybridSearchRequest` alongside resource schemas — search-engine configuration types surface at the same level as `AgentCreate`.
- **Score**: 3.5/5.

#### `core/db/models/__init__.py`
- **Cohesion**: Good. All ORM model classes. Clean aggregator with explicit `__all__`.
- **Interface narrowness**: 20 model classes. Appropriate.
- **Score**: 4.5/5.

#### `core/api/deps.py`
- **Cohesion**: Moderate. Houses FastAPI dependency functions for auth (OAuth2, PAT, dev-mode), scope context resolution, and PAT permission enforcement. Single concern (request-scoped identity/permissions) but wide.
- **Interface narrowness**: ~10 exported dependency callables. Consumers use mostly `get_current_user_context`, `get_current_user_context_or_pat`, `get_scoped_user_and_context`, and `ensure_pat_allows_write/read`.
- **Leaky abstractions**: Returns raw `Dict[str, Any]` as the user context (not a typed dataclass), so every consumer must know dict key names like `"memberships_by_org"`, `"is_superadmin"`, `"pat"`. This couples 15+ API handlers to the same dict shape.
- **Score**: 3/5.

#### `core/services/__init__.py`
- **Cohesion**: Partial. Only re-exports `EmbeddingService` and `QueryExpansionEngine`. `SearchService`, `NotificationService`, `EmailService` are not included — consumers of those import directly from their submodules.
- **Inconsistency**: Some services (embedding, query expansion) have public factory functions (`get_embedding_service`, `get_query_expansion_engine`) with `reset_*_for_tests` variants also exported. Exposing test reset helpers in the production package is a leaky abstraction.
- **Score**: 3/5.

#### `core/workers/async_bulk_operations.py` (canonical) + `core/async_bulk_operations.py` (shim source)
- **Cohesion**: Good. One concern: async bulk move/delete operations.
- **Interface narrowness**: 7 exports. Reasonable.
- **Leaky abstractions**: `get_async_db_session` (infrastructure detail) and `AsyncBulkOperationsManager` (internal task registry class) are public alongside the high-level `execute_bulk_operation_async`. A consumer shouldn't need to know about the manager.
- **Score**: 3/5.

#### `core/services/search_service.py`
- **Cohesion**: Good. One concern: full-text, semantic, and hybrid memory search.
- **Interface narrowness**: Exports `SearchService` and `get_search_service`. The `HybridRankingConfig` dataclass (20+ fields) leaks scoring algorithm internals into the public type.
- **Abstraction level**: `_env_bool`, `_env_float`, `_env_int` private helpers are defined at module level — fine, but the `HybridRankingConfig` dataclass is public and expects consumers to understand `normalization_method`, `reranker_provider`, `scope_personal_bonus` etc.
- **Score**: 3.5/5.

#### `core/utils/feature_flags.py` and related utils
- **Cohesion**: Good. Each util file has a single concern.
- **Score**: 4/5.

#### `core/pruning/pruning_service.py` + `core/pruning/compression_service.py`
- **Cohesion**: Good. Each service has one domain concern.
- **Interface narrowness**: Each exposes a service class and a factory function. Clean.
- **Score**: 4/5.

---

### 2.3 Smells

#### Grab-bag modules
- `core/db/crud.py` — 75 functions across 8 entity domains plus 3 search strategies plus business transactions (`apply_consolidation`, `search_memory_blocks_hybrid`). The repository extraction (Phase 3) is structurally incomplete.
- `core/api/main.py` — app factory + 8+ endpoint groups + utility functions. The `extract_keywords_enhanced` helper (lines 706-772) is a 70-line pure-text-processing function embedded in the app assembly file.

#### Mixed abstraction levels
- `core/db/crud.py` mixes thin DB helpers (`create_agent` — 1 line) with multi-step business transactions (`apply_consolidation` — 80 lines).
- `core/api/main.py` line 46 imports the private `_ensure_dev_mode_defaults` from `deps.py` directly, breaking the module boundary.

#### Duplicate / shadow API
- `core/api/orgs.py` vs `core/api/orgs_fixed.py`: `orgs_fixed.py` is labelled "prefer `orgs.py` for current endpoints" in its own docstring, but it still defines a full `APIRouter` with endpoints. It is not included in `main.py`'s router registration, making it dead code that could mislead future contributors.

---

## Part 3: Compatibility Shims

| Shim File | What It Hides | Still Load-Bearing? |
|---|---|---|
| `core/search/__init__.py` | Re-exports `SearchService`, `get_search_service` from `core.services.search_service`. Comment: "New code should import from `core.services.search_service`." | Yes. `core/db/crud.py` line 645 imports `from core.search import get_search_service`. Until `crud.py` is migrated, removing this shim breaks the search path. |
| `core/workers/async_bulk_operations.py` | Re-exports 7 symbols from `core.async_bulk_operations` (the root-level canonical file). Comment: "legacy imports from `core.async_bulk_operations` continue to work." | Partially. The shim itself is the new canonical path (`core.workers.*`). The root-level `core/async_bulk_operations.py` is the implementation. If any code imports from `core.async_bulk_operations` directly, the shim is needed; if all imports already use `core.workers.async_bulk_operations`, the root file is the one that is redundant. Requires a `grep` to confirm. |
| `core/core/__init__.py` | Docstring says "Internal namespace for worker exports. Modules under `core.workers.*` are the canonical import path." — but it re-exports nothing. | No. It is documentation-only. Safe to remove or leave. |
| `core/__init__.py` | Empty (1 line). | No. Python package marker only. |

---

## Part 4: Top 5 Modules to Refactor

### 1. `core/db/crud.py` — Priority: Critical
**File**: `apps/hindsight-service/core/db/crud.py`
**Rationale**: 75 public functions, 975 lines, covering 8 entity domains. It is the single heaviest cross-cutting dependency in the backend. The repository extraction at `core/db/repositories/` is already scaffolded but incomplete — completing it and reducing `crud.py` to a thin pass-through (or eliminating it) would be the highest-leverage refactor in the codebase.
**Anchor**: `core/db/crud.py:1` (entire file) — the Phase 3 scaffolding note at `core/db/repositories/__init__.py:1` names the intent.

### 2. `core/api/main.py` — Priority: High
**File**: `apps/hindsight-service/core/api/main.py`
**Rationale**: App factory has accreted 8 endpoint groups and a 130-line inline utility function. The search endpoints (lines 1038-1326) belong in a `core/api/search.py` router. The pruning/compression endpoints (lines 457-638) belong in a `core/api/memory_optimization.py` router (one is partially done — see the `try`/`except ImportError` at line 1343). The bulk keyword endpoints (lines 641-857) belong in `core/api/bulk_operations.py`. Moving them would make `main.py` app-factory-only (~150 lines).
**Anchor**: `core/api/main.py:706` — `extract_keywords_enhanced` is a helper function embedded in the app assembly file with no business being there.

### 3. `src/api/memoryService.ts` — Priority: High
**File**: `apps/hindsight-dashboard/src/api/memoryService.ts`
**Rationale**: 30+ methods spanning memory blocks, keywords, consolidation, pruning, compression, bulk operations, support, and build-info. The `base()` function (lines 26-47) duplicates `http.ts::apiBase()` and emits a debug log on every call. The `bulkGenerateKeywordsBatched` and `bulkApplyKeywordsBatched` methods implement multi-batch orchestration with progress callbacks — that orchestration should live in a higher-level service, not a raw API wrapper.
**Anchor**: `src/api/memoryService.ts:187` — the mass re-export line is symptomatic of the module's width.

### 4. `src/context/OrgContext.tsx` + `src/context/OrganizationContext.tsx` — Priority: High
**Files**: Both context files.
**Rationale**: Two React contexts mounted simultaneously in `App.tsx` both manage scope selection, both synchronize to `sessionStorage.ACTIVE_SCOPE`/`ACTIVE_ORG_ID`, and both dispatch `orgScopeChanged`. `OrgContext` uses `sessionStorage`; `OrganizationContext` uses `localStorage` for the same conceptual state. They drive two different switcher components (`OrgSwitcher.tsx` uses `useOrg`; `OrganizationManagement.tsx` uses `useOrganization`). Consolidating to one context (likely extending `OrgContext` with the management capabilities from `OrganizationContext`) would eliminate the race condition between the two storage systems and the dual-provider wrapping.
**Anchor**: `src/App.tsx:355-359` — double-nested provider registration.

### 5. `core/api/deps.py::get_current_user_context` return type — Priority: Medium
**File**: `apps/hindsight-service/core/api/deps.py`
**Rationale**: Returns `Tuple[Any, Dict[str, Any]]` where the dict has well-known keys (`id`, `email`, `is_superadmin`, `memberships`, `memberships_by_org`, `pat`, `dev_mode_pat`). All 15+ API handlers must know these string key names. Replacing the dict with a typed `CurrentUserContext` dataclass/Pydantic model would close the leaky abstraction and enable static analysis. This is a contained change since `deps.py` is the single constructor of these dicts.
**Anchor**: `core/api/deps.py:190-200` — the dict literal that is duplicated in three code paths (dev mode, PAT, oauth2).

---

## Summary Statistics

**Frontend modules analyzed**: 23 (api: 10, context: 5, services: 1, hooks: 3, utils: 3, types: 1)
**Backend modules analyzed**: 25+ (api: 18, db: 4 packages, services: 7, workers: 2, pruning: 2, search: 2, utils: 6)
**Clean interfaces (score 4+)**: `featureFlags.ts`, `notificationService.ts`, `db/models/__init__.py`, `pruning/*`, `utils/*`
**Critical issues**: 5
**Dead code confirmed**: `MemoryBlockTable_new.tsx`, `MemoryBlockTable_old.tsx` (no consumers), `core/api/orgs_fixed.py` (not registered in main.py), `core/core/__init__.py` (content-free)

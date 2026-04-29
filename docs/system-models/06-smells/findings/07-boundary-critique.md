# Boundary Smells — Hindsight AI Monorepo
<!-- Generated 2026-04-29. Source: MBSE docs (01-structural, 03-interfaces) + raw research (01–04). -->

---

## 1. Responsibility Segregation

### 1.1 `core/api/main.py` — App Factory + Eight Endpoint Groups

**Severity**: Critical | **Effort**: Medium

`apps/hindsight-service/core/api/main.py` is 1353 lines. It owns two completely unrelated concerns:

**Concern A — Application assembly**: CORS configuration (lines 83–97), middleware registration (lines 120–175), exception handlers, router inclusion. This is the app factory. It has a clear owner: the server bootstrap.

**Concern B — Business endpoint hosting**: The file directly implements 14 endpoint handlers, including:
- `POST /memory/prune/suggest` and `/memory/prune/confirm` (lines 458–511) — belong in `memory_optimization.py`
- `POST /memory-blocks/{id}/compress` and `/compress/apply` (lines 528–638) — belong in `memory_optimization.py`
- `POST /memory-blocks/bulk-generate-keywords`, `/bulk-apply-keywords`, `/bulk-compact` (lines 642–904) — belong in `bulk_operations.py`
- `GET /memory-blocks/search/fulltext`, `/semantic`, `/hybrid` (lines 1038–1326) — belong in `memory_blocks.py` or a dedicated `search.py`
- `GET /user-info`, `GET /conversations/count` (lines 296–413) — belong in `users.py` / `agents.py`

**Embedded helper** (evidence): `extract_keywords_enhanced(text: str) -> List[str]` at line 706 — a 130-line pure text-processing function with no dependency on the app factory, embedded in the assembly file.

The import of `_ensure_dev_mode_defaults` from `core.api.deps` at line 45 crosses a module boundary via a private symbol, confirming the factory has leaked into business logic territory.

**Seam to draw**: Reduce `main.py` to an app factory of ~150 lines. Move:
- prune + compress endpoints → `core/api/memory_optimization.py` (router already exists at that prefix)
- bulk-keyword + bulk-compact endpoints → `core/api/bulk_operations.py`
- three typed search endpoints → `core/api/memory_blocks.py` (where the unified `/search/` already lives)
- `user-info` → `core/api/users.py`
- `extract_keywords_enhanced` → `core/services/keyword_service.py` with signature `def extract_keywords(text: str) -> list[str]`

---

### 1.2 `core/db/crud.py` — Eight Entity Domains in One File

**Severity**: Critical | **Effort**: Large

`apps/hindsight-service/core/db/crud.py` is 973 lines with 75 public functions spanning agents, memory blocks, keywords, feedback, consolidation, organizations, invitations, audit logs, bulk operations, and search.

**Mixed abstraction levels** (evidence):
- `create_agent` — effectively a one-line model insert (line ~224)
- `apply_consolidation` at line 528 — 80-line multi-step business transaction that archives originals and creates a merged block; this belongs in a service layer, not a data-access layer
- `search_memory_blocks_hybrid`, `search_memory_blocks_fulltext`, `search_memory_blocks_semantic` at lines 754, 803, 849 — each calls `get_search_service()` via `from core.search import get_search_service` (an import from the shim layer, at lines 645, 768, 815, 863). A CRUD module reaching into a service layer inverts the dependency direction.

**`get_all_memory_blocks` parameter explosion** (evidence, `crud.py:239–262`): 22 parameters including `scope_ctx: Optional[ScopeContext]`, `filter_scope: Optional[str]`, `filter_organization_id: Optional[uuid.UUID]` — SQL-layer filtering details surface as the public interface of a "CRUD" function.

**Repositories exist but delegate back** (evidence): `core/db/repositories/__init__.py:4` — "Phase 3 scaffolding: these repositories currently delegate to existing functions in `core.db.crud`." The `memory_blocks` repository at `repositories/memory_blocks.py` contains the actual implementations, while `crud.py` now delegates to it for memory operations but still holds the implementation for `apply_consolidation` and all three search functions.

**Seam to draw**:
1. Move `apply_consolidation` → `core/services/consolidation_service.py::apply_consolidation(db, suggestion_id: UUID) -> MemoryBlock`
2. Remove search functions from `crud.py`; have handlers call `search_service.search(...)` directly, bypassing `crud` entirely
3. Complete the Phase 3 migration: move all remaining domain implementations into their per-domain repository files; `crud.py` becomes a backwards-compat facade that can be deleted after consumers are migrated

---

### 1.3 `src/api/memoryService.ts` — Seven Backend Resource Domains

**Severity**: High | **Effort**: Medium

`apps/hindsight-dashboard/src/api/memoryService.ts` exports 30+ methods covering:
- memory blocks CRUD
- keywords (add/remove associations, suggest)
- consolidation suggestions (list, validate, reject, get count)
- pruning (suggest, confirm)
- compression (compress, apply)
- bulk operations (generate keywords batched, apply keywords batched)
- support contact and build-info (unrelated admin resource)

**Abstraction-level violation** (evidence): `bulkGenerateKeywordsBatched` and `bulkApplyKeywordsBatched` implement multi-batch orchestration with `onProgress` callbacks — loop-and-accumulate logic that belongs in a higher-level service or hook layer, not an HTTP-wrapper module.

**URL resolution duplication** (evidence, line 26–47): A `base()` function duplicating `http.ts::apiBase()` including a hardcoded `:3000` dev port check. It emits `console.log('[DEBUG] memoryService base URL:...')` on every call (line 46).

**Double-export smell** (evidence, line 187): The module's default export is re-destructured as named exports, making every import see both the object and all individual methods.

**Two non-existent backend endpoints** (evidence, lines 158 and 175): `suggestKeywords` calls `POST /memory-blocks/${id}/suggest-keywords` (404) and `mergeMemoryBlocks` calls `POST /memory-blocks/merge` (404). Both are therefore dead dashboard features.

**Seam to draw**: Split into:
- `memoryBlocksService.ts` — CRUD + archive + feedback + keyword-associations + scope-change
- `consolidationService.ts` — consolidation suggestions list/validate/reject + prune suggest/confirm
- `memoryCompactionService.ts` — compression + bulk-compact
- `keywordOrchestrationService.ts` (or a hook `useKeywordGeneration`) — batch keyword generation/apply with progress callbacks
- Remove `contactSupport` and `buildInfo` to `supportService.ts`

---

### 1.4 `core/api/deps.py` — Untyped Dict as Identity Contract

**Severity**: High | **Effort**: Small

`apps/hindsight-service/core/api/deps.py:118,231` returns `Tuple[Any, Dict[str, Any]]`. The dict has seven well-known keys (`id`, `email`, `is_superadmin`, `memberships`, `memberships_by_org`, `pat`, `dev_mode_pat`) that every downstream handler must know by string name.

**Evidence of spread coupling**: The manual auth resolution in the three search endpoints in `main.py` (lines 1070–1110) reconstructs this dict by hand with the same keys: `{"id": u.id, "is_superadmin": bool(u.is_superadmin), "memberships": memberships, "memberships_by_org": ...}`. This duplicated construction is exactly what happens when there is no canonical type — each caller rebuilds the shape from memory.

The `ensure_pat_allows_write(current_user: Dict[str, Any])` and `ensure_pat_allows_read` function signatures at lines 311 and 353 also accept `Dict[str, Any]`, propagating the untyped contract downstream.

**Seam to draw**:
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
Change `get_current_user_context` and `get_current_user_context_or_pat` to return `Tuple[User, CurrentUserContext]`. Update `ensure_pat_allows_write(ctx: CurrentUserContext)`.

---

### 1.5 `context/OrganizationContext.tsx` — Scope Switching Mixed with Org Management State

**Severity**: Medium | **Effort**: Small

`apps/hindsight-dashboard/src/context/OrganizationContext.tsx` mixes two concerns in one context:
- **Scope switching** (personal / organization / public): `switchToPersonal`, `switchToOrganization`, `switchToPublic`, persistence to localStorage
- **Organization management state**: `currentOrganization`, `currentUserMembership`, `loading`, `error`, `organizations` list

The `switchToOrganization` method calls `organizationService.getMembers()` internally to verify membership — business verification logic embedded in a context.

The 11-item context value (evidenced by `02-module-interfaces.md §1.2`) is too wide for a context whose primary job is scope signaling.

**Seam to draw**: Extract scope state into a dedicated `ScopeContext` (active scope + org ID + switch functions); leave org management state (`currentOrganization`, `currentUserMembership`, `organizations`) in `OrganizationContext`. The `ScopeContext` can be a thin provider wrapping `localStorage` with no API calls.

---

## 2. Cohesion

### 2.1 `notificationService.ts` — Maximally Stable but Fully Concrete

**Severity**: High | **Effort**: Small

`apps/hindsight-dashboard/src/services/notificationService.ts` has an instability index of 0.00 with 32 afferent dependents (the highest fan-in in the entire frontend codebase). It is a concrete in-browser event bus — replacing the toast implementation requires touching 32 files because there is no interface between them.

**Three of the 10 api/ modules import it directly** (evidence: `agentService.ts:1`, `memoryService.ts:1`, `organizationService.ts:2`), creating a layering violation (HTTP transport layer depends on UI notification layer).

**Seam to draw**: Extract `INotificationService` to `src/types/notifications.ts`:
```ts
interface INotificationService {
  showSuccess(message: string): void;
  showError(message: string, action?: string): void;
  show401Error(): void;
  showNetworkError(): void;
  showWarning(message: string): void;
}
```
Remove `notificationService` from all `api/` modules. API modules should throw structured errors (`ApiError` with `status: number` and `message: string`). A single error-boundary hook or React Query `onError` handles the toast firing at the component layer.

---

### 2.2 `core/services/__init__.py` — Partial and Inconsistent Re-exports

**Severity**: Low | **Effort**: Small

`apps/hindsight-service/core/services/__init__.py` re-exports only `EmbeddingService` and `QueryExpansionEngine`. `SearchService`, `NotificationService`, `EmailService`, and `BetaAccessService` are not included — consumers of those must know the submodule path.

**Evidence of leaky abstraction**: The file exports `reset_embedding_service_for_tests` and `reset_query_expansion_engine_for_tests` — test-lifecycle helpers in the production package surface.

**Seam to draw**: Either make the `__init__.py` a complete aggregator for all 7 services (and move test helpers to a `_testing.py` module), or drop the re-exports entirely and require all callers to import from submodules directly. The partial state is the worst option.

---

## 3. Coupling

### 3.1 `notifications.py` — Runtime `metadata`/`metadata_json` Patch

**Severity**: High | **Effort**: Small

`apps/hindsight-service/core/api/notifications.py` patches the ORM object's attribute at runtime in at least two handler functions (evidence: lines 48 and 104):
```python
setattr(n, 'metadata', getattr(n, 'metadata_json', None))
```
This is tight coupling between the HTTP handler and an ORM serialization detail. The cause is a naming collision: SQLAlchemy reserves `.metadata` at the mapper level, so the column was renamed `metadata_json`, but the Pydantic schema field is `metadata`. The three handlers (and any future handler that touches notifications) must remember this patch or produce silent `null` serialization.

**Seam to draw**: Add a `@property` to the `Notification` SQLAlchemy model:
```python
@property
def metadata(self) -> Optional[dict]:
    return self.metadata_json
```
Or rename the Pydantic schema field to `metadata_json` to match the column. Either approach removes the runtime patch from all handler functions.

---

### 3.2 `HybridRankingConfig` — Scoring Internals as Public Type

**Severity**: Medium | **Effort**: Small

`apps/hindsight-service/core/services/search_service.py:60` — `HybridRankingConfig` is a public dataclass with 20 fields including `normalization_method`, `reranker_provider`, `scope_personal_bonus`, `recency_half_life_days`. These are scoring algorithm internals. The class is public and importable by any caller.

Any module that constructs or reads `HybridRankingConfig` directly is coupled to the algorithm's tuning parameters. If the scoring algorithm changes (e.g., replacing BM25 with a learned model), every caller of `HybridRankingConfig` needs to be updated.

**Seam to draw**: Make `HybridRankingConfig` private (`_HybridRankingConfig`) or `__all__`-excluded. Expose only:
```python
def get_search_service() -> SearchService  # existing factory
def configure_search(overrides: SearchOverrides) -> None  # for callers that need to tune weights
```
where `SearchOverrides` contains only the caller-facing fields (`fulltext_weight`, `semantic_weight`, `limit`, `min_score`).

---

### 3.3 Three Search Endpoints Duplicate Auth Resolution (40+ lines each)

**Severity**: High | **Effort**: Small

`apps/hindsight-service/core/api/main.py:1070–1110` and the equivalent blocks in the semantic and hybrid endpoint handlers each manually reconstruct the user context dict by:
1. Calling `get_current_user_context_or_pat(...)` if an auth header is present
2. Calling `resolve_identity_from_headers(...)` + `get_or_create_user_for_request(...)` + `get_user_memberships(...)` and assembling the dict by hand if not

The manually assembled dicts at lines ~1096–1100 **do not call `ensure_pat_allows_read`** and **do not apply `apply_optional_scope_narrowing`**, meaning PAT org restrictions and scope narrowing are silently skipped for these three search endpoints.

**Seam to draw**: Replace the inline auth block in all three handlers with:
```python
Depends(get_scoped_user_and_context_optional)
```
where `get_scoped_user_and_context_optional` is a variant of `get_scoped_user_and_context` that does not raise 401 if no auth is present (matching the optional-auth contract of search). This is a one-function addition to `deps.py`.

---

### 3.4 `crud.py` Importing via `core.search` Compatibility Shim

**Severity**: Medium | **Effort**: Small

`apps/hindsight-service/core/db/crud.py` imports `from core.search import get_search_service` at lines 645, 768, 815, and 863. `core/search/__init__.py` is a documented compatibility shim that re-exports from `core.services.search_service`. This means a DB-access module depends on a shim layer that depends on a service layer — a two-hop dependency through an indirection that exists only for migration purposes.

The same pattern exists in `core/db/repositories/memory_blocks.py:19` — the repository also imports via the shim.

**Seam to draw**: Change both `crud.py` and `repositories/memory_blocks.py` to import directly: `from core.services.search_service import get_search_service`. Once all callers migrate, the shim can be deleted.

---

## 4. Dependency Direction

### 4.1 Frontend: `api/` Layer Depends on `services/` (Notification Bus)

**Severity**: High | **Effort**: Small (see §2.1 for proposed seam)

The natural layer order is `services → api → context → components`. Three `api/` modules import from `services/` (evidence: `agentService.ts:1`, `memoryService.ts:1`, `organizationService.ts:2`). This inverts the dependency because the notification service is the notification **UI mechanism** — a higher-level concern than an HTTP transport wrapper.

---

### 4.2 Frontend: `utils/featureFlags.ts` Depends on `api/authService.ts`

**Severity**: Low | **Effort**: Small

`apps/hindsight-dashboard/src/utils/featureFlags.ts:1` imports `CurrentUserInfo` from `api/authService.ts`. `utils/` is the foundation layer (instability I = 0.20); `api/` sits above it (I = 0.17). The fix is to move `CurrentUserInfo` to `src/types/domain.ts`, which has no outgoing edges.

---

### 4.3 Backend: `crud.py` Depends on `core.services.search_service` (Via Shim)

**Severity**: Medium | **Effort**: Small (see §3.4 for proposed seam)

The canonical dependency direction is `api → services → db`. `crud.py` (db layer) calling into `search_service` (service layer) reverses this. Even though the search calls go through a shim, the structural inversion exists in both `crud.py` and `repositories/memory_blocks.py`.

---

### 4.4 Backend: `core/api/main.py` Imports `_ensure_dev_mode_defaults` from `deps.py`

**Severity**: Medium | **Effort**: Small

`apps/hindsight-service/core/api/main.py:45` imports `_ensure_dev_mode_defaults` — a private (underscore-prefixed) function from `core/api/deps.py`. A module reaching into a sibling module's private implementation breaks the encapsulation boundary. `_ensure_dev_mode_defaults` is a db-side side effect (ensures a dev PAT exists) and should either be called by `deps.py` itself before returning, or made public with an explicit contract.

---

### 4.5 Backend: `core/pruning/` Depends on `core/services/`

**Severity**: Low | **Effort**: None (acceptable)

`core/pruning/pruning_service.py` and `core/pruning/compression_service.py` call `core/services/search_service` and `core/services/embedding_service`. This is consistent with the intended direction (`pruning → services → db`). Not a violation; recorded here for completeness.

---

## 5. Abstraction Boundary Quality

### 5.1 Frontend → Backend: Three Missing/Broken Endpoints

**Severity**: Critical | **Effort**: Medium (requires backend implementation or dashboard removal)

The frontend→backend boundary has two completely broken call sites (evidence: `03-api-surface.md §3.5,3.6`):
- `memoryService.ts:175` calls `POST /memory-blocks/merge` — no backend route; 404
- `memoryService.ts:158` calls `POST /memory-blocks/{id}/suggest-keywords` — no backend route; 404

These are not contract-drift issues — the backend has no implementation at all. The "Merge Memory Blocks" and "Suggest Keywords" UI features are silently broken.

The boundary is further eroded by the 5-field `MemoryBlock` stub in `memoryService.ts:50` vs. the 19-field backend schema. This is an incomplete type boundary: callers of `getMemoryBlockById` are typed against a stub that omits `conversation_id`, `archived`, `feedback_score`, `keywords[]`, and 10 other fields.

---

### 5.2 MCP → Backend: Scope Is Set at Construction Time

**Severity**: Medium | **Effort**: Medium

`mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts` sets `X-Active-Scope` and `X-Organization-Id` as static Axios headers at construction time from env vars. Scope cannot change per-request. This means a single MCP server instance cannot serve requests for different organizations or switch between personal and organization scope — the configuration is baked in at process start.

This is not merely a flexibility issue. The boundary design assumes all MCP calls within a single process have the same scope context. If an LLM agent issues a `create_memory_block` and then an `advanced_search_memories` with different intended scopes, the second call silently uses the first's scope.

**Seam to draw**: Add `scope?: string` and `organizationId?: string` as optional per-call overrides in `MemoryServiceClient` methods. The constructor default remains for backward compatibility; per-call values shadow it.

---

### 5.3 Services → DB: `apply_consolidation` Lives in the DB Layer

**Severity**: High | **Effort**: Small (see §1.2)

`core/db/crud.py:528` hosts `apply_consolidation` — an 80-line function that archives original memory blocks, creates a merged block, and re-scopes keywords. This is business logic (a multi-step domain transaction) that has accreted in the persistence layer. The DB layer should not decide business rules about what gets archived and what gets created; that decision belongs in `core/services/consolidation_service.py`.

---

### 5.4 API → Services: `core/api/main.py` as a Service Aggregator

**Severity**: Critical | **Effort**: Medium (see §1.1)

The app factory's boundary with services is broken because it is both the app assembler and a direct service consumer. When the app factory holds endpoint handlers, it means any change to pruning, compression, search, or keyword generation logic touches the same file that owns CORS and middleware configuration. The change-coupling is structural.

---

## 6. Right-Sized Seams

### 6.1 Missing Abstraction: `INotificationService` Interface (Frontend)

**Severity**: High | **Effort**: Small

32 dependents on a concrete singleton that has no interface. See §2.1 for the proposed seam. The fix is additive (add the interface, no callers need to change in the short term) and unlocks unit testing of all api/ and context/ modules.

---

### 6.2 Missing Abstraction: `CurrentUserContext` Dataclass (Backend)

**Severity**: High | **Effort**: Small

15+ handlers coupled to a `Dict[str, Any]` with undocumented shape. See §1.4 for the proposed seam. The three search endpoints already demonstrate the failure mode: they manually reconstruct the same dict shape (missing two enforcements in the process). A typed dataclass prevents future handlers from making the same omission.

---

### 6.3 Over-Engineered: `core/db/repositories/` Phase 3 Scaffolding

**Severity**: Medium | **Effort**: Large (to complete) or Small (to roll back)

`core/db/repositories/__init__.py:4` explicitly documents that these repositories "currently delegate to existing functions in `core.db.crud`". The namespace exists with no behavioral separation. A caller choosing `crud.create_memory_block` vs `repositories.memory_blocks.create_memory_block` gets identical behavior from an identical code path.

The current state provides the cognitive overhead of two abstraction layers with the actual isolation of zero. Either:
- **Complete the migration**: move implementations into per-domain repository files, make `crud.py` a facade, then delete it. The `memory_blocks` repository is furthest along (it has real implementations).
- **Roll back**: delete the scaffolding, keep `crud.py`, file a backlog item. This is the honest state.

Holding the half-state is the worst option because it creates false confidence that the refactor is "in progress."

---

### 6.4 Over-Engineered: Dual Org Context Architecture (Frontend)

**Severity**: High | **Effort**: Small

`App.tsx:355–359` mounts both `<OrganizationProvider>` and `<OrgProvider>`. All consumers of `OrgContext` are dead code (`OrgSwitcher.tsx`, `AddKeywordModal.tsx`, `AddAgentModal.tsx`, `AddMemoryBlockModal.tsx` — all confirmed dead by the dependency-graph analysis). The vestigial `OrgContext` writes to `sessionStorage.ACTIVE_SCOPE` while `OrganizationContext` writes to both `localStorage.selectedScope` and `sessionStorage.ACTIVE_SCOPE`. Both dispatch the same `orgScopeChanged` window event.

The risk is not hypothetical — new code reading from `localStorage.selectedScope` and writing to `sessionStorage.ACTIVE_SCOPE` will silently diverge. This is an active bug surface with zero active consumers of the old path.

**Seam to draw**: Single-PR deletion of `OrgContext.tsx`, `orgsService.ts`, `OrgSwitcher.tsx`, and the four dead components that use them. Remove `<OrgProvider>` from `App.tsx:356`. No behavior change for live code.

---

### 6.5 Missing Abstraction: `get_scoped_user_and_context_optional` (Backend)

**Severity**: High | **Effort**: Small (see §3.3)

The three typed search endpoints in `main.py` exist because there was no auth dependency that supported optional authentication at the time they were written. The manual 40-line auth block is a workaround for a missing `deps.py` callable. Adding `get_scoped_user_and_context_optional` (returns `None` if no auth header is present, rather than raising 401) would eliminate all three manual blocks, restore the missing `ensure_pat_allows_read` and `apply_optional_scope_narrowing` calls, and allow the three endpoints to be moved to proper router files.

---

## Findings Table

| Severity | Area | Issue | Why It Matters |
|----------|------|-------|----------------|
| Critical | `core/api/main.py` | App factory hosts 14 endpoint handlers across 8 domains + 130-line embedded helper | One file owns two incompatible concerns; changes to any domain touch the assembly file |
| Critical | `core/db/crud.py` | 975 lines, 75 functions, 8 domains; business logic (`apply_consolidation`) in DB layer; search service called from DB layer | No isolation between domains; any schema change cascades; dependency inversion (db→services) |
| Critical | Dashboard `memoryService.ts` + backend | Two non-existent endpoints (`/merge`, `/suggest-keywords`) called by dashboard | "Merge" and "Suggest Keywords" features silently 404; boundary has no enforcement mechanism |
| High | `notificationService.ts` | 32 dependents on concrete singleton; api/ layer imports services/ layer | Inverts dependency direction; blocks unit testing of all api modules without toast-bus stub |
| High | `core/api/notifications.py` | `setattr(n, 'metadata', getattr(n, 'metadata_json', None))` patched in 2+ handlers | Future handler that forgets the patch produces silent `null` serialization |
| High | `core/api/deps.py` | `Dict[str, Any]` user context with 7 undocumented keys consumed by 15+ handlers | Three search endpoints already demonstrate the failure mode: manual reconstruction omits two security enforcement steps |
| High | `OrgContext` + `OrganizationContext` | Both mounted in `App.tsx`; write same logical keys to `sessionStorage` vs `localStorage`; all consumers of old path are dead code | Active bug surface; silent divergence possible from any new code |
| High | `apply_consolidation` in `crud.py` | 80-line multi-step business transaction in the DB-access layer | Service/DB boundary violated; consolidation logic changes require touching the DB module |
| High | Three search endpoints in `main.py` | 40+ lines of manual auth resolution per endpoint, missing `ensure_pat_allows_read` and scope narrowing | PAT org restrictions and scope narrowing are silently skipped; security gap |
| Medium | `HybridRankingConfig` | 20 public fields exposing scoring algorithm internals | Callers coupled to algorithm tuning parameters; algorithm evolution requires API-surface change |
| Medium | `core.search` shim import in `crud.py` + `repositories/memory_blocks.py` | Two-hop dependency through a migration shim | DB layer coupled to a service via an indirection that exists only for migration bookkeeping |
| Medium | `core/db/repositories/` Phase 3 scaffolding | Namespace with no behavioral separation from `crud.py` | False progress; cognitive overhead of two layers with isolation of zero |
| Medium | `main.py:45` imports `_ensure_dev_mode_defaults` | Private symbol accessed across module boundary | Encapsulation broken; `deps.py` internals exposed to app factory |
| Medium | MCP scope fixed at construction time | `MemoryServiceClient` cannot change scope per-call | Single MCP instance cannot serve multi-scope agent workflows |
| Low | `utils/featureFlags.ts` → `api/authService.ts` | Foundation layer depends on API layer | `CurrentUserInfo` type inversion; blocks reuse of feature flags in non-browser contexts |
| Low | `core/services/__init__.py` partial re-exports | Only 2 of 7 services re-exported; test helpers in production package | Callers must know internal submodule paths; test concerns leak to production surface |

---

## Ownership Conflicts

- **Auth resolution ownership is split between `deps.py` and three inline blocks in `main.py`**: `deps.py` owns `get_current_user_context_or_pat`; three endpoints in `main.py` duplicate and diverge from it. Single owner should be `deps.py`.
- **Consolidation business logic is split between `crud.py` (`apply_consolidation`) and `core/services/consolidation_service.py`** (if it exists) or the `consolidation.py` router (which calls `crud.apply_consolidation`). The business rule — archive originals, create merged block, re-scope keywords — belongs in a service, not a DB module.
- **Keyword extraction is split**: `extract_keywords_enhanced` (130 lines) lives in `main.py`; keyword association logic lives in `repositories/`; keyword search lives in `crud.py`. No single `keyword_service` owns the keyword domain.
- **Organization scope state has two owners** (`OrgContext` and `OrganizationContext`) writing to overlapping but different storage backends. Only one should exist.
- **`MemoryBlock` type definition is not co-owned but co-maintained**: dashboard `memoryService.ts:50` defines a 5-field stub, MCP `MemoryServiceClient.ts:15` defines a 12-field struct, backend `schemas/memory.py` defines 19+ fields. No single source of truth; all three drift independently.

---

## Coupling Risks

- **`notificationService` as a hidden integration point**: The 32 callers are not all equal. `api/` modules fire toasts on HTTP errors, while `context/` modules fire them on state transitions, and `components/` fire them on user actions. If `notificationService` is replaced (e.g., with a different toast library), all 32 callers need inspection.
- **`crud.py` as an implicit synchronization point**: With 75 functions and both repositories and api handlers importing from it, a refactor of any single domain in `crud.py` risks breaking callers in unrelated domains. The repositories delegation means `crud.py` is both a facade and a direct implementation — the two roles conflict.
- **`main.py` CORS config + business endpoints in one file**: A merge conflict between two contributors (one changing CORS, one adding a new search parameter) happens in the same 1353-line file with no structural separation.
- **`metadata_json` patch in `notifications.py`**: If the `Notification` model is updated (e.g., a column rename), the runtime `setattr` patch will fail silently at all three handler sites, not at import time.
- **MCP `MemoryBlock` type vs backend search response**: `MemoryServiceClient.searchFulltext/Semantic/Hybrid` return `MemoryBlock[]` but the backend returns `MemoryBlockWithScore[]`. Extra fields (`search_score`, `search_type`, `rank_explanation`) are silently dropped. Any MCP consumer that wants to display or rank by score cannot do so.

---

## Boundary Verdict

Overall: **Needs Revision**

The frontend dependency graph is a clean DAG with no cycles — the shape is sound. The problems are concentrated in three areas: (1) `main.py` and `crud.py` are god modules that have accreted unrelated responsibilities, and the Phase 3 repository extraction has stalled at a false-progress state; (2) the `notificationService` / `api/` layering inversion blocks unit testing and will become more expensive to fix as the component count grows; (3) three security-relevant gaps (auth-free mutating endpoints, missing scope narrowing in search, unguarded consolidation-suggestion delete) flow directly from the boundary problems — the inline auth duplication in `main.py` is what caused the `ensure_pat_allows_read` omission.

The highest-leverage sequence: draw the `CurrentUserContext` dataclass (closes the auth duplication gap and the security omissions simultaneously), extract `apply_consolidation` to a service (completes the services/db boundary), then migrate the app factory (shrinks `main.py` to ~150 lines and forces the endpoint-to-router assignments to be made explicitly).

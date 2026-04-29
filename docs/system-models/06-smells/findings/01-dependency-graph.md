## Dependency Graph Analysis

**Repo root**: `apps/hindsight-dashboard/src/`
**Files analyzed**: 95 (excluding test files, `vite-env.d.ts`, `jest.d.ts`)
**Internal edges**: 262 (resolved relative imports, deduplicated per file)
**External edges**: 119 (React, react-router-dom, etc. — excluded from this analysis)

### Layer Map

```
components/ (69)  ─┐
root/App.tsx  (2)  ─┤→ context/ → api/ → services/ → [types, utils, lib]
hooks/        (3)  ─┘               ↑
                              services/: sits ABOVE api in the dependency
                              direction (api/ imports services/ — see violations)
```

Intended dependency direction (outer depends on inner):

```
components → context → api → services
                   ↘    ↓
                   hooks → context
                         ↓
                   types / utils / lib  (foundation — no internal deps)
```

Actual directories:

| Layer       | Files | Role |
|-------------|-------|------|
| `components/` | 69 | React page-level and sub-components (highest instability) |
| `context/`    |  5 | React contexts: Auth, Org, Organization, Notification, PageHeader |
| `api/`        | 10 | HTTP service modules that call the backend |
| `services/`   |  1 | `notificationService` — in-browser toast/event bus |
| `hooks/`      |  3 | `usePageHeader`, `useModal`, `useTokenCreation` |
| `types/`      |  1 | `domain.ts` — shared UI type aliases |
| `utils/`      |  3 | `featureFlags`, `uuid`, `devMode` |
| `lib/`        |  1 | `viteEnv.ts` — typed env variable accessors |
| `root`        |  2 | `App.tsx` (router), `main.tsx` (entry) |

---

### Layering Violations

The codebase has **no documented layer contract** in README or CLAUDE.md, so the
layer order is inferred from actual dependency directions. Under the natural
ordering `utils/lib/types → services → api → context → hooks → components`,
two classes of violation are present.

#### Class 1: `api/` importing `services/` (runtime, significant)

`api/` modules fire toast notifications inline rather than returning errors and
letting callers decide. This couples the HTTP transport layer to the UI
notification bus.

| Source (layer) | Imports (layer) | Line | Direction | Type |
|----------------|-----------------|------|-----------|------|
| `src/api/agentService.ts` (api) | `src/services/notificationService.ts` (services) | 1 | api→services (wrong) | runtime |
| `src/api/memoryService.ts` (api) | `src/services/notificationService.ts` (services) | 1 | api→services (wrong) | runtime |
| `src/api/organizationService.ts` (api) | `src/services/notificationService.ts` (services) | 2 | api→services (wrong) | runtime |

**Consequence**: if `notificationService` changes its API, 3 API service modules
must change simultaneously. Worse, these API modules cannot be reused in any
non-browser context (e.g. a Node test environment, MCP server) without
importing the toast bus.

#### Class 2: `utils/featureFlags.ts` importing `api/authService` (runtime, moderate)

| Source (layer) | Imports (layer) | Line | Direction | Type |
|----------------|-----------------|------|-----------|------|
| `src/utils/featureFlags.ts` (utils) | `src/api/authService.ts` (api) | 1 | utils→api (wrong) | runtime |

`featureFlags.ts` imports `CurrentUserInfo` type from `authService` to shape
the `deriveApiFlagOverrides` function. Since `CurrentUserInfo` is a pure
interface, this could be resolved by moving the interface to `types/domain.ts`
or by declaring it locally in `featureFlags.ts`. The runtime import is
technically type-erased at JS output, but the TypeScript compiler dependency is
real and creates a layering inversion (utils should be a foundation that nothing
foundational depends on).

**Total**: 4 runtime violations, 0 type-only violations.

---

### Circular Dependencies

**0 cycles detected.** Tarjan SCC run over the full 95-node × 262-edge directed
graph found no strongly-connected components of size > 1. The import graph is a
DAG.

Per FP006 thresholds: **Healthy** (0 cycles).

---

### Module Metrics — Top 15 by Fan-In

| File | Fan-In | Fan-Out | Instability (I) | Flag |
|------|--------|---------|-----------------|------|
| `src/services/notificationService.ts` | 32 | 0 | 0.00 | stable-concrete |
| `src/api/memoryService.ts` | 22 | 2 | 0.08 | stable-concrete |
| `src/context/AuthContext.tsx` | 20 | 2 | 0.09 | stable-concrete |
| `src/types/domain.ts` | 15 | 0 | 0.00 | stable-abstract (types only) |
| `src/api/http.ts` | 13 | 0 | 0.00 | stable-concrete |
| `src/api/agentService.ts` | 12 | 2 | 0.14 | stable-concrete |
| `src/components/Portal.tsx` | 12 | 0 | 0.00 | stable-concrete |
| `src/components/RefreshIndicator.tsx` | 8 | 1 | 0.11 | stable-concrete |
| `src/components/Button.tsx` | 7 | 0 | 0.00 | stable-concrete |
| `src/hooks/usePageHeader.ts` | 7 | 1 | 0.12 | stable-concrete |
| `src/components/CopyToClipboardButton.tsx` | 6 | 1 | 0.14 | stable-concrete |
| `src/lib/viteEnv.ts` | 6 | 0 | 0.00 | stable-concrete |
| `src/api/organizationService.ts` | 5 | 3 | 0.38 | moderate |
| `src/context/OrgContext.tsx` | 5 | 2 | 0.29 | moderate |
| `src/context/NotificationContext.tsx` | 4 | 2 | 0.33 | moderate |

### Module Metrics — Top 10 by Fan-Out

| File | Fan-In | Fan-Out | Instability (I) | Flag |
|------|--------|---------|-----------------|------|
| `src/App.tsx` | 1 | 33 | 0.97 | high-fan-out |
| `src/components/MemoryBlockList.tsx` | 0 | 13 | 1.00 | high-fan-out + dead |
| `src/components/MemoryOptimizationCenter.tsx` | 1 | 12 | 0.92 | high-fan-out |
| `src/components/ArchivedMemoryBlockList.tsx` | 1 | 11 | 0.92 | high-fan-out |
| `src/components/MemoryBlocksPage.tsx` | 1 | 11 | 0.92 | high-fan-out |
| `src/components/Dashboard.tsx` | 1 | 8 | 0.89 | high-fan-out |
| `src/components/AddMemoryBlockModal.tsx` | 1 | 7 | 0.88 | high-fan-out |
| `src/components/AgentManagementPage.tsx` | 1 | 7 | 0.88 | high-fan-out |
| `src/components/ConsolidationSuggestions.tsx` | 1 | 7 | 0.88 | high-fan-out |
| `src/components/KeywordManager.tsx` | 1 | 7 | 0.88 | high-fan-out |

---

### God Modules (fan-in > 10 OR fan-out > 8)

Per FP006 thresholds: fan-in > 10 = Watch.

| File | Fan-In | Fan-Out | Why It's Risky |
|------|--------|---------|----------------|
| `src/services/notificationService.ts` | 32 | 0 | Depended on by **every** component, all 3 api services, and both hooks that trigger notifications. Any API change breaks 32 callers. |
| `src/api/memoryService.ts` | 22 | 2 | Core data API; 22 importers means a signature change (pagination, filters, response shape) cascades across half the codebase. |
| `src/context/AuthContext.tsx` | 20 | 2 | Auth state is read by nearly every page-level component; also imports from utils (featureFlags cycle path). |
| `src/api/agentService.ts` | 12 | 2 | Shared by all memory-related pages and modals. |
| `src/components/Portal.tsx` | 12 | 0 | Pure utility but depended on by every modal (12 of them). Stable but if the Portal contract changes, all modals break. |
| `src/App.tsx` | 1 | 33 | Router god-file. Directly instantiates 29 page-level components and 4 providers. Not a fan-in god module but fan-out = 33 makes it a change magnet for routing changes. |
| `src/components/MemoryBlockList.tsx` | 0 | 13 | 13 outgoing edges and zero incoming — dead code with high surface area (see Surprising Findings). |
| `src/components/MemoryOptimizationCenter.tsx` | 1 | 12 | Single-mounted page with 12 deps including both api services and 4 child modals. |
| `src/components/MemoryBlocksPage.tsx` | 1 | 11 | Same pattern as above. |
| `src/components/ArchivedMemoryBlockList.tsx` | 1 | 11 | Same pattern as above. |

---

### Hub Modules (high fan-in AND high fan-out)

No module exceeds both fan-in > 5 and fan-out > 5 simultaneously. The graph
has a clean split: high-fan-in modules are stable abstractions (services,
api, context) with minimal outgoing edges; high-fan-out modules are leaf
pages/components with minimal incoming edges. **No hub modules identified.**

---

### Instability Index by Layer

`I = Ce / (Ca + Ce)` where Ce = efferent (fan-out) coupling, Ca = afferent (fan-in) coupling.
D-line violation: I is near 0 (stable) but the module is concrete (not abstract).

| Layer | Files | Ca (fan-in total) | Ce (fan-out total) | I | D-line status |
|-------|-------|-------------------|--------------------|---|---------------|
| `types/` | 1 | 15 | 0 | **0.00** | OK — pure types, maximally stable, maximally abstract |
| `lib/` | 1 | 6 | 0 | **0.00** | OK — env accessors, appropriately stable |
| `services/` | 1 | 32 | 0 | **0.00** | **D-violation**: maximally stable but fully concrete (event-bus implementation). High change cost. |
| `api/` | 10 | 62 | 13 | **0.17** | **D-violation**: 62 afferent deps on concrete HTTP implementations. Should be behind interfaces. |
| `context/` | 5 | 34 | 8 | **0.19** | Mostly OK — React Contexts are effectively interfaces. Acceptable stability. |
| `utils/` | 3 | 4 | 1 | **0.20** | One violation: featureFlags imports api/ (inverts the layer). |
| `hooks/` | 3 | 10 | 3 | **0.23** | Healthy — light layer, mainly wires context to components. |
| `components/` | 69 | 98 | 203 | **0.67** | Expected for leaf layer. High instability is correct for UI code. |

**D-line violations**:

1. `services/notificationService.ts`: I = 0.00, but it is a concrete in-browser
   toast-event bus (32 dependents on implementation detail). Changing the toast
   API or replacing it with a different bus requires touching 32 files. Mitigation:
   extract an interface (`INotificationService`) in `types/` and program to the
   interface.

2. `api/` layer: I = 0.17 with 62 afferent dependencies on concrete HTTP service
   objects. No interfaces exist in the codebase for these services. Every component
   that calls `memoryService.getMemoryBlocks()` directly couples to the HTTP
   implementation; this blocks unit-testing without network mocks.

---

### Dependency Clusters

| Cluster | Files that import it | Matches documented subsystem? |
|---------|---------------------|-------------------------------|
| `notificationService` cluster | 32 files (all layers) | De-facto cross-cutting infrastructure. Not documented as a subsystem — it is wired directly into api/, context/, hooks/, and components/. |
| `memoryService` cluster | 22 files | Memory management subsystem. Loosely matches the `MemoryBlocks*` / `MemoryOptimization*` / `ArchivedMemory*` component grouping. |
| `AuthContext` cluster | 20 files | Auth/session subsystem. Tightly defined — all consumers use `useAuth()`. |
| `agentService` cluster | 12 files | Agent management subsystem. Narrower than memory; shared by agent pages + memory modals. |
| `api/` cluster (any) | 48 files | All page-level components import at least one api service directly. No service-layer indirection (e.g. custom hooks) separates components from HTTP calls. |

Cluster boundaries do not match the file-system directories beyond the
loose `components/` grouping. Notably, the notifications cross-cutting cluster
spans every layer and is not isolated into its own subsystem directory.

---

### Surprising Findings

#### 1. Dead code: 10 modules never imported by production code

| File | Lines | Notes |
|------|-------|-------|
| `src/components/MemoryBlockList.tsx` | 671 | Refactored replacement for `MemoryBlocksPage`; comment on line 1 says "Refactored MemoryBlockList component" but it is never mounted. 13 outgoing edges make it the second-highest fan-out file. |
| `src/components/AddAgentDialog.tsx` | 63 | Stateless presentational version of `AddAgentModal`. Zero callers; `AddAgentModal` is used instead. |
| `src/components/AddKeywordModal.tsx` | 143 | Full keyword-creation modal — never imported anywhere in the production tree. |
| `src/components/FloatingActionButton.tsx` | 68 | Wraps `AddMemoryBlockModal`; not mounted anywhere in `App.tsx` or any page. |
| `src/components/MemoryBlockTable_new.tsx` | — | Cloned from `MemoryBlockTable.tsx` with `_new` suffix; same imports, never used. |
| `src/components/MemoryBlockTable_old.tsx` | — | Previous version; never used. |
| `src/components/MemoryCompressionModal.tsx` | 381 | Distinct from `MemoryCompactionModal`; imports from it (`MemoryCompactionResult`). Not mounted anywhere. |
| `src/components/OrgSwitcher.tsx` | 60 | Superseded by `OrganizationSwitcher.tsx`. Only mention in production code is a comment in `MainContent.tsx` about z-index stacking. |
| `src/components/QuickCreateTokenModal.tsx` | — | Token-creation flow; not mounted anywhere. `TokenManagement.tsx` is used instead. |
| `src/utils/devMode.ts` | — | Dev-auth-header helper; not imported by any non-test source. |

**Total dead code**: ~1400+ lines in 10 files. The three `MemoryBlockTable` variants
alone indicate an incomplete refactor that was never cleaned up.

#### 2. Dual org-context architecture

Two parallel context/service pairs manage organization state:

- **OrgContext** (`context/OrgContext.tsx`) + `api/orgsService.ts`: provides `useOrg()`, used by `AddKeywordModal`, `AddAgentModal`, `AddMemoryBlockModal`, and `OrgSwitcher`. All four of these consumers are dead code (never imported).
- **OrganizationContext** (`context/OrganizationContext.tsx`) + `api/organizationService.ts`: provides `useOrganization()`, used by `OrganizationManagement` and `OrganizationSwitcher` (both live).

The `OrgContext` path is effectively vestigial — its consumers are all dead.
App.tsx mounts both `<OrgProvider>` and `<OrganizationProvider>` at line 20–21,
so both run at startup even though only `OrganizationContext` feeds live UI.

#### 3. `MemoryCompressionModal` imports from `MemoryCompactionModal`

`src/components/MemoryCompressionModal.tsx:5` imports `MemoryCompactionResult` type
from `./MemoryCompactionModal`. This cross-component type dependency means that
`MemoryCompactionModal` has a hidden export responsibility beyond its UI role.
Neither modal is reachable from live code.

#### 4. `api/` modules do not return errors — they toast them

`agentService.ts`, `memoryService.ts`, and `organizationService.ts` call
`notificationService.show401Error()` / `showNetworkError()` / `showApiError()`
inline, on lines 31, 63, 65, 77, etc. The calling components therefore do
**not** receive structured errors — they receive only thrown `Error('...')`.
This removes the ability for callers to distinguish error types programmatically
(e.g. differentiate 401 from 500 or network failures). It also means tests of
these API modules require mocking the notification bus.

---

### Summary

The dependency graph is a clean DAG (zero cycles) and the overall shape is
architecturally sound: stable foundation modules (`types`, `lib`, `services`,
`api`) are heavily depended-on and have near-zero outgoing edges; leaf
components correctly have high instability. The **two structural health risks**
are: (1) `api/` modules importing `services/notificationService` directly,
embedding UI-layer side-effects inside the HTTP layer — this is the primary
layering violation and blocks pure unit testing; (2) ten dead-code modules
totalling ~1400 lines including a fully-functional alternative implementation
of `MemoryBlockList` (671 lines, 13 deps) that is never mounted, indicating
an in-progress refactor was abandoned. The **top action** is to untangle the
notification coupling from `api/` by letting callers handle errors, then
delete the dead code cluster to reduce cognitive surface area by ~15%.

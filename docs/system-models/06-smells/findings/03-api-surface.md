# API Surface Audit — Hindsight AI (03-interfaces research)

Generated: 2026-04-29
Source revision: `main` (clean worktree at commit 3c70372)

---

## 1. HTTP Route Inventory

Routes are assembled in `/home/jean/git/hindsight-mbse/apps/hindsight-service/core/api/main.py`
(app bootstrap at `/home/jean/git/hindsight-mbse/apps/hindsight-service/app.py` — thin re-export only).

Auth abbreviations used below:
- **oauth** — resolved from `x-auth-request-user/email` or `x-forwarded-user/email` headers injected by oauth2-proxy
- **PAT** — `Authorization: Bearer <token>` or `X-API-Key: <token>`, validated by `get_current_user_context_or_pat`
- **either** — accepts both oauth and PAT
- **none** — no auth guard (public)
- **beta-admin** — `require_beta_access_admin` (superadmin or BETA_ACCESS_ADMIN_EMAILS env entry)
- **superadmin** — `is_superadmin` flag check inside handler

Dashboard caller column: "dash" = called by at least one `apps/hindsight-dashboard/src/api/*.ts` service.
MCP caller column: "mcp" = called by `mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts`.

### 1.1 `core/api/main.py` — inline router (no prefix)

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/user-info` | Resolve identity, return user + memberships + feature flags | oauth / PAT / none(dev) | untyped dict | yes | yes (`whoami`) |
| GET | `/conversations/count` | Count unique conversations for dashboard stat card | either | `{"count": int}` (dict) | yes | no |
| POST | `/memory/prune/suggest` | LLM-scored pruning suggestions batch | none (no dep) | `dict` | yes | no |
| POST | `/memory/prune/confirm` | Archive selected blocks for pruning | none (no dep) | `dict` | yes | no |
| POST | `/memory-blocks/{id}/change-scope` | Move a memory block between personal/org/public scopes | either | `schemas.MemoryBlock` | no | no |
| POST | `/memory-blocks/{id}/compress` | LLM-compress a single block, return suggestion | none (no dep) | `dict` | yes | no |
| POST | `/memory-blocks/{id}/compress/apply` | Apply compressed content to block | none (no dep) | `schemas.MemoryBlock` | yes | no |
| POST | `/memory-blocks/bulk-generate-keywords` | Extract keywords for a list of blocks | none (no dep) | `dict` | yes | no |
| POST | `/memory-blocks/bulk-apply-keywords` | Batch-apply keyword associations | none (no dep) | `dict` | yes | no |
| POST | `/memory-blocks/bulk-compact` | Concurrent LLM bulk compaction | none (no dep) | `dict` | yes | no |
| GET | `/memory-blocks/search/fulltext` | BM25 full-text search | either (optional) | `List[schemas.MemoryBlockWithScore]` | no* | yes |
| GET | `/memory-blocks/search/semantic` | Embedding similarity search | either (optional) | `List[schemas.MemoryBlockWithScore]` | no* | yes |
| GET | `/memory-blocks/search/hybrid` | Weighted fulltext+semantic | either (optional) | `List[schemas.MemoryBlockWithScore]` | no* | yes |
| GET | `/health` | Liveness probe | none | `{"status":"ok","service":...}` | no | no |

*The dashboard calls the unified `/memory-blocks/search/` endpoint (see memory_blocks router below), not these three directly.

**Notable:** `/memory/prune/suggest`, `/memory/prune/confirm`, `/memory-blocks/{id}/compress`, `/memory-blocks/{id}/compress/apply`, `/memory-blocks/bulk-generate-keywords`, `/memory-blocks/bulk-apply-keywords`, `/memory-blocks/bulk-compact` all accept `dict` bodies (no Pydantic input model) and have **no auth dependency** — they are protected only by the global `enforce_readonly_for_guests` middleware, which only requires _some_ auth header to be present. No scope or org enforcement occurs.

### 1.2 `core/api/memory_blocks.py` — prefix `/memory-blocks`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/memory-blocks/` | Create memory block | either | `schemas.MemoryBlock` | yes | yes |
| GET | `/memory-blocks/` | List/paginate memory blocks | either | `schemas.PaginatedMemoryBlocks` | yes | yes (`getAllMemoryBlocks`) |
| GET | `/memory-blocks/archived/` | List archived blocks | either | `schemas.PaginatedMemoryBlocks` | yes | no |
| GET | `/memory-blocks/search/` | Unified keyword/strategy search | either (optional) | `List[schemas.MemoryBlock]` | yes | yes (`retrieveRelevantMemories`) |
| GET | `/memory-blocks/{id}` | Get single block | either | `schemas.MemoryBlock` | yes | yes (`getMemoryDetails`) |
| PUT | `/memory-blocks/{id}` | Update block | either | `schemas.MemoryBlock` | yes | no |
| DELETE | `/memory-blocks/{id}` | Soft-delete (archive) block | either | 204 | yes | no |
| DELETE | `/memory-blocks/{id}/hard-delete` | Hard delete block | either | 204 | yes | no |
| POST | `/memory-blocks/{id}/archive` | Archive block | either | `schemas.MemoryBlock` | yes | no |
| POST | `/memory-blocks/{id}/feedback/` | Submit feedback | either | `schemas.MemoryBlock` | no | yes (`reportMemoryFeedback`) |
| GET | `/memory-blocks/{id}/keywords/` | Get keywords for block | either | `List[schemas.Keyword]` | no | no |
| POST | `/memory-blocks/{memory_id}/keywords/{keyword_id}` | Associate keyword | either | `schemas.MemoryBlockKeywordAssociation` | yes | no |
| DELETE | `/memory-blocks/{memory_id}/keywords/{keyword_id}` | Disassociate keyword | either | 204 | yes | no |

**Note:** `/memory-blocks/search/fulltext`, `/memory-blocks/search/semantic`, `/memory-blocks/search/hybrid` (from `main.py` inline router) are registered **before** the `memory_blocks_router` is included. FastAPI route resolution is first-match. There is no ordering conflict because those paths differ from `/memory-blocks/search/` (the unified endpoint in `memory_blocks.py`). However both `/memory-blocks/search/` and the three typed search endpoints exist — the MCP server and the dashboard route to different ones.

### 1.3 `core/api/agents.py` — prefix `/agents`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/agents/` | Create agent | either | `schemas.Agent` | yes | yes |
| GET | `/agents/` | List agents | either | `List[schemas.Agent]` | yes | yes (via `getAllMemoryBlocks`) |
| GET | `/agents/search/` | Search agents by name | either (optional) | `List[schemas.Agent]` | yes | yes (`searchAgents`) |
| GET | `/agents/{id}` | Get agent | either (optional) | `schemas.Agent` | yes | no |
| PUT | `/agents/{id}` | Update agent | either | `schemas.Agent` | yes | no |
| DELETE | `/agents/{id}` | Delete agent | either | 204 | yes | no |
| POST | `/agents/{id}/change-scope` | Move agent between scopes | either | `schemas.Agent` | no | no |

### 1.4 `core/api/keywords.py` — prefix `/keywords`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/keywords/` | Create keyword | either | `schemas.Keyword` | yes | no |
| GET | `/keywords/` | List keywords | either | `List[schemas.Keyword]` | yes | no |
| GET | `/keywords/{id}` | Get keyword | either | `schemas.Keyword` | no | no |
| PUT | `/keywords/{id}` | Update keyword | either | `schemas.Keyword` | yes | no |
| DELETE | `/keywords/{id}` | Delete keyword | either | 204 | yes | no |
| GET | `/keywords/{id}/memory-blocks/` | Get memory blocks by keyword | either | `List[schemas.MemoryBlock]` | yes | no |
| GET | `/keywords/{id}/memory-blocks/count` | Count memory blocks for keyword | either | `{"count": int}` | yes | no |

### 1.5 `core/api/organizations.py` — prefix `/organizations`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/organizations/` | Create organization | oauth | untyped dict | yes | no |
| GET | `/organizations/` | List user's organizations | oauth | untyped list | yes | yes (`whoami` indirectly) |
| GET | `/organizations/manageable` | List manageable organizations | oauth | untyped list | yes | no |
| GET | `/organizations/admin` | List all organizations (superadmin) | oauth + superadmin check | untyped list | yes | no |
| GET | `/organizations/{id}` | Get organization | oauth | untyped dict | yes | no |
| PUT | `/organizations/{id}` | Update organization | oauth + owner/admin | untyped dict | yes | no |
| DELETE | `/organizations/{id}` | Delete organization | oauth + owner/admin | 204 | yes | no |
| GET | `/organizations/{id}/members` | List members | oauth | untyped list | yes | no |
| POST | `/organizations/{id}/members` | Add member | oauth + owner/admin | `{"status":"added"}` | yes | no |
| PUT | `/organizations/{id}/members/{uid}` | Update member role/perms | oauth + owner/admin | none (no return) | yes | no |
| DELETE | `/organizations/{id}/members/{uid}` | Remove member | oauth + owner/admin | 204 | yes | no |
| POST | `/organizations/{id}/invitations` | Create invitation | oauth + owner/admin | `schemas.OrganizationInvitation` | yes | no |
| GET | `/organizations/{id}/invitations` | List invitations | oauth + owner/admin | `List[schemas.OrganizationInvitation]` | yes | no |
| POST | `/organizations/{id}/invitations/{inv_id}/accept` | Accept invitation | oauth or token | `schemas.OrganizationMember` | yes | no |
| POST | `/organizations/{id}/invitations/{inv_id}/decline` | Decline invitation | oauth or token | `{"status":"revoked"}` | yes | no |
| POST | `/organizations/{id}/invitations/{inv_id}/resend` | Resend invitation | oauth + owner/admin | `schemas.OrganizationInvitation` | yes | no |
| DELETE | `/organizations/{id}/invitations/{inv_id}` | Revoke invitation | oauth + owner/admin | 204 | yes | no |

**Note:** `core/api/orgs_fixed.py` contains a duplicate router that is **never included** in `app.py`. It is dead code.

### 1.6 `core/api/users.py` — prefix `/users`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| PATCH | `/users/me` | Update display name | oauth | untyped dict | no | no |
| GET | `/users/me/tokens` | List PATs | oauth | `List[schemas.TokenResponse]` | yes | no |
| POST | `/users/me/tokens` | Create PAT | oauth | `schemas.TokenCreateResponse` | yes | no |
| DELETE | `/users/me/tokens/{id}` | Revoke PAT | oauth | 204 | yes | no |
| POST | `/users/me/tokens/{id}/rotate` | Rotate PAT | oauth | `schemas.TokenCreateResponse` | yes | no |
| PATCH | `/users/me/tokens/{id}` | Update PAT metadata | oauth | `schemas.TokenResponse` | yes | no |

### 1.7 `core/api/audits.py` — prefix `/audits`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/audits/` | List audit logs | oauth + org/superadmin | `List[schemas.AuditLog]` | no | no |

### 1.8 `core/api/consolidation.py` — no prefix

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/consolidation/trigger/` | Manually trigger consolidation | none (no dep) | `{"message":...}` | yes | no |
| GET | `/consolidation-suggestions/` | List consolidation suggestions | either | `schemas.PaginatedConsolidationSuggestions` | yes | no |
| GET | `/consolidation-suggestions/{id}` | Get single suggestion | either | `schemas.ConsolidationSuggestion` | yes | no |
| POST | `/consolidation-suggestions/{id}/validate/` | Validate/apply consolidation | either | `schemas.ConsolidationSuggestion` | yes | no |
| POST | `/consolidation-suggestions/{id}/reject/` | Reject suggestion | either | `schemas.ConsolidationSuggestion` | yes | no |
| DELETE | `/consolidation-suggestions/{id}` | Delete suggestion | none (no dep) | 204 | yes | no |

**Note:** `POST /consolidation/trigger/` and `DELETE /consolidation-suggestions/{id}` have **no auth dependency at all** — not even the middleware guest guard (which only blocks writes when _no_ auth header is present; a guest browsing without headers can delete suggestions).

### 1.9 `core/api/bulk_operations.py` — prefix `/bulk-operations`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/bulk-operations/organizations/{org_id}/inventory` | Count org resources | oauth + owner/admin | untyped dict | no | no |
| POST | `/bulk-operations/organizations/{org_id}/bulk-move` | Bulk move resources | oauth | untyped dict | no | no |
| POST | `/bulk-operations/organizations/{org_id}/bulk-delete` | Bulk delete resources | oauth | untyped dict | no | no |
| GET | `/bulk-operations/admin/operations/{id}` | Get op status (always 403) | oauth | 403 always | no | no |
| GET | `/bulk-operations/admin/operations` | List bulk ops (superadmin) | oauth + superadmin | `List[schemas.BulkOperation]` | no | no |
| POST | `/bulk-operations/admin/operations/{id}/cancel` | Cancel operation (superadmin) | oauth + superadmin | `{"message":...}` | no | no |

**Note:** There are two routes registered for `GET /bulk-operations/admin/operations/{id}` in the same file (lines 267–276 always returns 403, lines 350–377 returns the operation for superadmins). FastAPI uses the first match, so the superadmin handler at line 350 is **shadowed** and unreachable.

### 1.10 `core/api/notifications.py` — prefix `/notifications`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/notifications/` | Get user notifications | oauth | `schemas.NotificationListResponse` | yes | no |
| POST | `/notifications/{id}/read` | Mark notification read | oauth | 204 | yes | no |
| GET | `/notifications/stats` | Notification statistics | oauth | `schemas.NotificationStatsResponse` | yes | no |
| GET | `/notifications/preferences` | Get notification preferences | oauth | `schemas.NotificationPreferencesResponse` | yes | no |
| PUT | `/notifications/preferences/{event_type}` | Update preference | oauth | `schemas.UserNotificationPreference` | yes | no |
| POST | `/notifications/test/create` | Create test notification (dev) | oauth | `schemas.Notification` | yes | no |
| DELETE | `/notifications/cleanup/expired` | Cleanup expired (superadmin) | oauth + superadmin check | untyped dict | no | no |

### 1.11 `core/api/support.py` — no prefix

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/build-info` | Return build metadata | none | untyped dict | yes | no |
| POST | `/support/contact` | Submit support request | oauth | `{"status":"ok","email_log_id":...}` | yes | no |

### 1.12 `core/api/beta_access.py` — prefix `/beta-access`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| POST | `/beta-access/request` | Request beta access | oauth (header-based) | untyped dict | no | no |
| POST | `/beta-access/review/{id}` | Admin review | beta-admin | untyped dict | no | no |
| POST | `/beta-access/review/{id}/token` | Token-based review (email link) | none | untyped dict | yes | no |
| GET | `/beta-access/status` | Get own beta access status | oauth | untyped dict | no | no |
| GET | `/beta-access/pending` | List pending requests | beta-admin | untyped dict | no | no |
| GET | `/beta-access/pending/stuck` | List stuck pending requests | beta-admin | untyped dict | no | no |
| POST | `/beta-access/review/{id}/resend-token` | Resend review token email | beta-admin | untyped dict | no | no |
| GET | `/beta-access/admin/users` | List all users with beta status | beta-admin | untyped dict | yes | no |
| PATCH | `/beta-access/admin/users/{uid}` | Update user beta status | beta-admin | untyped dict | yes | no |

**Note:** `POST /beta-access/review/{id}/token` is explicitly carved out of the `enforce_readonly_for_guests` middleware (main.py:125-126) to allow unauthenticated review link clicks. This is intentional for email-link flows.

### 1.13 `core/api/memory_optimization.py` — prefix `/memory-optimization`

| Method | Path | Purpose | Auth | Response Model | dash | mcp |
|--------|------|---------|------|----------------|------|-----|
| GET | `/memory-optimization/suggestions` | Compute optimization suggestions | either | untyped dict | yes | no |
| POST | `/memory-optimization/suggestions/{id}/execute` | Execute a suggestion | either | untyped dict | yes | no |
| GET | `/memory-optimization/suggestions/{id}/preview` | Preview suggestion (stub) | none (no dep) | untyped dict | yes | no |

**Note:** The `id` parameter here is a client-side ephemeral UUID generated fresh on each `GET /memory-optimization/suggestions` call (line 47 of `memory_optimization.py`). The `execute` and `preview` endpoints re-run the analysis to find a matching suggestion by UUID, meaning suggestion IDs are not stable across requests.

---

## 2. MCP Tool Inventory

Source: `/home/jean/git/hindsight-mbse/mcp-servers/hindsight-mcp/src/index.ts`
Client: `/home/jean/git/hindsight-mbse/mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts`

The MCP server is a stdio transport MCP server authenticated via `HINDSIGHT_API_TOKEN` (Bearer) or `HINDSIGHT_API_KEY` (X-API-Key header). Scope headers (`X-Active-Scope`, `X-Organization-Id`) are set at construction time from env vars.

| Tool Name | Required Inputs | Optional Inputs | Backend Endpoint(s) | Notes |
|-----------|----------------|-----------------|---------------------|-------|
| `create_memory_block` | `content`, `lessons_learned` | `agent_id`, `conversation_id`, `errors`, `metadata` | `POST /memory-blocks/` | `agent_id` resolved from `DEFAULT_AGENT_ID` env; `conversation_id` auto-generated if absent. Injects org scope if `HINDSIGHT_ORGANIZATION_ID` set. |
| `create_agent` | `agent_name` | — | `POST /agents/` | Injects org scope if env set. |
| `retrieve_relevant_memories` | `keywords` (string or array) | `agent_id`, `conversation_id`, `limit` | `GET /memory-blocks/search/` | Converts array to CSV before sending. |
| `retrieve_all_memory_blocks` | — | `agent_id`, `limit` | `GET /memory-blocks/` | Returns filtered `{content, errors, timestamp}` subset. |
| `retrieve_memory_blocks_by_conversation_id` | — | `conversation_id`, `agent_id`, `limit` | `GET /memory-blocks/` | `conversation_id` from `DEFAULT_CONVERSATION_ID` if not provided. |
| `report_memory_feedback` | `memory_block_id`, `feedback_type` | `feedback_details`, `comment` (deprecated alias) | `POST /memory-blocks/{id}/feedback/` | Maps `memory_block_id` param → `memory_id` field in `ReportFeedbackPayload`. |
| `get_memory_details` | `memory_block_id` | — | `GET /memory-blocks/{id}` | Returns filtered `{content, errors, timestamp}` subset. |
| `search_agents` | `query` | — | `GET /agents/search/` | Returns full agent objects. |
| `advanced_search_memories` | `search_query` | `search_type`, `agent_id`, `conversation_id`, `limit`, `min_score`, `similarity_threshold`, `fulltext_weight`, `semantic_weight`, `min_combined_score`, `include_archived` | `GET /memory-blocks/search/fulltext` OR `/search/semantic` OR `/search/hybrid` | Routes to one of three endpoints depending on `search_type`. `basic` is listed in `AdvancedSearchPayload` type but the handler defaults to `fulltext` — `basic` is not handled. |
| `show_capture_checklist` | — | — | (none — local) | Returns static checklist text. |
| `whoami` | — | — | `GET /user-info` | Returns full `user-info` payload. |

Total MCP tools: **11**

### MCP Type Safety Notes

- Tool handler at line 413: `typedArgs: Record<string, any>` — all tool arguments are `any` after dispatch. Type guard functions (`isValidCreateMemoryBlockPayload`, etc.) provide runtime validation but do not propagate TS types.
- `MemoryServiceClient.searchFulltext/searchSemantic/searchHybrid` return `MemoryBlock[]` but the backend returns `List[MemoryBlockWithScore]` (which includes `search_score`, `search_type`, `rank_explanation`). The client type `MemoryBlock` does not include these fields — extra properties are silently dropped.
- `getAllMemoryBlocks` returns `GetAllMemoryBlocksResponse` (typed), but `getMemoryBlocksByConversationId` also uses `GetAllMemoryBlocksResponse` while claiming to return `MemoryBlock[]` — it extracts `.items` correctly.

---

## 3. Dashboard ↔ Backend Contract Drift

### 3.1 `MemoryBlock` type mismatch

**Dashboard** (`/home/jean/git/hindsight-mbse/apps/hindsight-dashboard/src/api/memoryService.ts`, line 50):
```ts
export interface MemoryBlock { id: string; agent_id: string; content: string; visibility_scope?: string; organization_id?: string | null; }
```
This is a minimal stub — 5 fields only.

**Backend** (`/home/jean/git/hindsight-mbse/apps/hindsight-service/core/db/schemas/memory.py`, `MemoryBlock` class):
Fields: `id`, `agent_id`, `conversation_id`, `content`, `errors`, `lessons_learned`, `metadata_col`, `feedback_score`, `retrieval_count`, `archived`, `archived_at`, `visibility_scope`, `owner_user_id`, `organization_id`, `content_embedding`, `timestamp`, `created_at`, `updated_at`, `keywords[]`.

Missing from dashboard type: `conversation_id`, `errors`, `lessons_learned`, `metadata_col`, `feedback_score`, `retrieval_count`, `archived`, `archived_at`, `owner_user_id`, `content_embedding`, `timestamp`, `created_at`, `updated_at`, `keywords`. Most `memoryService` methods return `resp.json()` untyped — this only matters where code consumes the typed `MemoryBlock` return value of `getMemoryBlockById`.

**MCP client** (`/home/jean/git/hindsight-mbse/mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts`, lines 15-28):
Closer to the backend shape but still missing `retrieval_count`, `archived`, `archived_at`, `keywords`, `visibility_scope`, `owner_user_id`, `organization_id`. Critically, `id` is typed `optional` (`id?: string`) even though the backend always returns it.

### 3.2 `CurrentUserInfo` missing `dev_mode_pat` and `pat` fields

**Backend** `/user-info` response (main.py lines 334-346, 361-372):
- Dev mode returns: `authenticated`, `user_id`, `email`, `display_name`, `is_superadmin`, `beta_access_status`, `memberships`, `beta_access_admin`, `llm_features_enabled`, **`dev_mode_pat`** (the raw token string).
- PAT auth returns same set plus a **`pat`** object.

**Dashboard** `CurrentUserInfo` interface (`authService.ts`, lines 14-22):
```ts
interface CurrentUserInfo {
  authenticated: boolean; user_id?: string; email?: string; display_name?: string;
  is_superadmin?: boolean; beta_access_status?: ...; beta_access_admin?: boolean;
  memberships?: OrganizationMembership[]; llm_features_enabled?: boolean;
}
```
`dev_mode_pat` and `pat` are absent from the TS interface. The `dev_mode_pat` token is never forwarded for use in the dashboard's dev auth flow (the dashboard uses header shims via `devMode.ts` instead).

### 3.3 `OrganizationMembership` has `organization_name` in dashboard but inconsistently populated by backend

**Dashboard** `OrganizationMembership` (`authService.ts`, line 6):
```ts
export interface OrganizationMembership { id?: string; organization_id: string; organization_name?: string; role?: string; can_read?: boolean; can_write?: boolean; }
```

**Backend** `get_user_memberships` (`auth.py`, line 223) does include `organization_name`. However, the `memberships` returned via `get_current_user_context` (used by most endpoints) may use a cached dict that was built earlier, where some code paths construct the membership dict without joining the `Organization` table and omit the name. The dashboard marks `organization_name` as optional (`?`) which handles this gracefully, but the inconsistency means the switcher dropdown can show blank names.

### 3.4 `agentService.getAgents` expects paginated response, backend returns array

**Dashboard** `agentService.getAgents` (line 36-39):
```ts
if (data && Array.isArray(data.items)) return data as PaginatedAgents;
if (Array.isArray(data)) return { items: data } as PaginatedAgents;
```
The backend `GET /agents/` (`agents.py`, line 93) is declared `response_model=List[schemas.Agent]` — it returns a flat array, not a paginated object. The dashboard has a defensive dual-path to handle both. The `PaginatedAgents.total_items` is always `undefined` in practice since the backend never returns it for this endpoint.

### 3.5 Dashboard calls `/memory-blocks/merge` which does not exist in the backend

**Dashboard** `memoryService.mergeMemoryBlocks` (line 175):
```ts
const resp = await apiFetch('/memory-blocks/merge', { method: 'POST', ... });
```
No such route exists anywhere in the backend routers. This will 404 silently (the response is passed through `jsonOrThrow` which will throw `HTTP error 404`).

### 3.6 Dashboard calls `/memory-blocks/{id}/suggest-keywords` which does not exist

**Dashboard** `memoryService.suggestKeywords` (line 158):
```ts
const resp = await apiFetch(`/memory-blocks/${memoryBlockId}/suggest-keywords`, { method: 'POST', ... });
```
No such route exists in the backend. Returns 404. The backend's nearest equivalent is the bulk `POST /memory-blocks/bulk-generate-keywords`.

### 3.7 MCP `AdvancedSearchPayload.search_type` includes `'basic'` but handler ignores it

`AdvancedSearchPayload.search_type` is typed as `'basic' | 'fulltext' | 'semantic' | 'hybrid'` in `MemoryServiceClient.ts` (line 58). The `advanced_search_memories` handler in `index.ts` (line 653) uses `st !== 'fulltext'` and `st !== 'semantic'` then falls through to `searchHybrid` — a `search_type` of `'basic'` silently becomes a hybrid search call. The backend `search/` endpoint supports `basic`, but the MCP `advanced_search` tool bypasses it entirely.

### 3.8 `notifications` `metadata` field naming collision

**Backend** `Notification` Pydantic schema (`notifications.py`, line 37): field is named `metadata`.
**SQLAlchemy model**: column is named `metadata_json` (the `metadata` name conflicts with SQLAlchemy's reserved mapper attribute).

The `notifications.py` API handler manually patches the attribute at runtime: `setattr(n, 'metadata', getattr(n, 'metadata_json', None))`. This works but is fragile — it is repeated in three handler functions (lines 48, 104, and indirectly in `adapted_recent`). If a future handler forgets the patch, `metadata` will serialize as `null`.

---

## 4. Type-Safety Gaps

| Location | Issue | Severity | Fix Direction |
|----------|-------|----------|---------------|
| `main.py:458–704` (prune, compress, bulk-* handlers) | Request bodies typed `request: dict` / `request: dict = None`. No Pydantic models. No auth dependency. | High | Add Pydantic `RequestModel` for each; add `Depends(get_current_user_context_or_pat)` |
| `main.py:305` (`/user-info`) | Returns bare `dict` — no `response_model`. Callers cannot rely on schema validation. | Medium | Define and add a `UserInfoResponse` Pydantic model |
| `orgs.py` (all `@router.get/post/put/delete` except invitations) | No `response_model` — routes return dicts directly. FastAPI skips validation and filtering. | Medium | Add `response_model` or at least `response_model=None` with documented shape |
| `consolidation.py:29` (`/consolidation/trigger/`) | No auth dependency. Any unauthenticated caller can trigger LLM consolidation. | High | Add `Depends(get_current_user_context_or_pat)` |
| `consolidation.py:325` (`DELETE /consolidation-suggestions/{id}`) | No auth dependency, no permission check. Any caller can hard-delete suggestions. | High | Add auth dep and permission check |
| `memory_optimization.py:304` (`GET …/preview`) | No auth dependency, no `scoped` dep, no scope enforcement. Returns stub data. | Low | Add `Depends(get_scoped_user_and_context)` for consistency |
| `index.ts:413` (MCP tool handler) | `typedArgs: Record<string, any>` — all arguments are `any` after the initial dispatch branch. Type guards validate but do not narrow. | Medium | Use discriminated type after guard; use `unknown` and narrow |
| `MemoryServiceClient.ts:114` (`whoAmI`) | Returns `Promise<any>` — response not typed. | Low | Add `UserInfoResponse` interface matching backend shape |
| `MemoryServiceClient.ts:207–219` (search methods) | Returns `MemoryBlock[]` but backend sends `MemoryBlockWithScore[]` (extra fields `search_score`, `search_type`, `rank_explanation`). Types lie. | Medium | Add `MemoryBlockWithScore` interface extending `MemoryBlock` |
| `memoryService.ts` (most methods) | `resp.json()` cast to no type — callers use `any`. `createMemoryBlock`, `updateMemoryBlock`, etc. return untyped `any`. | Medium | Generic typed wrapper, e.g., `jsonOrThrow<T>` |
| `bulk_operations.py:267–276` | Duplicate `GET /bulk-operations/admin/operations/{id}` shadows superadmin handler at line 350. The typed endpoint is unreachable. | High | Remove the always-403 stub route or merge logic |

---

## 5. Test Coverage Map

Integration test root: `/home/jean/git/hindsight-mbse/apps/hindsight-service/tests/integration/`
Unit test root: `/home/jean/git/hindsight-mbse/apps/hindsight-service/tests/unit/`

| Route / Group | Has Integration Test | Notes |
|---------------|---------------------|-------|
| `GET /user-info` | Yes (unit: `test_main_user_info.py`, `test_bulk_ops_api_smoke.py`) | dev mode and PAT paths tested |
| `GET /conversations/count` | Yes (`test_main_endpoints.py:141`) | |
| `POST /memory/prune/suggest` | Yes (`test_main_endpoints.py:194`) | LLM disabled path only (503) |
| `POST /memory/prune/confirm` | Yes (`test_main_endpoints.py:215`) | |
| `POST /memory-blocks/{id}/change-scope` | Yes (`test_main_scope_change_coverage.py`, `test_scope_changes_audit.py`) | Multiple permission scenarios |
| `POST /memory-blocks/{id}/compress` | Yes (`test_compression_api.py`, `test_final_80_percent_push.py`) | LLM disabled path |
| `POST /memory-blocks/{id}/compress/apply` | Partial (`test_compression_api.py` tests compress but not apply directly) | Apply path not explicitly tested |
| `POST /memory-blocks/bulk-generate-keywords` | Yes (`test_main_endpoints.py:274`, `test_coverage_boost.py`) | |
| `POST /memory-blocks/bulk-apply-keywords` | Yes (`test_main_endpoints.py:296`) | |
| `POST /memory-blocks/bulk-compact` | Yes (`test_main_endpoints.py:356`) | LLM disabled path (503) |
| `GET /memory-blocks/search/fulltext` | Yes (`test_main_endpoints.py:329`, `test_scope_utils_coverage.py:215`, `test_search_api.py`) | |
| `GET /memory-blocks/search/semantic` | Yes (`test_main_endpoints.py:335`, `test_scope_utils_coverage.py:221`) | |
| `GET /memory-blocks/search/hybrid` | Yes (`test_main_endpoints.py:341`, `test_scope_utils_coverage.py:227`) | |
| `GET /health` | Implicit (used as liveness probe, not directly tested in suite) | |
| `POST /memory-blocks/` | Yes (integration/memory_blocks/) | |
| `GET /memory-blocks/` | Yes | |
| `GET /memory-blocks/archived/` | Yes | |
| `GET /memory-blocks/search/` | Yes (via `test_search_api.py`) | |
| `GET /memory-blocks/{id}` | Yes | |
| `PUT /memory-blocks/{id}` | Yes | |
| `DELETE /memory-blocks/{id}` | Yes | |
| `DELETE /memory-blocks/{id}/hard-delete` | Yes | |
| `POST /memory-blocks/{id}/archive` | Yes | |
| `POST /memory-blocks/{id}/feedback/` | Yes | |
| `GET /memory-blocks/{id}/keywords/` | Yes | |
| `POST/DELETE /memory-blocks/{id}/keywords/{kw_id}` | Yes | |
| Agents CRUD | Yes (integration/agents/) | |
| `POST /agents/{id}/change-scope` | Yes (`test_scope_changes_audit.py`) | |
| Keywords CRUD | Yes (integration/keywords/) | |
| Organizations CRUD + members | Yes (unit: `test_orgs_endpoints_simple.py`, `test_organization_access_control.py`) | |
| Invitations lifecycle | Yes (`test_org_invitations_api_smoke.py`) | |
| `GET /audits/` | Partial (unit smoke tests, no dedicated integration test) | |
| `POST /consolidation/trigger/` | Yes (consolidation integration tests) | |
| Consolidation suggestions CRUD | Yes (`test_consolidation_scoping_api.py`, `test_consolidation_suggestions.py`) | |
| `DELETE /consolidation-suggestions/{id}` | Partial (no dedicated test for unauthorized delete) | Auth gap not tested |
| Bulk operations (org-level) | Yes (integration/bulk_operations/) | |
| `GET /bulk-operations/admin/operations/{id}` (superadmin) | No — shadowed by always-403 stub, effectively untestable | Dead route |
| Notifications CRUD + preferences | Yes (unit: `test_notifications_api_smoke.py`) | |
| `/users/me` (PATCH) | Indirect via user info tests | |
| PAT lifecycle (`/users/me/tokens/*`) | Yes (unit: `test_token_api.py`, `test_pat_dependency.py`) | |
| `GET /build-info` | Yes (unit: `test_support_build_info.py`) | |
| `POST /support/contact` | Yes (unit: `test_support_endpoints.py`, `test_support_rate_limit.py`) | |
| Beta access endpoints | Yes (unit: `test_beta_access.py`) | |
| `GET /memory-optimization/suggestions` | Yes (`test_memory_optimization.py`) | |
| `POST /memory-optimization/suggestions/{id}/execute` | Yes (`test_memory_optimization.py`) | |
| `GET /memory-optimization/suggestions/{id}/preview` | Yes (stub response tested) | |
| `/memory-blocks/merge` (dashboard-only) | N/A — endpoint does not exist in backend | |
| `/memory-blocks/{id}/suggest-keywords` (dashboard-only) | N/A — endpoint does not exist in backend | |

---

## 6. Cross-Cutting Concerns

### 6.1 Authorization Header Handling

Two auth credential mechanisms coexist:

1. **oauth2-proxy headers** — `X-Auth-Request-User`, `X-Auth-Request-Email` (preferred), `X-Forwarded-User`, `X-Forwarded-Email` (fallback). Set by a Traefik/oauth2-proxy sidecar. Resolved in `core/api/auth.py:resolve_identity_from_headers`.

2. **Personal Access Tokens (PAT)** — Either `Authorization: Bearer hsp_<token>` or `X-API-Key: hsp_<token>`. Validated in `core/api/deps.py:get_current_user_context_or_pat` via HMAC verification (`core/utils/token_crypto.py`).

The `get_current_user_context` dep (used by orgs, audits, notifications, bulk-ops, support, beta-access, users) accepts **only** oauth2-proxy headers — it does not fall back to PAT auth. PAT holders cannot use most management endpoints (organizations, notifications, etc.).

The `get_current_user_context_or_pat` dep accepts both, with PAT taking priority if an `Authorization` or `X-API-Key` header is present.

### 6.2 `X-Active-Scope` and `X-Organization-Id` Propagation

**Backend middleware** (`main.py:144–174`): For write operations on `/agents`, `/keywords`, `/memory-blocks`, `/consolidation`, `/consolidation-suggestions/`, the middleware rejects requests that lack `X-Active-Scope` (or `scope` query param), **unless** a PAT is present (PAT bypasses the middleware check). For org-scoped writes, `X-Organization-Id` (or `organization_id` query param) is also required.

**Dashboard** (`http.ts:107–153`): `apiFetch` automatically injects `X-Active-Scope` and `X-Organization-Id` headers from `sessionStorage.getItem('ACTIVE_SCOPE')` and `sessionStorage.getItem('ACTIVE_ORG_ID')` for all requests (read and write). Guest mode forces `scope=public`. The `noScope` option suppresses injection.

**MCP client** (`MemoryServiceClient.ts:104–109`): Sets `X-Active-Scope` and `X-Organization-Id` as static Axios headers at construction time from `HINDSIGHT_ACTIVE_SCOPE` and `HINDSIGHT_ORGANIZATION_ID` env vars. Scope cannot change per-request.

**Gap:** `getConsolidationSuggestions` in `memoryService.ts` (lines 141-142) reads scope from `sessionStorage` and adds it as **query params** only (`params.set('scope', scope)`), not as headers. The backend middleware checks both, so this works. However, `validateConsolidationSuggestion` and `rejectConsolidationSuggestion` call `apiFetch` without `noScope`, relying on the automatic header injection. This is correct but the inconsistency (explicit QP for GET, auto-header for POST) is fragile.

### 6.3 Scope Enforcement in the Database Layer

`core/db/scope_utils.py` provides `apply_scope_filter(query, current_user, model)` used by CRUD functions. It enforces:
- `visibility_scope = 'public'` always visible
- `visibility_scope = 'personal'` AND `owner_user_id = current_user.id` for non-superadmins
- `visibility_scope = 'organization'` AND `organization_id IN user_orgs`
- Superadmin sees all

The `get_scoped_user_and_context` dependency (used by most list/get endpoints) builds a `ScopeContext` from the request scope headers, which is then passed down to CRUD functions for optional **narrowing** (via `apply_optional_scope_narrowing`). The narrowing is additive — a request for organization scope with a specific org_id will further restrict the base access filter.

### 6.4 CORS

Configured in `main.py:83–97`:
```
allow_origins = [
  "http://localhost", "http://localhost:3000", "http://localhost:8000",
  "https://app.hindsight-ai.com", "https://app-staging.hindsight-ai.com"
]
allow_credentials = True, allow_methods = ["*"], allow_headers = ["*"]
```
The wildcard `allow_headers` means `X-Active-Scope`, `X-Organization-Id`, `X-API-Key`, and `X-CSRF-Token` are all permitted. `allow_credentials=True` with `allow_origins` (not `*`) is correct for cookie-based auth.

### 6.5 `orgs_fixed.py` Dead Code

`/home/jean/git/hindsight-mbse/apps/hindsight-service/core/api/orgs_fixed.py` defines a full duplicate organizations router (including at least `POST /` and several members endpoints). It is **never imported or included** in `app.py` or `main.py`. It should be removed to avoid maintenance confusion.

### 6.6 `notifications` `metadata`/`metadata_json` impedance mismatch

Pydantic schema uses `metadata` (Python reserved-word avoidance issue — SQLAlchemy's declarative base also reserves `.metadata`). The DB column is `metadata_json`. The API layer patches the attribute at runtime in three places. This is a persistent tech-debt item that creates silent failures if any new notification handler forgets the patch.

---

## Summary

**Total HTTP route count: 82** across 13 router files/groups  
**Total MCP tool count: 11**

**Top 3 contract drift issues:**

1. **Two non-existent backend endpoints called by dashboard**: `/memory-blocks/merge` and `/memory-blocks/{id}/suggest-keywords` will 404 silently. Users clicking "Merge" or "Suggest Keywords" (single-block) receive an error. This is a complete feature break.

2. **`MemoryBlock` dashboard type is a 5-field stub** while the backend schema has 19+ fields. Code consuming `getMemoryBlockById` as `MemoryBlock` will not type-check fields like `feedback_score`, `lessons_learned`, `archived`, `conversation_id`. The MCP client's `MemoryBlock` type also misses scored-search fields returned by the typed search endpoints.

3. **PAT scope bypass in `advanced_search_memories`**: The MCP tool routes `search_type='basic'` to `searchHybrid` silently. More significantly, all three advanced search backend endpoints in `main.py` perform manual auth resolution (30+ lines per endpoint) duplicating the logic in `get_current_user_context_or_pat`. These duplicated resolvers do not enforce `ensure_pat_allows_read` and do not call `get_scoped_user_and_context`, meaning PAT organization restrictions are partially enforced but scope narrowing (the additional `apply_optional_scope_narrowing` step) is skipped for these three endpoints.

**One question for the interface view:**  
The `GET /bulk-operations/admin/operations/{id}` superadmin handler is unreachable due to the earlier always-403 stub route shadowing it — was this intentional (temporarily disabling the endpoint) or an accidental registration order? The MBSE interface model should document whether this endpoint is active or not.

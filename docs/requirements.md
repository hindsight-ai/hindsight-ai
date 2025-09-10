# Hindsight AI — Product & Technical Requirements

This document specifies the expected behavior, constraints, and operational requirements of the Hindsight AI application across environments (staging, product4) From any app page (e.g., `/memory-blocks`), top‑right "Sign In" goes directly to Google and returns to the same page authenticated.
5) After successful OAuth, the same tab shows authenticated state without opening a new tab.
6) **Organization Management**: Authenticated users can access organization management through the user account dropdown menu:
   - **"Manage Organizations"** menu item opens a modal dialog with organization and member management
   - **Create Organizations**: Users can create new organizations with name and optional slug
   - **View Organizations**: Lists all organizations the user has access to (superadmin sees all)
   - **Member Management**: For each organization, users can view, add, update, and remove members
   - **Role Management**: Support for owner, admin, editor, viewer roles with appropriate permissions
   - **Self-Protection**: Users cannot remove themselves or change their own role
   - **Real-time Updates**: Changes are immediately reflected in the UI with success/error notifications
7) **Dev Mode Experience**: In local development, "Sign In" automatically authenticates as `dev@localhost` with superadmin privileges, enabling full testing of organization management features without OAuth setup.n, local). It is the single source of truth for functionality, routing/auth flows, deployment, runtime configuration, and acceptance criteria.

Roadmap Reference
- Execution ordering, phased delivery plan, and acceptance criteria for in-progress governance & UX work are tracked in `docs/roadmap.md`. This requirements file defines the target state; the roadmap file defines how we get there iteratively.

## 1. Scope & Goals
- Provide a secure web UI to manage AI Agent memories and related operations.
- Ensure environment parity and safe deployments with minimal drift.
- Support authenticated usage via Google OAuth (through oauth2-proxy) and a read‑only Guest Mode.

## 2. Stakeholders
- Product owner: sets functional priorities.
- Engineers: implement and operate the system (backend, frontend, DevOps).
- Operators: manage infrastructure, DNS, certificates, and secrets.

## 3. Glossary
- Dashboard: Frontend React/Vite UI (served by Nginx).
- Service/API: FastAPI backend (hindsight-service).
- oauth2-proxy: Reverse proxy handling Google OAuth and auth cookies.
- Traefik: Edge reverse proxy, TLS termination via Let’s Encrypt DNS‑01.
- GHCR: GitHub Container Registry for images.

## 4. Environments
- Production: branch `main`, environment name `production`.
- Staging: branch `staging`, environment name `staging`.
- Local development: docker compose or `vite dev` + API.

A single compose file `docker-compose.app.yml` is used for both staging and production, parameterized by `.env` on the server.

### 4.1 Local Development Authentication
In local development mode, the system provides a simplified authentication mechanism:
- **Dev Authentication**: Click "Sign In" button automatically authenticates as `dev@localhost`
- **Full Permissions**: Dev user has superadmin privileges and can access all features
- **Organization Management**: Dev user can create, manage organizations and memberships through the user menu
- **Production Parity**: Same permission logic as production, just bypasses OAuth flow
- **Dev Mode Indicators**: UI shows "Development Mode" status and admin badge
- **Simplified Logout**: In dev mode, logout redirects to home page instead of OAuth logout flow

## 5. Secrets & Configuration
All secrets are environment‑scoped in GitHub Environments. Use the same key names for both envs; values differ per env.

Required secrets (per env):
- SSH: `SSH_HOST`, `SSH_USERNAME`, `SSH_KEY`, `SSH_PORT`.
- Domains: `APP_HOST` (e.g., app.hindsight-ai.com or app-staging.hindsight-ai.com), `TRAEFIK_DASHBOARD_HOST`.
- TLS/ACME: `ACME_EMAIL`, `CLOUDFLARE_DNS_EMAIL`, `CLOUDFLARE_DNS_API_TOKEN`.
- App/API: `API_URL` (recommended: `/api`), `AUTHORIZED_EMAILS_CONTENT` (newline separated).
- OAuth: `OAUTH2_PROXY_CLIENT_ID`, `OAUTH2_PROXY_CLIENT_SECRET`, `OAUTH2_PROXY_COOKIE_SECRET`.
- DB: `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- LLM: `LLM_API_KEY`, `LLM_MODEL_NAME`.
- Tuning: `CONSOLIDATION_BATCH_SIZE`, `FALLBACK_SIMILARITY_THRESHOLD`.

Runtime env (set in server `.env` by the workflow):
- `HINDSIGHT_SERVICE_IMAGE`, `HINDSIGHT_DASHBOARD_IMAGE` (GHCR digests/tags).
- `APP_HOST`, `TRAEFIK_DASHBOARD_HOST`, `HINDSIGHT_SERVICE_API_URL`.
- Backend build meta: `BACKEND_BUILD_SHA`, `FRONTEND_BUILD_SHA`, `BUILD_TIMESTAMP` (informational).

## 6. Deployment Pipeline
- Trigger: push to `main` or `staging`.
- Jobs:
  - Build & push backend image to GHCR.
  - Build & push dashboard image to GHCR.
  - Deploy job (dynamic environment selection; concurrency per branch to avoid overlap).
- Deploy steps (remote host):
  - Copy `docker-compose.app.yml`, `config/`, `templates/`, `letsencrypt/`.
  - Write server `.env` with environment secrets.
  - Replace ACME email placeholder in Traefik config.
  - Authenticate to GHCR, `docker compose pull`, `up -d`.
  - Health check: containers stay Up; logs printed on failure.
- Remote directories:
  - Production: `~/hindsight-ai-production`
  - Staging: `~/hindsight-ai-staging`

## 7. Networking, DNS, TLS
- DNS: `APP_HOST` and `TRAEFIK_DASHBOARD_HOST` point to their respective servers.
- TLS: Traefik obtains certs via Let’s Encrypt DNS‑01 using Cloudflare API.
- Universal SSL limitation: avoid two‑level subdomains like `app.staging.domain`; use single level such as `app-staging.domain` unless you manage a delegated sub‑zone or advanced cert.

## 8. Reverse Proxy & Routing
- Traefik terminates TLS and routes:
  - Dashboard: `Host(${APP_HOST})` → Nginx (dashboard).
  - OAuth paths: `/oauth2/*` to oauth2-proxy.
  - API via oauth2-proxy for app host: `/api` → oauth2-proxy → Nginx → backend.
- Nginx (dashboard container):
  - Proxies `/api/` to backend with auth headers forwarded.
  - Proxies `/guest-api/` to backend without auth headers.
  - Serves SPA with fallback to `index.html`.
  - Serves `/env.js` with `Cache-Control: no-store`.

## 9. Frontend Runtime Configuration
- Single image for all envs with runtime configuration via `env.js` (generated at container start from `HINDSIGHT_SERVICE_API_URL`).
- Build metadata passed as Vite vars: `VITE_VERSION`, `VITE_BUILD_SHA`, `VITE_BUILD_TIMESTAMP`, `VITE_DASHBOARD_IMAGE_TAG` (shown in About dialog).

## 10. Authentication & Authorization
- Identity provider: Google OAuth via oauth2-proxy.
- Cookie domain: `.hindsight-ai.com` (works for staging and production).
- Backend requires auth for mutating operations; unauthenticated POST/PUT/PATCH/DELETE return 401 with a guest‑mode message.
- Guest mode: UI allows read‑only exploration when enabled.

### 10.1 Login & Guest Flow (Authoritative)
- Routes:
  - `/login`: dedicated full‑screen login page.
  - `/dashboard`: main app dashboard route.
  - `/`: trampoline — if authenticated, redirect to `/dashboard`; else if not in guest mode, redirect to `/login`.
- Header “Sign In” button (top‑right):
  - Goes directly to `/oauth2/sign_in?rd=<current_path>` (no stop at `/login`).
- Login page “Sign In” button:
  - Clears guest mode if set, and goes to `/oauth2/sign_in?rd=/dashboard`.
- Login page “Explore as Guest” button:
  - Enables guest mode and navigates to `/dashboard`.
- After OAuth callback:
  - The app checks `/api/user-info` (never the guest endpoint). If authenticated, guest mode is cleared and the app renders authenticated state in the same tab.
- Unauthenticated fetch to `/api/user-info` may 302 to Google; the UI treats it as “not authenticated” and redirects to `/login` (no crash).

### 10.3 Edge-Case Rules
- Do not auto-redirect to `/login` on any `/oauth2/*` paths (allow direct navigation to oauth2-proxy).
- In guest mode, clicking Sign In does not clear guest pre-redirect; guest is cleared automatically after a successful auth check.

### 10.2 CORS & Security Headers
- Same‑origin allowed automatically by Nginx (origin equals `$scheme://$host`).
- `/env.js` caching disabled.
- OAuth2‑proxy headers forwarded to backend for identity (`X-Auth-Request-*` and `X-Forwarded-*`).

## 11. Backend API Expectations
The backend exposes a FastAPI application with the following expectations:

- General
  - Health: `GET /health` returns `{ status: "ok", service: "hindsight-service" }`.
  - Auth reflection: `GET /user-info` returns `{ authenticated, user, email }` based on oauth2-proxy headers in production; returns a fake dev user locally.
  - Conversations KPI: `GET /conversations/count` returns `{ count }` of unique conversations.
- Agents
  - `POST /agents/` create (unique `agent_name`).
  - `GET /agents/` list (pagination via `skip`, `limit`).
  - `GET /agents/{agent_id}` details.
  - `GET /agents/search/?query=…` simple search.
  - `DELETE /agents/{agent_id}` delete.
- Memory Blocks
  - `GET /memory-blocks/` list with filters:
    - `agent_id`, `conversation_id`, `search_query`, `start_date`, `end_date`, `min/max_feedback_score`, `min/max_retrieval_count`, `keywords` (comma‑separated UUIDs), `sort_by`, `sort_order`, `skip`, `limit`, `include_archived`.
  - `POST /memory-blocks/` create (requires existing agent).
  - `GET /memory-blocks/{id}` details.
  - `PUT /memory-blocks/{id}` update.
  - `POST /memory-blocks/{id}/archive` soft-archive; `DELETE /memory-blocks/{id}/hard-delete` hard delete.
  - Feedback: `POST /memory-blocks/{id}/feedback/` with `{ feedback_type, feedback_details }`.
- Keywords
  - `POST /keywords/`, `GET /keywords/`, `GET /keywords/{id}`, `PUT /keywords/{id}`, `DELETE /keywords/{id}`.
  - Associations: `POST /memory-blocks/{id}/keywords/{keyword_id}` and `DELETE` for removal.
- Pruning
  - `POST /memory/prune/suggest` with `{ batch_size, target_count, max_iterations }` → suggestion payload.
  - `POST /memory/prune/confirm` with `{ memory_block_ids: [...] }` → archive counts.
- Compression (LLM)
  - `POST /memory-blocks/{id}/compress` with optional `{ user_instructions }` → suggestion payload; requires `LLM_API_KEY`.
  - `POST /memory-blocks/{id}/compress/apply` with `{ compressed_content, compressed_lessons_learned }` → updated memory block.
- Keyword Generation (Bulk)
  - `POST /memory-blocks/bulk-generate-keywords` with `{ memory_block_ids: [...] }` → suggestion set.
  - `POST /memory-blocks/bulk-apply-keywords` with `{ applications: [...] }` → results.
- Search
  - Full-text: `GET /memory-blocks/search/fulltext` with `query`, `limit`, optional filters.
  - Semantic (placeholder): `GET /memory-blocks/search/semantic` with `query`, `similarity_threshold`.
  - Hybrid: `GET /memory-blocks/search/hybrid` with weighted params; validates weights sum to 1.0.
- Organizations
  - `GET /organizations/` list organizations for current user (superadmin sees all)
  - `POST /organizations/` create new organization with `{ name, slug }` (creator becomes owner)
  - `GET /organizations/{org_id}` get organization details
  - `PUT /organizations/{org_id}` update organization name/slug (requires owner/admin role)
  - `DELETE /organizations/{org_id}` delete organization (requires owner role)
  - `GET /organizations/{org_id}/members` list organization members
  - `POST /organizations/{org_id}/members` add member with `{ email, role, can_read, can_write }`
  - `PUT /organizations/{org_id}/members/{user_id}` update member role/permissions
  - `DELETE /organizations/{org_id}/members/{user_id}` remove member from organization

Access control
- Read-only enforcement for unauthenticated POST/PUT/PATCH/DELETE via ASGI middleware (checks oauth2-proxy headers).
- Guest consumers must use `/guest-api` proxy in the dashboard, which strips auth headers.
- Organization management requires authentication and appropriate role permissions (owner/admin for most operations).

## 12. Non‑Functional Requirements
- Parity: same container images for staging and production (runtime config only).
- Availability: dashboard, backend, oauth2‑proxy, traefik remain Up after deploy health check.
- Observability: basic container logs visible in CI on failure.
- Security: secrets never baked into images; all secret values come from environment.
- Performance: dashboard loads without blocking on cross‑origin OAuth redirect attempts.

## 13. Local Development Requirements
- Compose dev: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build`
  - Dashboard at `http://localhost:3000`, API at `http://localhost:8000`.
  - Vite dev proxy forwards `/api` and `/guest-api` to `http://localhost:8000`.
- Standalone dev: `npm run dev` in dashboard, `uvicorn` for backend.

### 13.1 Frontend Dev
- Vite dev server: `npm run dev` in `apps/hindsight-dashboard`.
- Runtime config: `public/env.js` provides defaults for dev; for custom API, set `VITE_HINDSIGHT_SERVICE_API_URL` in `.env.local`.
- Dev proxy (vite.config.js): `/api` and `/guest-api` → `http://localhost:8000`.
- Entry points: `src/main.jsx`, `src/App.jsx`.

### 13.2 Backend Dev
- Uvicorn: `uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000` from `apps/hindsight-service`.
- Database: Postgres 13 via compose; migrations via Alembic (auto-run in container at startup per scripts).
- Env vars: `DATABASE_URL`, `LLM_API_KEY`, `LLM_MODEL_NAME` minimal for full feature coverage.

### 13.3 Docker Compose Dev
- Override file `docker-compose.dev.yml` exposes DB (5432), API (8000), Dashboard (3000) and enables `develop.watch` for hot rebuild.
- Use `./start_hindsight.sh --watch` for watch mode (Compose v2.21+).

## 14. Acceptance Criteria (Key Scenarios)
1) First visit (unauthenticated) to `/` redirects to `/login`.
2) On `/login`, clicking “Sign In” sends user to Google and returns to `/dashboard` authenticated.
3) On `/login`, clicking “Explore as Guest” navigates to `/dashboard` with guest badge and write actions blocked.
4) From any app page (e.g., `/memory-blocks`), top‑right “Sign In” goes directly to Google and returns to the same page authenticated.
5) After successful OAuth, the same tab shows authenticated state without opening a new tab.
6) Switching environments uses the same dashboard image with a different runtime `HINDSIGHT_SERVICE_API_URL`.
7) Certificates are issued successfully for `APP_HOST` and `TRAEFIK_DASHBOARD_HOST`; no literal `${...}` placeholders appear in Traefik logs.
8) CI prevents overlapping deploys per branch (concurrency), and staging deploys never affect production.

## 15. Risks & Mitigations
- OAuth redirect mismatch: ensure Google Cloud OAuth has `https://<APP_HOST>/oauth2/callback` for both envs.
- DNS wildcard limitations: prefer single‑level subdomains (e.g., `app-staging.domain`).
- Browser caching: hard refresh after deploy if UI changes appear inconsistent.

## 16. Change Management
- All changes flow via PRs/branch pushes to `staging` or `main`.
- This document must be updated when routes, auth flows, secrets, or deploy steps change.

---
Last updated: manual

## 17. Frontend Application Shell & Layout
- Layout structure:
  - Fixed left sidebar that never scrolls with page content (positioned fixed; app content accounts for its width).
  - Top header within main content contains page title, scale selector, guest badge (when applicable), and user account button.
  - Main content area scrolls independently (internal scroll container), preserving the fixed sidebar and header positions.
- Responsive behavior:
  - Sidebar collapsible; collapsed width ~16 (Tailwind) vs expanded ~64.
  - Mobile: hamburger button toggles sidebar visibility.
  - Content scale control in header with presets 100%, 75%, 50%; persisted in `localStorage` (`UI_SCALE`).
- Notifications:
  - Global notification container overlays messages (success/info/warning/error).
  - 401 helper shows a persistent prompt with a “refresh auth” action linking to `/oauth2/sign_in?rd=<current>`.
- Guest badge:
  - When in guest mode, header shows “Guest Mode · Read-only”.
  - All mutating actions are blocked with a warning via the notification service.

## 18. Routing Map & Navigation
- Routes:
  - `/login`: full-screen login page (standalone, no app layout).
  - `/dashboard`: default authenticated landing page.
  - `/`: trampoline → `/dashboard` (authenticated) or `/login` (unauthenticated and not guest).
  - `/memory-blocks` (+ detail `/:id`), `/keywords`, `/agents`, `/analytics`, `/consolidation-suggestions`, `/archived-memory-blocks`, `/pruning-suggestions`, `/memory-optimization-center`.
- Navigation:
  - Left sidebar items link to each top-level route; active state highlights current section.
  - Top-right account button: shows avatar initial; unauthenticated shows “Sign In” button.
  - Sign In in header goes directly to `/oauth2/sign_in?rd=<current_path>` (bypasses `/login`).
  - Sign Out redirects to `/oauth2/sign_out?rd=<origin>`.

## 19. Login & Guest Page UX (/login)
- Content:
  - Title, short description, two buttons: “Sign In” (primary) and “Explore as Guest”.
- Behavior:
  - Sign In: navigates to `/oauth2/sign_in?rd=/dashboard`.
  - Explore as Guest: sets session guest mode and navigates to `/dashboard`.
  - No app layout chrome; page fills viewport.

## 20. Dashboard Page (/dashboard)
- KPI cards:
  - Agents count, Memory Blocks count, Conversations count; click opens relevant pages.
  - Loading skeletons while data loads.
- Recent Memory Blocks:
  - List of latest entries with preview, tags, and quick actions.
  - Manual Refresh button updates lists and shows “Last updated”.
- Data sources:
  - Agents: GET `/agents/?limit=…`.
  - Memory blocks count: GET `/memory-blocks/?limit=…` (reads `total_items`).
  - Conversations: GET `/conversations/count`.

## 21. Memory Blocks Page (/memory-blocks)
- Filters & search:
  - Search term, agent filter, conversation filter; synced to URL query (`search`, `agent`, `conversation`).
  - Pagination: `page` query param; page size default 12.
  - Sorting: by `created_at desc`.
- Cards grid:
  - Responsive grid (1/2/3 columns by breakpoint) of memory blocks.
  - Actions per card: View (opens detail modal), Archive, Delete, Suggest Keywords, Compact Memory.
  - Guest mode blocks all mutating actions with clear warnings.
- Pagination controls:
  - Previous/Next buttons; display of range and total.
- Modals:
  - Detail modal: fetches by ID; shows full content, metadata, actions.
  - Compaction modal: runs LLM-driven compression (`POST /memory-blocks/{id}/compress`) and apply (`POST /memory-blocks/{id}/compress/apply`).
- Empty/error states:
  - Clear filters CTA when filters active; Create Memory Block CTA otherwise.

## 22. Keywords Management (/keywords)
- Capabilities:
  - List keywords (GET `/keywords/`).
  - Create, update, delete keywords (POST/PUT/DELETE routes).
  - Associate/disassociate keywords with memory blocks (POST/DELETE `/memory-blocks/{id}/keywords/{keyword_id}`).
  - Suggestions: bulk suggest and apply keywords for selected memory blocks.
- UI:
  - Table/list of keywords with counts/usage; modals for add/edit; bulk apply flows with progress feedback.

## 23. Agents Management (/agents)
- Capabilities:
  - List agents, search, create, delete (GET/POST/DELETE).
- UI:
  - Table/list with search field and add agent modal.

## 24. Consolidation Suggestions (/consolidation-suggestions)
- Capabilities:
  - List suggestions with statuses; view details; validate or reject.
- API:
  - GET `/consolidation-suggestions/` and `/{id}`; POST validate/reject endpoints.

## 25. Pruning Suggestions (/pruning-suggestions)
- Capabilities:
  - Generate pruning suggestions (batched, LLM-assisted) and confirm pruning (archives selected blocks).
- API:
  - POST `/memory/prune/suggest` with `{ batch_size, target_count, max_iterations }`.
  - POST `/memory/prune/confirm` with `{ memory_block_ids: [...] }`.

## 26. Memory Optimization Center (/memory-optimization-center)
- Capabilities:
  - Fetch optimization suggestions, execute selected suggestions, view details.
- API:
  - Under `/memory-optimization/*` (router included in backend), including list, execute, details.

## 27. Search
- Full-text search:
  - GET `/memory-blocks/search/fulltext?query=…&limit=…&include_archived=`.
- Semantic search (placeholder):
  - GET `/memory-blocks/search/semantic?query=…&similarity_threshold=…`.
- Hybrid search:
  - GET `/memory-blocks/search/hybrid?query=…&fulltext_weight=…&semantic_weight=…&min_combined_score=…`.

## 28. Data Model (High-level)
- Agent: `{ agent_id (UUID), agent_name, created_at, updated_at }`.
- MemoryBlock: `{ id (UUID), agent_id, conversation_id, timestamp, content, errors, lessons_learned, metadata(JSON), feedback_score, retrieval_count, archived, archived_at, created_at, updated_at, search_vector, content_embedding }`.
- FeedbackLog: `{ feedback_id, memory_id, feedback_type, feedback_details, created_at }`.
- Keyword: `{ keyword_id, keyword_text, created_at }`.
- MemoryBlockKeyword: join table `{ memory_id, keyword_id }`.
- ConsolidationSuggestion: `{ suggestion_id, group_id, suggested_content, suggested_lessons_learned, suggested_keywords(JSON), original_memory_ids(JSON), status, timestamp, created_at, updated_at }`.

## 29. Write-Access Enforcement & Headers
- Backend enforces read-only for unauthenticated requests across POST/PUT/PATCH/DELETE via ASGI middleware.
- oauth2-proxy passes identity headers and auth token to Nginx → backend:
  - X-Auth-Request-User, X-Auth-Request-Email, X-Auth-Request-Access-Token, Authorization.
- Backend accepts either `X-Auth-Request-*` or `X-Forwarded-*` identity headers on `/user-info`.

## 30. OAuth & Cookies
- oauth2-proxy configuration:
  - Provider: Google; Redirect URL: `https://<APP_HOST>/oauth2/callback`.
  - Upstream: dashboard container.
  - Cookie domain: `.hindsight-ai.com`; Secure; SameSite=Lax; reverse-proxy mode.
  - Skip auth: `/manifest.json`, `/favicon.ico`, `/guest-api/*`.
- Session persistence: cookie available on both staging and production due to shared eTLD+1.

## 31. Error Pages & Templates
- Custom 403 page (templates/error.html) for unauthorized emails with admin contact and sign-out.

## 32. Accessibility & UX Guidelines
- Keyboard focus maintained across modal open/close; ESC closes modals.
- Sufficient color contrast for critical elements; visible focus states on interactive elements.
- Loading states with skeletons where applicable to avoid layout shift.

## 33. Performance & Caching
- SPA assets under `/assets/` are immutable and cached for 1 year.
- `/env.js` is never cached and must be requested fresh at load.
- Avoid blocking UI on cross-origin OAuth redirects; handle as unauthenticated state.

## 34. Security & Privacy
- No secrets in frontend bundles; runtime config exposes only public endpoints.
- All cookies marked Secure and SameSite=Lax via oauth2-proxy.
- Restrictive CSRF policy on Nginx for mutating methods; same-origin permitted.

## 35. Operational Playbook (Staging/Production)
- Staging and production use the same images; config differs via `.env`.
- Concurrency ensures only one deploy per branch.
- To rotate oauth2-proxy cookies or client secrets: update environment secrets and redeploy.
- To reset Let’s Encrypt: set `recreate_acme_json` input to true on manual workflow dispatch.
- oauth2-proxy parameters (compose env):
  - `OAUTH2_PROXY_PROVIDER=google`
  - `OAUTH2_PROXY_REDIRECT_URL=https://<APP_HOST>/oauth2/callback`
  - `OAUTH2_PROXY_UPSTREAMS=http://hindsight-dashboard:80`
  - `OAUTH2_PROXY_COOKIE_SAMESITE=lax`, `OAUTH2_PROXY_COOKIE_SECURE=true`, cookie domain `.hindsight-ai.com`
  - `OAUTH2_PROXY_REVERSE_PROXY=true`, `OAUTH2_PROXY_SET_XAUTHREQUEST=true`, `OAUTH2_PROXY_PASS_ACCESS_TOKEN=true`, `OAUTH2_PROXY_SET_AUTHORIZATION_HEADER=true`
  - `OAUTH2_PROXY_SKIP_AUTH_ROUTES=/manifest.json$,/favicon.ico$,^/guest-api/.*`
  - `OAUTH2_PROXY_AUTHENTICATED_EMAILS_FILE=/etc/oauth2-proxy/authorized_emails.txt`
  - `OAUTH2_PROXY_LOGOUT_REDIRECT_URL=https://accounts.google.com/Logout`

Traefik labels:
- Dashboard router: `Host(${TRAEFIK_DASHBOARD_HOST})` → `api@internal` over `websecure` with `letsencrypt` resolver.
- OAuth routers: `Host(${APP_HOST}) && PathPrefix('/oauth2')` and `Host(${APP_HOST}) && PathPrefix('/api')` → `oauth2-proxy`.
- App router: `Host(${APP_HOST})` → dashboard (port 80).

# Hindsight AI — Product & Technical Requirements

This document specifies the expected behavior, constraints, and operational requirements of the Hindsight AI application across environments (staging, production, local). It is the single source of truth for functionality, routing/auth flows, deployment, runtime configuration, and acceptance criteria.

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

### 10.2 CORS & Security Headers
- Same‑origin allowed automatically by Nginx (origin equals `$scheme://$host`).
- `/env.js` caching disabled.
- OAuth2‑proxy headers forwarded to backend for identity (`X-Auth-Request-*` and `X-Forwarded-*`).

## 11. Backend API Expectations
- Exposes `/user-info` to reflect authenticated user.
- All read endpoints are accessible to guest (no auth headers required).
- All write endpoints require auth and return 401 if unauthenticated.
- Provides build info endpoint consumed by About dialog.

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


# ADR 0003: Traefik + oauth2-proxy + Nginx architecture

- Status: Accepted
- Date: 2025-09-07

## Context
We need TLS termination, OAuth with Google, and a simple way to serve the SPA and proxy the API with auth headers.

## Decision
Adopt an edge proxy (Traefik) with Let’s Encrypt DNS-01 via Cloudflare; route `/oauth2/*` and `/api` to `oauth2-proxy` in reverse-proxy mode; serve the SPA via Nginx and proxy `/api` (and `/guest-api`) to the backend.

## Consequences
- Clear separation of concerns: Traefik (TLS/routing), oauth2-proxy (auth), Nginx (static + local proxy), FastAPI (business logic).
- oauth2-proxy injects identity headers and sets secure cookies on `.hindsight-ai.com` for both envs.

## Alternatives Considered
- Traefik forward-auth plugin: tighter coupling, fewer off-the-shelf controls vs oauth2-proxy.
- Nginx-only with embedded OAuth: more config complexity and fewer standardized features.


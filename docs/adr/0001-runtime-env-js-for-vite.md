# ADR 0001: Runtime env.js for Vite dashboard

- Status: Accepted
- Date: 2025-09-07

## Context
The React/Vite dashboard originally baked environment variables at build time (e.g., API URL). This required building separate images for staging and production and made promotions slower and less reproducible. It also complicated local development when switching API targets.

## Decision
Use a small runtime `env.js` loaded before the app to expose public configuration via `window.__ENV__`. Generate it at container startup from `HINDSIGHT_SERVICE_API_URL`. In code, read runtime first, then fall back to `import.meta.env.VITE_*`, then to sensible defaults (e.g., `/api`).

## Consequences
- Same dashboard image (by commit SHA) serves all environments; runtime configuration supplies the API endpoint.
- Faster, safer promotions; strong staging→prod parity.
- Prevent caching issues: serve `/env.js` with `Cache-Control: no-store` and include a query param when referenced (e.g., `/env.js?v=1`).

## Alternatives Considered
- Build-time env only (rejected): separate images per env; slower promotions; more drift.
- Config JSON fetched at runtime: viable but adds async bootstrap and error handling.


# Hindsight Dashboard

![Hindsight Dashboard Screenshot](docs/2025-06-07_22-52-memory-dashboard.png)

A clean UI to browse, search, filter, archive and curate your agent’s memory blocks. Includes validation flows for consolidation suggestions and a pruning workflow.

## Features

- Memory browsing with rich filters (date, feedback score, retrieval count, keywords)
- Full‑view memory detail and keyword management
- Feedback actions (positive/negative/neutral)
- Archived view and bulk operations
- Consolidation suggestions review (validate/reject)
- Pruning suggestions review and confirm

## Run (recommended via Docker)

The root repository quickstart (`./start_hindsight.sh`) brings up the API, DB and dashboard. Then open http://localhost:3000.

## Run locally (without Docker)

Prereqs: Node 18+

```bash
cd apps/hindsight-dashboard
npm install
REACT_APP_HINDSIGHT_SERVICE_API_URL=http://localhost:8000 npm start
```

## Environment

- `REACT_APP_HINDSIGHT_SERVICE_API_URL`: base URL of the backend API

In production, access is protected by OAuth2‑Proxy (Google). For local dev, the API can expose a mock `/user-info` response when `DEV_MODE=true` in the backend.

## Scripts

- `npm start` — run dev server on port 3000
- `npm run build` — build static assets
- `npm test` — CRA test runner

Further screenshots and design notes are in `docs/`.

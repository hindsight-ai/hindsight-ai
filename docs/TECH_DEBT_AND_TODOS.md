# Tech Debt and Next Fixes

This document tracks known issues and small inconsistencies found during the README overhaul. These are intentionally not fixed in the current branch to keep changes focused. Use this as a checklist for a follow‑up branch.

## API/MCP Contract Mismatches

- MemoryBlock ID field name
  - API response: `id` (Pydantic schema `MemoryBlock.id`)
  - MCP client types: `memory_id` (see `mcp-servers/hindsight-mcp/src/client/MemoryServiceClient.ts`)
  - Action: pick one canonical name. Recommendation: use `id` everywhere (API + MCP), with client‑side mapping if needed.

- Feedback payload shape
  - API endpoint: `POST /memory-blocks/{memory_id}/feedback/` expects body matching `schemas.FeedbackLogCreate` with `memory_id` and `feedback_details`.
  - MCP tool/client: sends `{ memory_block_id, feedback_type, comment }`.
  - Action: standardize to `{ memory_id, feedback_type, feedback_details }` or add API aliasing for backward compatibility. Update MCP client accordingly.

- Metadata field naming
  - API models used `metadata_col`; MCP/UX typically says `metadata`.
  - Status: API now accepts `metadata` as an alias for `metadata_col` on create/update (no response rename yet).
  - Action: consider returning `metadata` in responses as well for consistency (or document the response field clearly).

## Backend Code Issues

- Search filter references a non‑existent column
  - File: `apps/hindsight-service/core/db/crud.py`
  - Issue: `models.MemoryBlock.external_history_link` is referenced but not defined in `models.py`.
  - Action: remove the filter or add the column to the model and migrations.

- Missing import in pruning service
  - File: `apps/hindsight-service/core/pruning/pruning_service.py`
  - Issue: uses `func.random()` without `from sqlalchemy import func`.
  - Action: add the missing import.

## Product/UX

- Copilot Assistant integration
  - Dev compose includes `hindsight-copilot-assistant` and it works; long‑term it should be integrated directly within the dashboard or linked clearly.
  - Action: decide integration point in the dashboard nav, or provide a launch link with shared auth context.

- Keyword extraction
  - Current implementation is stubbed. Consider spaCy, KeyBERT, or a lightweight ML option with stopword handling and lemmatization.

## Ops/Docs

- Migrations on fresh DB
  - Current Alembic chain may not apply cleanly on a blank database.
  - Action: fix the initial migration chain or provide a single baseline migration aligned with the live schema. For now, docs instruct restoring from the provided backup.

- Domain setup
  - Domains `dashboard.hindsight-ai.com` and `api.hindsight-ai.com` are final but require server deploy + Cloudflare + OAuth2 creds.
  - Action: add a short deployment checklist (Cloudflare DNS, Traefik config, OAuth2 Proxy client IDs, authorized emails).

## Nice‑to‑Have Enhancements

- API recipes doc with more complex filter/sort examples and pagination patterns.
- MCP result formatting improvements for readability (e.g., pretty‑printed summaries, truncation controls).
- Tests for consolidation/pruning flows with LLM off/on (mocked), and search performance.

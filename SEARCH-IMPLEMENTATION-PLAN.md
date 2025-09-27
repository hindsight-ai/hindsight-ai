# Search Infrastructure Foundation Plan

## Goals
- Consolidate the agent-facing `GET /memory-blocks/search/` endpoint onto `SearchService` so keywords/basic search use the same pipeline as enhanced endpoints.
- Preserve current behaviour (keyword search default) while enabling explicit strategy selection (`basic`, `fulltext`, `hybrid`).
- Enforce visibility scope filtering and agent/conversation constraints consistently for all strategies.
- Instrument the path with structured metadata (search type, applied filters) for observability.
- Ensure existing clients, including the MCP tool, keep working without changes.

## Implementation Tasks
1. Refactor API layer (`core/api/memory_blocks.py`) to call `SearchService.enhanced_search_memory_blocks`.
2. Extend `SearchService._basic_search_fallback` to support explicit keyword lists and AND/OR handling.
3. Wire request parameter validation (strategy selection, limit bounds, agent/conversation UUID format).
4. Add audit/metrics hooks (structured logs) describing strategy and filters.
5. Update `MemoryServiceClient.retrieveRelevantMemories` fixtures/tests if response schema changes.
6. Update docs (README/server notes) describing search strategies and defaults.
7. Maintain ≥80% overall test coverage; increase local coverage for refactored modules to ≥90%.

## Testing Strategy
- Unit tests for `SearchService` covering basic/fulltext/hybrid fallbacks.
- API integration tests for `/memory-blocks/search/` verifying:
  * default behaviour matches current keyword results,
  * scope enforcement for public/personal/organization memories,
  * validation errors for bad parameters.
- Regression tests for MCP client tool invocation (mock HTTP).
- Ensure test suite exercises migrations indirectly; no schema changes in this MR.
- Run full `pytest` suite; fail build if coverage <80%.

## Tooling & CI Checklist
- Add/adjust coverage configuration to surface per-module stats.
- Update Makefile or scripts to run focused search tests.
- Document manual verification steps in PR description.

## Dependencies & Risks
- Requires clean state of `main`/`staging` before merge.
- Low risk: purely refactor + validation tightening. Regression testing critical for MCP path.

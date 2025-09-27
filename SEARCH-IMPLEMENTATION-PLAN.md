# Search Infrastructure Foundation Plan (Updated)

## Goals
- Finish consolidating agent-facing `/memory-blocks/search/` on the shared `SearchService` pipeline so keyword/basic search behaves like enhanced strategies.
- Preserve existing defaults for clients (keyword/basic) while allowing explicit strategy selection (`basic`, `fulltext`, `semantic`, `hybrid`).
- Enforce scope filters, agent/conversation bounds, and validation consistently across all strategies.
- Emit structured metadata (strategy, filters, expansion status) for observability.
- Keep the MCP client working without interface changes.

## Implementation Tasks
1. ✅ Deliver shared search helpers (`SearchService`/CRUD) through the earlier embeddings worktree.
2. Refactor the `/memory-blocks/search/` endpoint in `core/api/memory_blocks.py` to call `crud.search_memory_blocks_enhanced`, handling strategy/limit validation and response metadata.
3. Remove or adapt the legacy `retrieve_relevant_memories` repository helper so agent search uses the shared service path.
4. Add structured logs/metrics describing selected strategy, filters, and expansion status.
5. Update integration tests for `/memory-blocks/search/` plus any MCP fixtures to exercise strategy selection, scope enforcement, and validation errors.
6. Refresh documentation (README + MCP tooling notes) describing search strategies, defaults, and new metadata.
7. Maintain ≥80% coverage overall and ≥90% for newly refactored modules.

## Testing Strategy
- Unit tests around validation utilities (strategy parsing, UUID handling) and the enhanced CRUD delegation.
- Integration tests for `/memory-blocks/search/` verifying default keyword behaviour, explicit strategies, and failure cases.
- MCP regression test (or mocked HTTP client) ensuring the tool still works with default parameters.
- Full pytest run with coverage check ≥80%.

## Observability & Tooling
- Ensure logs include strategy, filters, query expansion metadata, and scope context for auditability.
- Expose recommended commands in the README for running the focused search test suite.

## Dependencies & Risks
- Depends on SearchService work from `search-embeddings-ingest` (already merged).
- Regression risk for agent clients; thorough integration/regression testing required.
- Keep default behaviour identical unless a strategy parameter is explicitly provided.

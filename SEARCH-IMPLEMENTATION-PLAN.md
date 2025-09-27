# Search Search-Service Convergence Plan (Updated)

## Goals
- Consolidate keyword, fulltext, semantic, and hybrid searches on the shared `SearchService` pipeline so all strategies share validation, scoping, and telemetry.
- Preserve historical defaults for keyword/basic searches while allowing explicit strategy overrides (`basic`, `fulltext`, `semantic`, `hybrid`).
- Provide semantic retrieval via pgvector with consistent scoring metadata and graceful fallbacks when embeddings or vector support are unavailable.
- Emit structured metadata (strategy, weights, filters, expansion status) for observability and propagate it to API clients.
- Keep MCP and dashboard consumers working without interface breaking changes.
- Maintain ≥80% overall coverage (≥90% on newly refactored paths).

## Implementation Tasks
1. ✅ Ship shared search helpers (`SearchService`, CRUD facade, repository wiring) from the embeddings ingest work.
2. ✅ Refactor `/memory-blocks/search/` to delegate to `SearchService.enhanced_search_memory_blocks`, validate inputs, and surface metadata headers.
3. ✅ Replace repository-level keyword search with the unified service while keeping a legacy fallback for edge cases.
4. ✅ Harden semantic search (pgvector cosine similarity, thresholds, fallbacks) and expose rank explanations/score components.
5. ✅ Update integration/unit coverage for strategy selection, scope enforcement, fallback behaviour, and metadata emission.
6. 🔄 Refresh docs + MCP tooling notes to describe strategy defaults, overrides, and metadata headers.
7. 🔄 Monitor staging metrics for latency/hit ratio regressions as hybrid weighting evolves.

## Testing Strategy
- Unit tests for validation utilities, semantic/pgvector fallbacks, hybrid weighting heuristics, and CRUD delegation.
- Integration tests for `/memory-blocks/search/` plus dedicated endpoints (`fulltext`, `semantic`, `hybrid`) covering defaults, overrides, and errors.
- MCP regression check ensuring default parameters continue to function.
- Full pytest runs with coverage ≥80%.

## Observability & Tooling
- Include strategy, filters, expansion, and scope context in logs; expose headers (`X-Search-Metadata`) to API consumers.
- Document focused commands for running search-centric test suites.

## Dependencies & Risks
- Relies on embeddings ingestion landing ahead of semantic/pgvector usage.
- Requires Postgres + pgvector in production; non-Postgres environments automatically fall back to substring search.
- Regression risk for legacy clients; thorough integration/regression testing mitigates.

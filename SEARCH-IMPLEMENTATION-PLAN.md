# Search Semantic API Plan (Updated)

## Goals
- Implement semantic retrieval using stored embeddings for memory blocks.
- Expose similarity-based ranking through `/memory-blocks/search/semantic` with consistent scoring metadata.
- Provide configurable thresholds, pagination, and scope filters aligned with other search strategies.
- Maintain ≥80% overall coverage (semantic paths ≥90%).

## Implementation Tasks
1. ✅ Replace the placeholder semantic search with a pgvector similarity query supporting cosine distance.
2. ✅ Honor optional filters (agent, conversation, scope, archived) and gracefully fall back when embeddings are unavailable.
3. ✅ Extend `/memory-blocks/search/semantic` to expose thresholds, limits, and return `MemoryBlockWithScore` payloads with rank explanations.
4. ✅ Add defensive checks/logging when embeddings are disabled and propagate fallback metadata to clients.
5. ✅ Ensure MCP/dashboard consumers understand the new search metadata (score, type, explanation).
6. 🔄 Monitor metrics for latency/hit ratio regression as staging evolves (no additional code tasks pending).

## Testing Strategy
- ✅ Unit tests covering semantic query composition and pgvector fallbacks.
- ✅ Integration tests validating ranking, thresholds, and fallback behaviour when vectors or providers are absent.
- ✅ Regression verification that hybrid search incorporates semantic results correctly.
- 🔄 Full pytest runs retained to guard for regressions after merges.

## Dependencies & Risks
- Depends on embeddings ingestion (already merged on staging).
- Requires Postgres with pgvector; non-Postgres environments will exercise the documented fallback path.
- Performance tuning may be required as data volume grows; monitor staging metrics after deploy.

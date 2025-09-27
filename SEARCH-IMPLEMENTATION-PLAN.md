# Search Semantic API Plan

## Goals
- Implement true semantic retrieval using stored embeddings for memory blocks.
- Expose similarity-based ranking through `/memory-blocks/search/semantic` and ensure consistent response schema with scores and metadata.
- Provide configurable thresholds, pagination, and sorting strategies.
- Maintain ≥80% overall coverage; semantic search paths ≥90% where feasible.

## Implementation Tasks
1. SearchService enhancements
   - ✅ Replace placeholder `search_memory_blocks_semantic` with a pgvector similarity query (cosine distance or dot product).
   - ✅ Support optional filters (agent, conversation, scope) and archived handling.
   - ✅ Return `MemoryBlockWithScore` objects with similarity metrics and rank explanations.
2. Repository/DAO support
   - ✅ Ensure repository helpers gracefully degrade when vectors are missing (log and fall back to basic search paths).
3. API layer
   - ✅ Adjust `/memory-blocks/search/semantic` to expose threshold, limit, include_archived, and surface metadata.
   - ✅ Add defensive checks when embeddings are disabled and respond with informative errors/fallback metadata.
4. Metrics & logging
   - Instrument latency, hit ratios, and fallback reasons for semantic queries.
5. Client updates
   - Confirm MCP client and dashboard consumers handle `search_score`/`rank_explanation` fields.
6. Documentation & rollout notes
   - Update docs describing semantic search behaviour, configuration toggles, and expected responses.

## Testing Strategy
- ✅ Unit tests for SearchService semantic queries using pgvector fixtures and stub data.
- ✅ Integration tests hitting the REST endpoint verifying ranking, thresholds, and fallback behaviour when embeddings are absent.
- ✅ Regression tests ensuring the hybrid path blends semantic results correctly.
- Full pytest run verifying coverage; add targeted tests for failure paths (e.g., pgvector extension missing).

## Dependencies & Risks
- Depends on embedding ingestion branch (ensures vectors exist and backfill tooling is available).
- Requires Postgres with pgvector; tests must skip or fall back on SQLite.
- Query performance may need monitoring; be ready to tune indexes or adjust limits.

# Search Hybrid Ranking Plan

## Goals
- Blend full-text, semantic, and heuristic signals into a unified ranking aligned with RAG best practices.
- Provide transparent score breakdowns (full-text, semantic, boosts, reranker) so clients can reason about ordering.
- Keep results performant under per-tenant workloads; track latency and retrieval counts.
- Maintain ≥80% overall coverage; new ranking utilities ≥90% where feasible.

## Implementation Tasks
1. Scoring framework
   - Extend `SearchService.search_memory_blocks_hybrid` to normalize full-text/semantic scores, apply configurable weights, and expose component metadata.
   - Layer heuristic boosts (feedback score bonus, recent-memory decay, scope adjustments) behind config toggles.
2. Reranker integration
   - Introduce a pluggable reranker interface with a default no-op implementation and wire optional cross-encoder/LLM reranker for top-k results.
   - Surface reranker latency and applied adjustments in response metadata.
3. Retrieval counters + telemetry
   - Increment `retrieval_count` when results are returned; ensure updates are transactional and safe under concurrency.
   - Emit structured logs/metrics for hybrid blending (weights, fallback reasons, final scores).
4. Configuration & documentation
   - Add configs for weights, heuristic toggles, reranker provider/model, and decay windows.
   - Update README/prod runbooks describing ranking pipeline, tuning guidance, and fallback behaviour.
5. Client compatibility
   - Ensure API responses continue returning `search_score`, `search_type`, and rank explanations including component breakdown.
   - Confirm MCP/dashboard consumers handle the extra metadata gracefully.

## Testing Strategy
- Unit tests for weighted score math, heuristic boosts, and reranker hooks; verify monotonic behaviour under edge cases.
- Integration tests for `/memory-blocks/search/hybrid` validating blended ordering, fallback semantics, and retrieval_count increments.
- Reranker stub tests to confirm optional execution paths and metadata emission.
- Run targeted performance/regression checks to ensure latency budgets met; monitor retrieval_count writes under load.

## Dependencies & Risks
- Relies on semantic search branch (vector similarity + metadata) merged earlier.
- External rerankers may require network/model access; provide mock implementations for CI.
- Retrieval_count updates can contend under parallel requests; consider batching or deferred writes if necessary.

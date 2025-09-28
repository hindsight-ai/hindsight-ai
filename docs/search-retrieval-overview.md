# Search Retrieval Overview

This document summarizes the layered retrieval pipeline implemented across the recent search worktrees: embedding ingestion, hybrid ranking, and query expansion. It acts as the canonical reference for engineers tuning or extending search behaviour.

## Embedding Ingestion

Dense embeddings back the semantic and hybrid search modes.

- Embeddings live on `memory_blocks.content_embedding` via pgvector (with JSON fallback under SQLite).
- Providers: `mock`, `ollama`, `huggingface`, configured through `EmbeddingConfig` / `EmbeddingService` exposed in `core.services`.
- `scripts/backfill_embeddings.py` orchestrates batched backfills with `--batch-size` and `--dry-run` toggles.

Operational notes:

- Generate embeddings synchronously on memory create/update when a provider is enabled.
- Keep the mock provider as default in CI; monitor latency/cost for real providers.
- After enabling a real provider, run the backfill script to hydrate historical memories.

## Hybrid Ranking

Hybrid search blends full-text and semantic scores, then applies heuristic boosts.

- Implementation: `SearchService.search_memory_blocks_hybrid`
  - Normalizes component scores and merges using configurable weights.
  - Applies recency decay, feedback boosts, scope bonuses (and leaves space for rerankers).
  - Returns per-result `score_components`, combined explanations, and heuristic metadata.
- Environment knobs (`HYBRID_*`) control weights, normalization, decay windows, feedback/scope bonuses, reranker toggles, and score floors.
- Call `refresh_hybrid_ranking_config()` in tests after mutating environment values.

Telemetry highlights:

- Metadata includes weight snapshots, heuristic enablement flags, fallback reasons, and per-result components.
- API endpoints log the final mode plus whether expansion was applied.

## Query Expansion

Query expansion broadens the user query before handing it to downstream search flows.

- `QueryExpansionEngine` applies stemming, synonym swaps (default or JSON-supplied dictionaries), and optional LLM rewrites (`QUERY_EXPANSION_LLM_PROVIDER`, with `mock` providing deterministic variants for tests).
- When `QUERY_EXPANSION_LLM_PROVIDER=ollama`, the engine calls the same Ollama instance that powers embeddings (defaults to `http://ollama:11434`) using the model named in `QUERY_EXPANSION_LLM_MODEL` (recommended: lightweight models such as `llama3.2:1b`). Guardrails—temperature defaults to `0.0`, max tokens to `64`, and results are sanitized/deduplicated—ensure rewrites fall back to rule-based variants when the LLM misbehaves.
- Guardrails: `QUERY_EXPANSION_MAX_VARIANTS` and `QUERY_EXPANSION_LLM_MAX_VARIANTS` cap fan-out.
- CRUD helpers invoke `_execute_with_query_expansion`, which runs the base/expanded queries, deduplicates results, aggregates metadata, and keeps variant telemetry.
- Expansion metadata records the original query, applied steps, variant runs, and aggregate timing.

## Evaluation Harness

`core.search.evaluation.evaluate_cases` compares baseline vs. expanded precision/recall for curated query ↔ memory datasets.

- CLI wrapper: `uv run python apps/hindsight-service/scripts/run_query_expansion_evaluation.py --dataset cases.json --output summary.json`.
- Integration test `tests/integration/search/test_query_expansion_eval.py` seeds fixtures and asserts improved recall when expansion is enabled.

## Testing & Future Work

- Unit coverage: `tests/unit/test_query_expansion_engine.py` and `tests/unit/test_crud_query_expansion.py`.
- Regression coverage: `tests/integration/search/test_search_api.py` exercises metadata wiring.
- Follow-ups: tenant-specific synonym dictionaries, caching/rate limiting for LLM rewrites, CI gates on evaluation deltas, and optional intent classification experiments building on the expansion infrastructure.

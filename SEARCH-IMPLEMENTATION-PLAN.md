# Search Embeddings Ingest Plan

## Goals
- Introduce dense vector support for memory blocks using pgvector (or equivalent) for semantic retrieval.
- Generate embeddings at write time and ensure updates keep vectors in sync.
- Provide a safe backfill path for existing records and tooling for monitoring progress.
- Reuse proven embedding integration patterns from `/home/jeanibarz/git/knowledge-base-mcp-server` (local inference via Hugging Face/Ollama) while keeping providers swappable.
- Maintain ≥80% overall coverage; new modules ≥90% where feasible.

## Implementation Snapshot

- ✅ **Database migrations**: `8c0f1b2d4a6b_switch_content_embedding_to_pgvector.py` enables pgvector when available and swaps `memory_blocks.content_embedding` to the new vector type while keeping SQLite JSON fallback support through `EmbeddingVector`.
- ✅ **Embedding service layer**: `core/services/embedding_service.py` centralises provider selection (mock, Ollama, HuggingFace) and exposes helpers via `core/services/__init__.py`.
- ✅ **Ingestion pipeline**: `core/db/repositories/memory_blocks.py` now attaches embeddings on create/update when a provider is enabled, with defensive logging and opt-out when disabled.
- ✅ **Backfill entry point**: `EmbeddingService.backfill_missing_embeddings` performs batched updates; orchestration script still TBD once we wire CLI plumbing.
- ✅ **Configuration**: `EMBEDDING_PROVIDER`, `EMBEDDING_DIMENSION`, provider-specific env vars, and dependency bumps (`pgvector>=0.4.1`).
- ✅ **Testing**: Added focused unit coverage for `EmbeddingVector` and embedding service behaviours plus integration tests under `tests/integration/memory_blocks/test_memory_embeddings.py`.
- ✅ **Operational tooling**: `scripts/backfill_embeddings.py` now wraps `EmbeddingService.backfill_missing_embeddings` with batch sizing and dry-run support; remaining follow-up is lightweight observability (metrics/logging) for production runs.
- 🔄 **Hybrid ranking rollout**: Once semantic endpoints land we must evaluate vector index sizing and scheduling (tracked separately).

## Testing Strategy
- ✅ Alembic migration exercised via integration suite (testcontainers Postgres) ensuring the vector column is available during fixture setup.
- ✅ Unit tests cover key branches in `EmbeddingVector` (bind/result handling) and `EmbeddingService` helpers (mock provider, blank text short-circuit, metadata composition).
- ✅ Integration tests verify memory create/update/backfill populate embeddings without blocking writes when providers are disabled.
- 🔄 Backfill scripting smoke test: add an end-to-end exercise (e.g. seeded Postgres fixture invoking `uv run python scripts/backfill_embeddings.py`) so CI covers the management command path.

## Dependencies & Risks
- Requires Postgres ≥14 with the pgvector extension installed; SQLite keeps using JSON storage through the type decorator.
- External providers (Ollama/HuggingFace) introduce network variance. The mock provider remains the default for CI and local development without credentials.
- Coordinate with DevOps to ensure pgvector is available prior to deploying the migration and to provision provider credentials where applicable.
- Monitor row size growth; consider partial indexes or pruning strategies if embeddings materially impact storage or query performance.

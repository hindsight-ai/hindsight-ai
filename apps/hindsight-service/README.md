# Memory Service

This service is the core backend logic for managing the AI agent's memory. It handles database interactions, core memory operations like keyword extraction and feedback processing, and exposes an internal API for other services (like the MCP server) to consume.

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- `uv` (or `pip` and `pip-tools`) for dependency management.
- Docker and Docker Compose (for running the PostgreSQL database).

### Setup

1.  **Navigate to the `hindsight-service` directory:**
    ```bash
    cd apps/hindsight-service
    ```

2.  **Install dependencies:**
    Using `uv` (recommended):
    ```bash
    uv sync
    ```
    Or using `pip` and `pip-tools`:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Database Setup:**
    Ensure the PostgreSQL database is running and the schema is migrated. Refer to the `../infra/README.md` for detailed instructions on setting up the database.

### Running the Service

To start the memory service, run the following command from the `hindsight-service` directory:

```bash
uv run uvicorn core.api.main:app --reload --host 0.0.0.0 --port 8000
```
This will start the FastAPI application, typically accessible at `http://localhost:8000`.

## 📂 Project Structure

-   `core/api/`: Contains the FastAPI application entry point and API routes.
-   `core/db/`: Houses database models (SQLAlchemy ORM), database session management, and CRUD operations.
-   `core/core/`: Legacy/back-compat shims and select long-running workers.
-   `core/workers/`: Background/long-running tasks (e.g., consolidation worker, async bulk operations shim).
-   `core/utils/`: Lightweight utilities (e.g., keyword extraction heuristics, role/scope constants).

## 🔎 Keyword Extraction

- Active extractor: `core/utils/keywords.py` provides `simple_extract_keywords()`, a dependency-free heuristic that
  selects up to 10 lowercased tokens (>= 3 chars), de-duplicated in first-seen order.
- Repositories call this heuristic as the default. There is no spaCy dependency.
- Removed legacy stub: the old `core/core/keyword_extraction.py` spaCy-based implementation was an experimental stub and
  returned empty results; it has been removed to reduce confusion and dead code.

## 🔗 Environment

Important env vars (see `.env.example`):
- `APP_BASE_URL`: Frontend base URL used to build login/accept-invite links in emails.
  - Production: `https://app.hindsight-ai.com`
  - Staging: `https://app-staging.hindsight-ai.com`
  - Dev: `http://localhost:3000`
- `ADMIN_EMAILS`: Comma-separated emails to elevate as superadmins on first login. Required for accessing admin-only routes such as the beta access console.
- `BETA_ACCESS_ADMINS`: Optional comma-separated emails allowed to review beta access requests without being full superadmins.
- `DEV_MODE`: **Local development only.** When `true` the API impersonates `dev@localhost` as a superadmin, auto-accepts beta access, and issues a ready-to-use PAT (returned by `/user-info` and logged on startup). The backend will refuse to start with `DEV_MODE=true` unless it is running on `localhost`. Always set `DEV_MODE=false` (or unset) in staging and production.
- `ALLOW_DEV_MODE`: Optional safety valve for automated tests. Leave set to `false` outside controlled test environments.

### Embedding Configuration

Semantic retrieval relies on dense vector embeddings. The service can run with embeddings disabled (default), a mock provider for deterministic testing, or real providers:

- `EMBEDDING_PROVIDER`: `disabled` (default), `mock`, `ollama`, or `huggingface`.
- `EMBEDDING_DIMENSION`: Optional integer dimension override. Mock provider falls back to 32 when unset.
- `OLLAMA_BASE_URL` / `OLLAMA_EMBEDDING_MODEL`: Ollama settings (defaults: `http://localhost:11434`, `nomic-embed-text:v1.5`).
- `HUGGINGFACE_API_KEY`, `HUGGINGFACE_EMBEDDING_MODEL`, `HUGGINGFACE_API_BASE`: Hugging Face Inference API settings. Provider is disabled automatically when the key is missing.

When a provider is enabled, embeddings are generated synchronously on memory create/update. The mock provider is used in CI so tests do not require network access. Use `EmbeddingService.backfill_missing_embeddings` for batched backfills once a provider is configured.

Local Docker Compose profiles spin up `ollama/ollama` alongside Postgres and the API. Models are cached in the `ollama_data` volume, and the backend automatically targets `http://ollama:11434` with `nomic-embed-text:v1.5` unless overridden via environment variables. If the provider is unreachable or pgvector is unavailable, the service falls back to the Python cosine implementation and ultimately to keyword search, emitting the reason in `X-Search-Metadata`.

#### Embedding Backfill Script

Run the utility script once a provider is configured:

```bash
uv run python scripts/backfill_embeddings.py --batch-size 200
```

Add `--dry-run` to inspect how many rows still need embeddings before running the job.

### Hybrid Ranking Configuration

Hybrid search blends full-text and semantic signals with heuristic boosts. Tuning is driven by environment variables (all optional with sensible defaults):

- `HYBRID_FULLTEXT_WEIGHT`, `HYBRID_SEMANTIC_WEIGHT`: Baseline weights before normalization (defaults 0.7/0.3).
- `HYBRID_ALLOW_WEIGHT_OVERRIDES`: When `false`, ignores request overrides and pins configured weights (default `true`).
- `HYBRID_NORMALIZATION`: Component score normalization strategy (`min_max` default, `max` supported).
- `HYBRID_MIN_SCORE_FLOOR`: Lower bound applied after heuristics (default `0`).
- Recency decay knobs: `HYBRID_RECENCY_DECAY_ENABLED`, `HYBRID_RECENCY_HALF_LIFE_DAYS`, `HYBRID_RECENCY_MIN_MULTIPLIER`, `HYBRID_RECENCY_MAX_MULTIPLIER`.
- Feedback bonuses: `HYBRID_FEEDBACK_BOOST_ENABLED`, `HYBRID_FEEDBACK_WEIGHT`, `HYBRID_FEEDBACK_MAX_SCORE`.
- Scope adjustments: `HYBRID_SCOPE_BOOST_ENABLED`, `HYBRID_SCOPE_PERSONAL_BONUS`, `HYBRID_SCOPE_ORG_BONUS`, `HYBRID_SCOPE_PUBLIC_BONUS`.
- Reranker scaffolding: `HYBRID_RERANKER_ENABLED`, `HYBRID_RERANKER_PROVIDER`, `HYBRID_RERANKER_TOP_K`.

Configuration is cached per process; call `refresh_hybrid_ranking_config()` in tests when mutating environment variables.

### Query Expansion Configuration & Evaluation

The query expansion pipeline applies stemming, synonym substitution, and optional LLM rewrites before invoking the existing search flows. Key toggles:

- `QUERY_EXPANSION_ENABLED` (default `true`).
- `QUERY_EXPANSION_STEMMING_ENABLED`, `QUERY_EXPANSION_SYNONYMS_ENABLED`.
- `QUERY_EXPANSION_MAX_VARIANTS` (default `5`) and `QUERY_EXPANSION_SYNONYMS_PATH` (JSON dictionary of token → synonyms).
- `QUERY_EXPANSION_LLM_PROVIDER` (`mock` yields deterministic rewrites for tests) and `QUERY_EXPANSION_LLM_MAX_VARIANTS`.

An evaluation harness compares baseline vs. expanded retrieval quality. Create a JSON dataset of cases (each entry: `query`, optional `search_type`, and `relevant_ids`) and run:

```bash
uv run python apps/hindsight-service/scripts/run_query_expansion_evaluation.py --dataset path/to/dataset.json --output summary.json
```

Within tests, `core.search.evaluation.evaluate_cases` returns per-query precision/recall plus aggregate deltas so you can gate CI or surface regressions.

See `docs/search-retrieval-overview.md` for a consolidated overview of embedding ingestion, hybrid ranking, and query expansion internals.

## 🔐 Permissions & Scopes

- See `SECURITY.md` for the security model overview (roles, scopes, and helpers).
- See `ROLE_PERMISSIONS_README.md` for dynamic role permission details and usage patterns.

## 🔑 Personal Access Tokens (PAT)

- Create/manage under Dashboard → Profile → API Tokens.
- Token format: `hs_pat_<token_id>_<secret>` (shown once on create/rotate).
- Use with requests via `Authorization: Bearer <token>` or `X-API-Key: <token>`.
- Scopes: `read` for GETs, `write` for POST/PUT/PATCH/DELETE. Optional `organization_id` restricts writes to that org.
- Middleware permits write methods when a PAT header is present; routes enforce validation and scope checks.

## 🧪 Running Tests

To run the tests for the memory service, navigate to the `hindsight-service` directory and execute:

```bash
uv run pytest
```
(Ensure `pytest` is installed as a development dependency).

## 📞 API Endpoints

The service exposes a RESTful API. You can find the automatically generated OpenAPI documentation (Swagger UI) at `/docs` when the service is running (e.g., `http://localhost:8000/docs`).

Key endpoints include:
-   `/memory_blocks/`: For creating and retrieving memory blocks.
-   `/memory_blocks/search/`: Agent-facing search endpoint. Accepts optional `strategy` (`basic`, `fulltext`, `semantic`, `hybrid`), `keywords`, or `query` plus filters (`agent_id`, `conversation_id`). Defaults to the legacy keyword/basic behaviour.
-   `/feedback_logs/`: For reporting feedback on memory blocks.
-   `/agents/`: For managing agent information.
-   `/keywords/`: For managing keywords.

---

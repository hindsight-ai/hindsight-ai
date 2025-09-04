# Memory Service (FastAPI)

Core backend for Hindsight AI: stores and retrieves memory blocks, records feedback, proposes LLM‑based consolidation and pruning suggestions, and serves the dashboard + MCP server.

## Quick Start

Run everything via Docker (recommended): see the repository root README quickstart. To run just the API locally:

Prereqs
- Python 3.10+ and `uv` (or pip)
- Local PostgreSQL or `docker compose` from `infra/postgres`

Install and run
```bash
cd apps/hindsight-service
uv sync
export DATABASE_URL=postgresql://user:password@localhost:5432/hindsight_db
uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Open `http://localhost:8000/docs` for Swagger.

## Environment Variables

- `DATABASE_URL`: PostgreSQL URI (required)
- `LLM_API_KEY`: API key for Gemini (optional; enables consolidation/pruning LLM paths)
- `LLM_MODEL_NAME`: Gemini model name (default: `gemini-2.5-flash`)
- `CONSOLIDATION_BATCH_SIZE`: Batch size for consolidation worker (default 100)
- `FALLBACK_SIMILARITY_THRESHOLD`: TF‑IDF duplicate threshold (default 0.4)
- `DEV_MODE`: If `true`, `/user-info` returns a mock user (local dev convenience)

## API Quick Tour

Create an agent
```bash
curl -s -X POST http://localhost:8000/agents/ \
  -H 'Content-Type: application/json' \
  -d '{"agent_name":"dev-agent"}'
```

Create a memory block
```bash
curl -s -X POST http://localhost:8000/memory-blocks/ \
  -H 'Content-Type: application/json' \
  -d '{
    "agent_id":"<agent-uuid>",
    "conversation_id":"00000000-0000-0000-0000-000000000001",
    "content":"Investigated intermittent 500 errors on POST /checkout.",
    "lessons_learned":"Added backoff, fixed race condition.",
    "errors":"Timeouts from payment gateway",
    "metadata_col": {"service":"checkout","latency_ms":720}
  }'
```

List memory blocks with filters and pagination
```bash
curl -s "http://localhost:8000/memory-blocks/?search_query=timeout&limit=25&sort_by=creation_date&sort_order=desc"
```

Report feedback (affects `feedback_score`)
```bash
curl -s -X POST http://localhost:8000/memory-blocks/<id>/feedback/ \
  -H 'Content-Type: application/json' \
  -d '{"memory_id":"<id>","feedback_type":"positive","feedback_details":"useful fix"}'
```

Archive a memory block
```bash
curl -s -X POST http://localhost:8000/memory-blocks/<id>/archive
```

List archived memory blocks
```bash
curl -s "http://localhost:8000/memory-blocks/archived/?limit=25"
```

Generate pruning suggestions (LLM or fallback)
```bash
curl -s -X POST http://localhost:8000/memory/prune/suggest -H 'Content-Type: application/json' -d '{"batch_size":20}'
```

Confirm pruning (archives the selected IDs)
```bash
curl -s -X POST http://localhost:8000/memory/prune/confirm \
  -H 'Content-Type: application/json' \
  -d '{"memory_block_ids":["<id1>","<id2>"]}'
```

Consolidation suggestions (LLM‑generated)
```bash
curl -s "http://localhost:8000/consolidation-suggestions/?status=pending&limit=50"
```

Validate or reject a suggestion
```bash
curl -s -X POST http://localhost:8000/consolidation-suggestions/<suggestion_id>/validate/
curl -s -X POST http://localhost:8000/consolidation-suggestions/<suggestion_id>/reject/
```

## Project Structure

- `core/api/`: FastAPI app, routes
- `core/db/`: SQLAlchemy models, schemas, CRUD, session
- `core/core/`: consolidation worker, (placeholder) keyword extraction
- `core/pruning/`: LLM‑based pruning suggestions service
- `migrations/`: Alembic configuration + versions

## Tests

```bash
uv run pytest
```

## Notes

- Keyword extraction is currently stubbed; you can integrate spaCy or another NLP lib in `core/core/keyword_extraction.py`.
- Consolidation uses Gemini when `LLM_API_KEY` is present; otherwise a TF‑IDF duplicate grouping fallback runs (no rewriting).
- Pruning suggestions work in batches and degrade gracefully without an API key.

Request bodies may use either `metadata_col` or `metadata` — the API accepts `metadata` as an alias.

### Important: Start from Backup (until migrations are fixed)

On a fresh database, Alembic migrations may not apply cleanly. For now, the fastest path to a working setup is to restore the provided backup:

```bash
# 1) Ensure Docker is available and .env is set
cp .env.example .env

# 2) Restore the database from the included backup (interactive selector)
./infra/scripts/restore_db.sh

# 3) Start the stack
./start_hindsight.sh
```

The restore script drops and recreates `hindsight_db`, restores from `hindsight_db_backups/data/…sql`, and attempts to align Alembic to the backup’s revision.

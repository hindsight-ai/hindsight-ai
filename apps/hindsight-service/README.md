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
- `DEV_MODE`: Set to `true` locally to bypass SSO with `dev@localhost` and auto-mark beta access as accepted for quicker manual testing.

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
-   `/feedback_logs/`: For reporting feedback on memory blocks.
-   `/agents/`: For managing agent information.
-   `/keywords/`: For managing keywords.

---

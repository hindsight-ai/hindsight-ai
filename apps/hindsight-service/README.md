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
uv run uvicorn memory_service.api.main:app --host 0.0.0.0 --port 8000
```
This will start the FastAPI application, typically accessible at `http://localhost:8000`.

## 📂 Project Structure

-   `src/memory_service/api/`: Contains the FastAPI application entry point and API routes.
-   `src/memory_service/db/`: Houses database models (SQLAlchemy ORM), database session management, and CRUD operations.
-   `src/memory_service/core/`: Contains core business logic, such as keyword extraction (MVP currently simple) and feedback processing.

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

# Hindsight AI

Hindsight AI is a system designed to enhance AI agent memory and operational intelligence. Its primary purpose is to provide a robust and scalable solution for:
- **Memory Management:** Storing, retrieving, and managing an AI agent's conversational and operational memories.
- **Knowledge Distillation:** Extracting actionable insights and lessons learned from raw interactions.
- **Continuous Improvement:** Enabling AI agents to learn from past experiences and improve their performance over time.

The system aims to address the general problem of AI agents lacking persistent learning and self-improvement capabilities, providing a foundation for more intelligent and adaptive AI behaviors. While designed for scalability, specific data volume expectations and detailed scaling strategies for production environments are not yet documented.

## Overall Architecture

The monorepo includes the following main applications and infrastructure components:

-   **Applications (`apps/`):**
    -   [`hindsight-dashboard`](apps/hindsight-dashboard/README.md): The frontend application for visualizing and interacting with the memory service.
    -   [`hindsight-service`](apps/hindsight-service/README.md): The core backend service for managing AI agent memories, keyword extraction, and database interactions.
    -   [`hindsight-copilot-assistant`](apps/hindsight-copilot-assistant/README.md): A Next.js application that serves as a Copilot Assistant for the Hindsight AI memory service, providing a generative UI for interacting with the AI Agent Memory Service.
-   **Infrastructure (`infra/`):**
    -   `postgres`: Docker Compose setup for the PostgreSQL database.
    -   `migrations`: SQL scripts for initial database schema setup.
-   **MCP Servers (`mcp-servers/`):**
    -   [`hindsight-mcp`](mcp-servers/hindsight-mcp/README.md): An MCP (Model Context Protocol) server that extends AI agent capabilities by providing tools and resources. The `hindsight-mcp` server specifically offers tools for interacting with the Hindsight AI Agent Memory Service, enabling agents to manage memory blocks, retrieve relevant memories, and report feedback within the Hindsight AI ecosystem.

These components are designed to integrate seamlessly. The `hindsight-service` (backend) interacts with the PostgreSQL database (part of `infra` components) and exposes an API, which is then consumed by the `hindsight-dashboard` (frontend) for visualization and interaction.

### Knowledge Distillation Process

Knowledge distillation within Hindsight AI is primarily performed by a background worker (`consolidation_worker.py`) that consolidates similar or duplicate memory blocks into single, refined suggestions. The process involves:
1.  **Fetching Memory Blocks:** Retrieving memory blocks from the database in batches.
2.  **Analyzing Duplicates:** This is done primarily using an LLM-based analysis (Google Gemini API). The LLM is prompted to act as an AI assistant, identify semantically similar or duplicate memory blocks, group them, and then generate a consolidated version of the `content`, `lessons_learned`, and `keywords` for each group. The goal is to increase quality and information density while reducing overall size. A fallback similarity analysis (TF-IDF vectorization and cosine similarity) is used if the LLM is unavailable, but it *only* identifies groups and does not generate consolidated suggestions.
3.  **Storing Suggestions:** Only LLM-generated consolidation suggestions are stored in the `consolidation_suggestions` table with a "pending" status, awaiting user review.

The underlying mechanisms involve:
*   **LLM (Google Gemini API):** For semantic analysis, grouping, and generating consolidated content, lessons learned, and keywords. It's configured with a low temperature (0.3) for deterministic responses and strict JSON output.
*   **TF-IDF Vectorization and Cosine Similarity:** As a fallback mechanism for identifying similar memory blocks when the LLM is not available.

### Types of Operational Memories Stored

Hindsight AI stores various types of operational memories within its `MemoryBlock` model:
*   `content`: The main content of the memory block, which can include general conversational data or any textual information an AI agent deems important.
*   `errors`: Textual details about errors encountered, potentially including system logs or error messages.
*   `lessons_learned`: Textual information summarizing lessons learned from an interaction or experience.
*   `metadata_col`: A flexible JSONB column for additional structured metadata. This can store data like performance metrics (e.g., `{"latency": 150, "cpu_usage": "20%"}`), decision-making traces (e.g., `{"decision_path": ["step1", "step2"], "outcome": "success"}`), or other relevant operational context.
*   `keywords`: Associated keywords for the memory block.
*   `feedback_score`: An integer representing feedback on the memory block.
*   `retrieval_count`: An integer tracking how many times the memory block has been retrieved.
*   `archived`: A boolean indicating if the memory block is archived.

### Integration with AI Agents and External Systems

Hindsight AI integrates with existing AI agents and external systems primarily through two mechanisms:
1.  **FastAPI Backend API:** The `hindsight-service` exposes a RESTful API that allows for direct HTTP-based interaction with the memory service. This API provides endpoints for managing agents, memory blocks (creation, retrieval, update, archive, delete), feedback, keywords, and search.
2.  **Model Context Protocol (MCP) Server:** The `hindsight-mcp` server provides a set of predefined tools for MCP-compatible AI agents to interact with the Hindsight AI memory service. These tools abstract the underlying API calls and handle environment variable injection for `agent_id`, `conversation_id`, and `MEMORY_SERVICE_BASE_URL`. Tools include `create_memory_block`, `retrieve_relevant_memories`, `retrieve_all_memory_blocks`, `retrieve_memory_blocks_by_conversation_id`, `report_memory_feedback`, and `get_memory_details`.

### Feedback Mechanism

AI agents can report explicit feedback on the utility or correctness of a previously retrieved `memory_block` using the `report_memory_feedback` tool provided by the `hindsight-mcp` server. This tool requires the `memory_block_id` (UUID), `feedback_type` (enum: 'positive', 'negative', 'neutral'), and an optional `comment` (TEXT). This feedback is recorded by updating the `feedback_score` on individual memory blocks and logging feedback details. This mechanism lays the groundwork for future enhancements, such as informing LLM-based consolidation processes or guiding human review of memory blocks to further refine the memory store and improve agent performance.

## Quick Start Guide

Get Hindsight AI running in minutes with Docker Compose.

### Prerequisites
- Docker and Docker Compose
- Git

### 1. Clone and Setup
```bash
git clone https://github.com/your-repo/hindsight-ai.git
cd hindsight-ai
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` and add your LLM API key:
```bash
# Required for local development
LLM_API_KEY=your_api_key_here
LLM_MODEL_NAME=gemini-1.5-flash
```

### 3. Start Services
```bash
./start_hindsight.sh
# or with auto-rebuild on code changes
./start_hindsight.sh --watch
```

This will:
- Start PostgreSQL database
- Apply database migrations automatically
- Launch backend service on http://localhost:8000
- Launch frontend dashboard on http://localhost:3000
- Keep frontend and backend same-origin via the dashboard's `/api` proxy

Note: Database schema/data is managed via the provided backup/restore scripts.

### 4. Stop Services
```bash
./stop_hindsight.sh
```

## Database Setup

Migrations are applied automatically by the backend container at startup.

You have two options to initialize your database:

1. Fresh DB via migrations (default): Just start the stack with `./start_hindsight.sh`. The backend will run `alembic upgrade head` and create all tables.
2. Load sample data (optional): Use the provided backup to prefill the DB with example data.
   - Run: `./infra/scripts/restore_db.sh`
   - The script stops the DB, drops and recreates `hindsight_db`, restores the selected backup, and restarts the DB.
   - Useful for demos and exploring features.

## Local Development with Docker Compose

For development with hot-reload and debugging capabilities:

### Start Development Environment
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Services available at:
- **Frontend Dashboard**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Database**: localhost:5432

### Stop Development Environment
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

## Advanced Setup (Manual)

For developers who need granular control or want to run services outside Docker:

### Prerequisites
- Python 3.13+ with `uv` (or pipenv/poetry)
- Node.js and npm
- PostgreSQL (or use Docker for database)

### 1. Database Setup
```bash
cd infra/postgres
docker-compose up -d
```

### 2. Backend Service
```bash
cd apps/hindsight-service
uv sync  # Install dependencies
uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Dashboard
```bash
cd apps/hindsight-dashboard
npm install
npm start
```

## Deployment

This section provides instructions for deploying the Hindsight AI application using Docker Compose, both locally and to a remote server.

### Local Development with Docker Compose

For local development, you can use Docker Compose to build and run the services directly from the source code. This setup uses Docker Compose profiles to exclude production services like Traefik and OAuth2 proxy, making local development simpler.

1.  **Create a `.env` file:**
    *   Copy the `.env.example` file to a new file named `.env`.
    *   Fill in the required values for your local environment. You can leave `HINDSIGHT_SERVICE_IMAGE` and `HINDSIGHT_DASHBOARD_IMAGE` as they are, since Docker Compose will build the images from the source code.

2.  **Start Services for Local Development:**
    *   From the root of the project, run the following command:
        ```bash
        docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
        ```
    *   This will build the Docker images for the `hindsight-service` and `hindsight-dashboard` and start the database, backend, and frontend services.
    *   The services will be accessible at:
        *   **Frontend Dashboard**: http://localhost:3000
        *   **Backend API**: http://localhost:8000
        *   **Database**: localhost:5432 (if you need direct access)
    *   For auto-rebuild on code changes (Compose v2.21+), use:
        ```bash
        ./start_hindsight.sh --watch
        # or
        docker compose -f docker-compose.yml -f docker-compose.dev.yml watch
        ```

3.  **Stop Services:**
    *   Press `Ctrl+C` to stop the services, or run:
        ```bash
        docker compose -f docker-compose.yml -f docker-compose.dev.yml down
        ```

### Production Deployment with Docker Compose

For production deployment, you can use the same Docker Compose setup but include the production profile to enable Traefik and OAuth2 proxy.

1.  **Create a `.env` file:**
    *   Copy the `.env.example` file to a new file named `.env`.
    *   Fill in all required values including production-specific ones like OAuth2 credentials and Cloudflare settings.

2.  **Start Services for Production:**
    *   From the root of the project, run the following command:
        ```bash
        docker compose --profile prod -f docker-compose.yml up -d --build
        ```
    *   This will build the Docker images and start all services including Traefik for reverse proxy and OAuth2 proxy for authentication.
    *   Services will be accessible via your configured domain names (e.g., https://app.hindsight-ai.com).
    *   The backend API is not publicly exposed; the dashboard proxies `/api` to the backend.
        To access the API directly on the server for debugging, use SSH port-forwarding:
        ```bash
        ssh -L 8000:localhost:8000 <your_server>
        curl http://localhost:8000/build-info
        ```

### Remote Deployment

Remote deployment is automated via a GitHub Actions workflow. The workflow builds the Docker images, pushes them to the GitHub Container Registry, and then deploys them to a remote server using Docker Compose.

1.  **Prerequisites:**
    *   A remote server with Docker and Docker Compose installed.
    *   SSH access to the remote server.

2.  **Configure GitHub Secrets:**
    *   In your GitHub repository, go to `Settings > Secrets and variables > Actions` and add the following secrets:
        *   `SSH_HOST`: The IP address or hostname of your remote server.
        *   `SSH_USERNAME`: The username for SSH access to your remote server.
        *   `SSH_KEY`: The private SSH key for your remote server.
        *   `SSH_PORT`: The SSH port for your remote server (usually 22).
        *   `CLOUDFLARE_DNS_EMAIL`: Your Cloudflare email address.
        *   `CLOUDFLARE_DNS_API_TOKEN`: Your Cloudflare API token.
        *   `OAUTH2_PROXY_CLIENT_ID`: Your Google OAuth2 client ID.
        *   `OAUTH2_PROXY_CLIENT_SECRET`: Your Google OAuth2 client secret.
        *   `OAUTH2_PROXY_COOKIE_SECRET`: A long, random string for the OAuth2 Proxy cookie secret.
        *   `LLM_API_KEY`: Your API key for the LLM service.
        *   `LLM_MODEL_NAME`: The name of the LLM model you want to use.
        *   `CONSOLIDATION_BATCH_SIZE`: The batch size for the consolidation worker.
        *   `FALLBACK_SIMILARITY_THRESHOLD`: The similarity threshold for the fallback mechanism.
        *   `POSTGRES_USER`: The username for the PostgreSQL database.
        *   `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
        *   `POSTGRES_USER`: The username for the PostgreSQL database.
        *   `POSTGRES_PASSWORD`: The password for the PostgreSQL database.
        *   `AUTHORIZED_EMAILS_CONTENT`: A comma-separated list of email addresses that are authorized to access the application.

3.  **Deployment:**
    *   Pushing to the `main` or `feat/docker-compose-deployment` branch will trigger the GitHub Actions workflow.
    *   The workflow will automatically build and push the Docker images, and then deploy the application to your remote server.

### Google OAuth2 Provider Configuration

To use Google as an OAuth2 provider, you need to create a project in the [Google Cloud Console](https://console.cloud.google.com/) and configure the OAuth2 consent screen and credentials.

1.  **Create a new project.**
2.  **Configure the OAuth consent screen:**
    *   Select "External" for the user type.
    *   Fill in the required information (app name, user support email, etc.).
    *   Add the following authorized domains:
        *   `hindsight-ai.com`
        *   `google.com`
3.  **Create OAuth 2.0 client IDs:**
    *   Select "Web application" for the application type.
    *   Add the following authorized redirect URIs:
        *   `https://app.hindsight-ai.com/oauth2/callback`
        *   `https://traefik.hindsight-ai.com/oauth2/callback`
    *   Copy the "Client ID" and "Client secret" and add them to your GitHub secrets as `OAUTH2_PROXY_CLIENT_ID` and `OAUTH2_PROXY_CLIENT_SECRET`.

## Database Backup and Restore

⚠️ **IMPORTANT: Alembic migrations are currently broken.** ⚠️

A full backup and restore of the Hindsight AI PostgreSQL database (`hindsight_db`) can be performed using the `backup_db.sh` and `restore_db.sh` shell scripts located in `infra/scripts/`.

*   **Backup (`backup_db.sh`):**
    Ensure the script is executable (`chmod +x infra/scripts/backup_db.sh`), then run `./infra/scripts/backup_db.sh` from the project root. Backups are timestamped, include the Alembic revision, and are stored in `./hindsight_db_backups/data/`. The script manages old backups (keeping 100 by default). Hourly backups can be automated via cron jobs.

*   **Restore (`restore_db.sh`):**
    Ensure the script is executable (`chmod +x infra/scripts/restore_db.sh`) and the PostgreSQL Docker container is running. Run `./infra/scripts/restore_db.sh` from the project root. The script will prompt you to select a backup file, then stop the `db` container, drop and recreate `hindsight_db`, restore the selected backup, and restart the `db` container. **Caution: Restoring overwrites current data.**
    Database data is persisted using Docker Volumes, but backups are crucial to protect against explicit volume removal.

**Note:** The restore process no longer attempts to run Alembic migrations due to current issues with the migration system. The backup file contains a complete database schema and data snapshot.

The provided database backup includes sample memory blocks and consolidation suggestions that demonstrate the system's capabilities:
* **Memory Blocks:** Example operational memories showing how the system stores AI agent interactions, errors, lessons learned, and metadata
* **Consolidation Suggestions:** Examples of how the knowledge distillation process identifies similar memories and generates consolidated insights
* **Keywords:** Sample keyword extractions that show how the system categorizes and indexes memories for retrieval

This sample data helps users understand how Hindsight AI captures, organizes, and distills AI agent operational intelligence.

## Running Tests

To run tests for the Hindsight AI components:

*   **For the `hindsight-service` (Backend):**
    1.  Navigate to the `apps/hindsight-service` directory.
    2.  Ensure `pytest` is installed as a development dependency.
    3.  Execute the command: `uv run pytest`

*   **For the `hindsight-dashboard` (Frontend):**
    1.  Navigate to the `apps/hindsight-dashboard` directory.
    2.  Execute the command: `npm test`
    This launches the test runner in interactive watch mode.

## Manual Control and Troubleshooting

For development, debugging, or when you need to inspect logs directly, you might want to manually control individual services. The typical port for the Hindsight AI backend service is `8000` (`http://localhost:8000`), and for the frontend dashboard, it is `3000` (`http://localhost:3000`).

### Stopping Individual Services

While `./stop_hindsight.sh` stops all services, you can stop individual components manually. If a service is already running on its designated port, the `./start_hindsight.sh` script includes checks to prevent starting it again. If you are starting services manually, you can use commands like `lsof -t -i:PORT | xargs kill -9` (replacing `PORT` with 3000 for the dashboard or 8000 for the backend) to find and terminate the process occupying the port. The purpose of the `lsof -t -i:<port> | xargs kill -9` command is to find the process ID (PID) of any process listening on the specified port and then forcefully terminate that process. This is particularly useful when you intend to restart the service manually from a terminal to gain output visibility for troubleshooting or running monitoring, or if convenience scripts fail.

*   **Backend Service (Port 8000)**:
    To find and kill the process running on port 8000:
    ```bash
    lsof -t -i:8000 | xargs kill -9
    ```
    This command finds the process ID (PID) listening on port 8000 and then forcefully terminates it.

*   **Frontend Dashboard (Port 3000)**:
    To find and kill the process running on port 3000:
    ```bash
    lsof -t -i:3000 | xargs kill -9
    ```
    This command finds the process ID (PID) listening on port 3000 and then forcefully terminates it.

### Starting Individual Services Manually (with Hot Reload)

To start services with direct log output and hot-reloading capabilities (useful for development):

*   **Hindsight Service (Backend)**:
    Navigate to the `apps/hindsight-service` directory and run:
    ```bash
    cd apps/hindsight-service
    uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The `--reload` flag enables hot-reloading, meaning the server will automatically restart when code changes are detected. Logs will be visible directly in your terminal.

*   **Hindsight Dashboard (Frontend)**:
    If you prefer running the Vite dev server directly with HMR, set the API base and start:
    ```bash
    cd apps/hindsight-dashboard
    npm install
    VITE_HINDSIGHT_SERVICE_API_URL=http://localhost:8000 npm run dev
    ```
    Docker-based dev is recommended since it proxies `/api` automatically. When running Vite dev directly, the env override is required.

## More Detailed Documentation

More detailed documentation for individual components can be found in their respective `README.md` files:
- For `hindsight-dashboard`: `apps/hindsight-dashboard/README.md`
- For `hindsight-service`: `apps/hindsight-service/README.md`

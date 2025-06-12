# Hindsight AI Monorepo

This repository contains the complete Hindsight AI project, a system designed to enhance AI agent memory and operational intelligence. It is structured as a monorepo to manage related applications and infrastructure components efficiently.

## Purpose

Hindsight AI aims to provide a robust and scalable solution for:
- **Memory Management:** Storing, retrieving, and managing an AI agent's conversational and operational memories.
- **Knowledge Distillation:** Extracting actionable insights and lessons learned from raw interactions.
- **Continuous Improvement:** Enabling AI agents to learn from past experiences and improve their performance over time.

## Overall Architecture

The monorepo is organized into two primary top-level directories:

-   **`apps/`**: Contains individual applications that form the Hindsight AI system.
    -   [`hindsight-dashboard`](apps/hindsight-dashboard/README.md): The frontend application for visualizing and interacting with the memory service.
    -   [`hindsight-service`](apps/hindsight-service/README.md): The core backend service responsible for managing AI agent memories, keyword extraction, and database interactions.
-   **`infra/`**: Contains infrastructure-related components and configurations.
    -   `postgres`: Docker Compose setup for the PostgreSQL database.
    -   `migrations`: SQL scripts for initial database schema setup.
-   **`mcp-servers/`**: Contains Model Context Protocol (MCP) servers that extend AI agent capabilities.
    -   [`hindsight-mcp`](mcp-servers/hindsight-mcp/README.md): An MCP server providing tools for interacting with the Hindsight AI Agent Memory Service.

These components are designed to integrate seamlessly, with the `hindsight-service` interacting with the PostgreSQL database and exposing an API consumed by the `hindsight-dashboard`.

## Quick Start Guide

For a quick setup and teardown of all Hindsight AI services, use the provided convenience scripts:

*   **Start All Services**: `./start_hindsight.sh`
    This script automates the setup and launch of all Hindsight AI components:
    1.  **PostgreSQL Database**: Starts the database using Docker Compose.
    2.  **Database Migrations**: Applies necessary database schema migrations for the backend service.
    3.  **Backend Service**: Launches the Python FastAPI backend on `http://localhost:8000`.
    4.  **Frontend Dashboard**: Starts the React development server for the dashboard on `http://localhost:3000`.
    The script includes checks to prevent starting services that are already running.
*   **Stop All Services**: `./stop_hindsight.sh`
    This script will gracefully terminate processes listening on ports 3000 and 8000, and shut down the Dockerized PostgreSQL database.

For detailed, step-by-step setup, continue with the instructions below:

To set up and run the entire Hindsight AI project locally, follow these steps:

1.  **Prerequisites**:
    *   Docker and Docker Compose
    *   Python 3.13+ and `uv` (or `pipenv`/`poetry`)
    *   Node.js and npm (or yarn)

2.  **Clone the Repository**:
    ```bash
    git clone https://github.com/your-repo/hindsight-ai.git
    cd hindsight-ai
    ```

3.  **Set up Infrastructure (PostgreSQL)**:
    Navigate to the `infra/postgres` directory and start the database:
    ```bash
    cd infra/postgres
    docker-compose up -d
    ```
    Wait a few moments for the database to initialize.

4.  **Apply Initial Database Schema**:
    The initial schema is applied via SQL scripts. Ensure the database container is running.
    ```bash
    # You might need a tool like `psql` or a database client to apply this.
    # For example, if using psql from your host:
    # psql -h localhost -p 5432 -U user -d hindsight_db -f ../migrations/V1__initial_schema.sql
    # (Replace `user` with your configured user and `hindsight_db` with your database name if different)
    ```
    *Note: The `hindsight-service` will handle its own migrations via Alembic, but this initial schema sets up the database itself.*

5.  **Set up and Run Hindsight Service (Backend)**:
    Navigate to the `apps/hindsight-service` directory, install dependencies, and run the service:
    ```bash
    cd ../../apps/hindsight-service
    uv sync # or poetry install / pipenv install
    uv run uvicorn core.api.main:app --reload
    ```
    The backend service should now be running, typically on `http://localhost:8000`.

6.  **Set up and Run Hindsight Dashboard (Frontend)**:
    In a new terminal, navigate to the `apps/hindsight-dashboard` directory, install dependencies, and start the development server:
    ```bash
    cd ../../apps/hindsight-dashboard
    npm install # or yarn install
    npm start # or yarn start
    ```
    The frontend dashboard should open in your browser, typically on `http://localhost:3000`.

You now have the entire Hindsight AI system running locally.

## Manual Control and Troubleshooting

For development, debugging, or when you need to inspect logs directly, you might want to manually control individual services.

### Stopping Individual Services

While `./stop_hindsight.sh` stops all services, you can stop individual components manually:

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
    Navigate to the `apps/hindsight-dashboard` directory and run:
    ```bash
    cd apps/hindsight-dashboard
    npm start
    ```
    `npm start` typically includes hot-reloading by default for React applications, and logs will be displayed in your terminal.

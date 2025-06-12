#!/bin/bash

set -e

# Define paths
POSTGRES_DIR="infra/postgres"
BACKEND_DIR="apps/hindsight-service"
DASHBOARD_DIR="apps/hindsight-dashboard"

echo "Starting PostgreSQL database..."
if docker compose -f "${POSTGRES_DIR}/docker-compose.yml" ps -q postgres-db-1 &> /dev/null; then
    echo "PostgreSQL database is already running."
else
    (cd "${POSTGRES_DIR}" && docker compose up -d)
fi

echo "Applying database migrations..."
(cd "${BACKEND_DIR}" && uv sync && uv run alembic upgrade head)

echo "Starting backend service..."
if lsof -i:8000 -t >/dev/null ; then
    echo "Backend service is already running on port 8000."
else
    # Ensure uv is installed and activated for the backend service
    if ! command -v uv &> /dev/null
    then
        echo "uv (rye) could not be found. Please install it to run the backend service."
        echo "Refer to https://rye-up.com/guide/installation/ for installation instructions."
        exit 1
    fi
    (cd "${BACKEND_DIR}" && uv run uvicorn core.api.main:app --host 0.0.0.0 --port 8000 --reload > /dev/null 2>&1 &)
    sleep 1 # Give a moment for the process to start
    pgrep -f "uvicorn core.api.main:app" | tr '\n' ' ' > "${BACKEND_DIR}/.backend.pid"
fi

echo "Starting dashboard..."
if lsof -i:3000 -t >/dev/null ; then
    echo "Dashboard is already running on port 3000."
else
    (cd "${DASHBOARD_DIR}" && npm install && npm start > /dev/null 2>&1 &)
    sleep 1 # Give a moment for the process to start
    pgrep -f "npm start" | tr '\n' ' ' > "${DASHBOARD_DIR}/.dashboard.pid"
fi

echo "All Hindsight services started."
echo "PostgreSQL: Running via Docker Compose"
echo "Backend: http://localhost:8000"
echo "Dashboard: http://localhost:3000"

exit 0

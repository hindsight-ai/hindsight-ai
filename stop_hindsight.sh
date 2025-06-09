#!/bin/bash

set -e

# Define paths
POSTGRES_DIR="infra/postgres"
BACKEND_DIR="apps/hindsight-service"
DASHBOARD_DIR="apps/hindsight-dashboard"

echo "Stopping dashboard..."
PIDS_3000=$(lsof -t -i:3000 || true)
if [ -n "$PIDS_3000" ]; then
    echo "Killing processes on port 3000 (PIDs: $PIDS_3000)"
    for PID in $PIDS_3000; do
        kill "$PID" || true
    done
    sleep 1 # Give it a moment to terminate
else
    echo "No process found listening on port 3000."
fi
rm -f "${DASHBOARD_DIR}/.dashboard.pid" || true

echo "Stopping backend service..."
PIDS_8000=$(lsof -t -i:8000 || true)
if [ -n "$PIDS_8000" ]; then
    echo "Killing processes on port 8000 (PIDs: $PIDS_8000)"
    for PID in $PIDS_8000; do
        kill "$PID" || true
    done
    sleep 1 # Give it a moment to terminate
else
    echo "No process found listening on port 8000."
fi
rm -f "${BACKEND_DIR}/.backend.pid" || true

echo "Stopping PostgreSQL database..."
(cd "${POSTGRES_DIR}" && docker compose down)

echo "All Hindsight services stopped."

exit 0

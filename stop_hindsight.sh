#!/bin/bash

set -e

echo "Stopping Hindsight AI services..."

# Check if Docker Compose services are running
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "Stopping Docker Compose services..."
    docker compose -f docker-compose.yml -f docker-compose.dev.yml down
    echo "✅ Docker Compose services stopped."
else
    echo "No Docker Compose services found running."
fi

# Also stop any legacy processes that might be running on ports
echo "Checking for legacy processes on ports 3000 and 8000..."

# Stop dashboard on port 3000
PIDS_3000=$(lsof -t -i:3000 || true)
if [ -n "$PIDS_3000" ]; then
    echo "Killing legacy processes on port 3000 (PIDs: $PIDS_3000)"
    for PID in $PIDS_3000; do
        kill "$PID" || true
    done
    sleep 1
fi

# Stop backend on port 8000
PIDS_8000=$(lsof -t -i:8000 || true)
if [ -n "$PIDS_8000" ]; then
    echo "Killing legacy processes on port 8000 (PIDs: $PIDS_8000)"
    for PID in $PIDS_8000; do
        kill "$PID" || true
    done
    sleep 1
fi

# Clean up legacy PID files
rm -f "apps/hindsight-dashboard/.dashboard.pid" || true
rm -f "apps/hindsight-service/.backend.pid" || true

echo "All Hindsight services stopped."

exit 0

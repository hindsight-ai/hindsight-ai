#!/bin/bash

set -e

echo "Starting Hindsight AI services for local development..."
echo "Using Docker Compose with development profile..."

# Parse flags
WATCH_MODE=0
for arg in "$@"; do
  case "$arg" in
    -w|--watch)
      WATCH_MODE=1
      shift
      ;;
  esac
done

# Ensure .env exists for docker compose variable interpolation
if [ ! -f .env ]; then
    echo ".env not found. Creating it from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Update values as needed (e.g., LLM_API_KEY)."
    else
        echo "ERROR: .env.example is missing. Cannot create .env."
        exit 1
    fi
fi

# Check if services are already running
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "Hindsight AI services are already running."
    echo "To stop them, run: ./stop_hindsight.sh"
    exit 0
fi

# Get the current git commit SHA
BUILD_SHA=$(git rev-parse HEAD 2>/dev/null || echo "")

# Get current timestamp
BUILD_TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Get frontend version from package.json
FRONTEND_VERSION=$(cat apps/hindsight-dashboard/package.json | jq -r '.version' 2>/dev/null || echo)

# Get backend version from pyproject.toml
BACKEND_VERSION=$(cat apps/hindsight-service/pyproject.toml | grep -E "^version\s*=" | sed -E 's/version\s*=\s*"([^"]+)"$/\1/' || echo "unknown")

# Export environment variables for docker-compose
export BACKEND_BUILD_SHA="$BUILD_SHA"
export FRONTEND_BUILD_SHA="$BUILD_SHA"
export BUILD_TIMESTAMP
export BACKEND_IMAGE_TAG="hindsight-service:local"
export FRONTEND_IMAGE_TAG="hindsight-dashboard:local"
export BACKEND_VERSION
# Export both legacy CRA and Vite-style variables for compatibility
export REACT_APP_VERSION="$FRONTEND_VERSION"
export REACT_APP_BUILD_SHA="$BUILD_SHA"
export REACT_APP_BUILD_TIMESTAMP="$BUILD_TIMESTAMP"
export REACT_APP_DASHBOARD_IMAGE_TAG="hindsight-dashboard:local"

export VITE_VERSION="$FRONTEND_VERSION"
export VITE_BUILD_SHA="$BUILD_SHA"
export VITE_BUILD_TIMESTAMP="$BUILD_TIMESTAMP"
export VITE_DASHBOARD_IMAGE_TAG="hindsight-dashboard:local"

# Default to relative proxy (unset var so frontend uses '/api')
if [ -n "${VITE_HINDSIGHT_SERVICE_API_URL}" ]; then
  export VITE_HINDSIGHT_SERVICE_API_URL
else
  unset VITE_HINDSIGHT_SERVICE_API_URL
fi

# Start all services using Docker Compose with development profile
echo "Building and starting services..."
echo "Build SHA: $BUILD_SHA"
echo "Build Timestamp: $BUILD_TIMESTAMP"
echo "Frontend Version: $FRONTEND_VERSION"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check if services are running
if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo ""
    echo "✅ All Hindsight AI services started successfully!"
    echo ""
    echo "Services are accessible at:"
    echo "  🌐 Frontend Dashboard: http://localhost:3000"
    echo "  🔧 Backend API: http://localhost:8000"
    echo "  🗄️  Database: localhost:5432"
    echo ""
    # Show Copilot Assistant URL only if service is running
    if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps 2>/dev/null | grep -q "hindsight-copilot-assistant"; then
        if docker compose -f docker-compose.yml -f docker-compose.dev.yml ps | grep "hindsight-copilot-assistant" | grep -q "Up"; then
            echo "  🤖 Copilot Assistant: http://localhost:3001"
        fi
    fi
    echo ""
    echo "To view logs: docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f"
    echo "To stop services: ./stop_hindsight.sh"
    if [ $WATCH_MODE -eq 0 ]; then
      echo "For auto-rebuild on code changes, rerun with: ./start_hindsight.sh --watch"
    fi
else
    echo "❌ Failed to start services. Check logs with:"
    echo "docker compose -f docker-compose.yml -f docker-compose.dev.yml logs"
    exit 1
fi

# If watch mode requested, start compose watch (blocks until interrupted)
if [ $WATCH_MODE -eq 1 ]; then
  if docker compose watch --help >/dev/null 2>&1; then
    echo ""
    echo "🔁 Starting Docker Compose watch for code changes..."
    echo "Press Ctrl+C to stop watching; containers keep running."
    exec docker compose -f docker-compose.yml -f docker-compose.dev.yml watch
  else
    echo "⚠️ Your Docker Compose does not support 'watch'. Please update Compose or run manually:"
    echo "docker compose -f docker-compose.yml -f docker-compose.dev.yml watch"
  fi
fi

exit 0

#!/usr/bin/env bash

# Restart the frontend locally (Vite dev with HMR) while keeping backend/db running via Docker Compose.
# - If services are not running, it will start them via ./start_hindsight.sh
# - If the frontend container is running and binding :3000, it will stop only that container to free the port
# - It then starts the local Vite dev server on :3000 with auto reload
#
# Usage: ./restart_frontend_dev.sh
# Optional env:
#   FRONTEND_DEV_PORT (default: 3000)
#   FRONTEND_DIR (default: apps/hindsight-dashboard)

set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")" && pwd)
COMPOSE_FILES=(-f "$ROOT_DIR/docker-compose.yml" -f "$ROOT_DIR/docker-compose.dev.yml")
FRONTEND_SERVICE="hindsight-dashboard"
FRONTEND_DIR=${FRONTEND_DIR:-"$ROOT_DIR/apps/hindsight-dashboard"}
FRONTEND_DEV_PORT=${FRONTEND_DEV_PORT:-3000}

command_exists() { command -v "$1" >/dev/null 2>&1; }

log() { printf "\033[1;34m[frontend-dev]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[frontend-dev]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[frontend-dev]\033[0m %s\n" "$*"; }

ensure_prereqs() {
  if ! command_exists docker; then err "Docker is required."; exit 1; fi
  if ! command_exists npm; then err "Node.js/npm is required to run the Vite dev server."; exit 1; fi
}

compose() { docker compose "${COMPOSE_FILES[@]}" "$@"; }

services_up() {
  compose ps 2>/dev/null | grep -q "Up" && return 0 || return 1
}

frontend_container_running() {
  compose ps "$FRONTEND_SERVICE" 2>/dev/null | grep -q "Up" && return 0 || return 1
}

stop_frontend_container() {
  if frontend_container_running; then
    log "Stopping frontend container ($FRONTEND_SERVICE) to free port :$FRONTEND_DEV_PORT..."
    compose stop "$FRONTEND_SERVICE" >/dev/null
  else
    log "Frontend container is not running; nothing to stop."
  fi
}

kill_local_port() {
  local port="$1"
  # Try lsof then fallback to fuser
  if command_exists lsof; then
    local pids
    pids=$(lsof -ti tcp:"$port" -sTCP:LISTEN || true)
    if [ -n "$pids" ]; then
      warn "Killing local processes on :$port -> $pids"
      xargs -r kill -9 <<< "$pids" || true
    fi
  elif command_exists fuser; then
    if fuser -n tcp "$port" >/dev/null 2>&1; then
      warn "Killing local processes on :$port"
      fuser -k -n tcp "$port" || true
    fi
  else
    warn "Neither lsof nor fuser found; skipping explicit port cleanup."
  fi
}

start_services_if_needed() {
  if services_up; then
    log "Services appear to be running."
  else
    log "Starting services via ./start_hindsight.sh ..."
    (cd "$ROOT_DIR" && ./start_hindsight.sh || true)
  fi
}

start_vite_dev() {
  log "Starting Vite dev server with HMR on :$FRONTEND_DEV_PORT ..."
  log "Directory: $FRONTEND_DIR"
  cd "$FRONTEND_DIR"

  # Prefer existing node_modules; otherwise, install minimal deps
  if [ ! -d node_modules ]; then
    warn "node_modules not found; installing dependencies (npm ci || npm install) ..."
    if command_exists npm; then
      (npm ci || npm install)
    fi
  fi

  export VITE_DEV_MODE=true
  # Allow overriding API URL; default logic in http.ts falls back to /api or localhost:8000
  # export VITE_HINDSIGHT_SERVICE_API_URL="http://localhost:8000"  # Uncomment to force direct API

  # Run dev; keep attached so you get live reload
  npm run dev -- --port "$FRONTEND_DEV_PORT"
}

main() {
  ensure_prereqs
  start_services_if_needed
  stop_frontend_container
  kill_local_port "$FRONTEND_DEV_PORT"

  # Small delay to ensure the port is released
  sleep 0.5

  # Provide a hint on how to switch back to the containerized frontend
  trap 'warn "Vite dev stopped. To restore the containerized frontend: docker compose ${COMPOSE_FILES[*]} up -d $FRONTEND_SERVICE"' EXIT
  start_vite_dev
}

main "$@"

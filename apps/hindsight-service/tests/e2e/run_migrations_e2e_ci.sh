#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../../"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required to run E2E migration tests" >&2
  exit 1
fi

# Ensure pytest is available in the project env; prefer uv if present
if command -v uv >/dev/null 2>&1; then
  echo "Running E2E migration tests via uv+pytest"
  uv run --with pytest pytest -m e2e -k migrations_stepwise
else
  echo "uv not found; falling back to system Python"
  python -m pip install -U pip pytest >/dev/null
  pytest -m e2e -k migrations_stepwise
fi

echo "E2E migration tests completed"


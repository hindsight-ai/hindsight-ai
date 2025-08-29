#!/bin/bash
set -e

HOST="${DATABASE_URL#*@}"
HOST="${HOST%:*}"
PORT="${DATABASE_URL##*:}"
PORT="${PORT%%/*}"

echo "Waiting for PostgreSQL at $HOST:$PORT..."
until pg_isready -h "$HOST" -p "$PORT" -U "${DATABASE_URL#*//}"
do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing migrations"
uv sync
uv run alembic upgrade head

echo "Starting backend service"
exec "$@"

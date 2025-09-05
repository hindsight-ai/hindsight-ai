#!/bin/bash
set -e

# Ensure DATABASE_URL is provided
if [ -z "${DATABASE_URL}" ]; then
  echo "ERROR: DATABASE_URL environment variable is not set."
  exit 1
fi

echo "Waiting for PostgreSQL using DATABASE_URL..."
until pg_isready -d "${DATABASE_URL}" >/dev/null 2>&1; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - executing migrations"
if ! alembic upgrade head; then
  if [ "${DEV_MODE}" = "true" ]; then
    echo "Alembic migration failed in DEV_MODE. Resetting public schema and retrying..."
    psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" || {
      echo "Failed to reset schema"; exit 1; }
    alembic upgrade head || { echo "Migration still failing after reset"; exit 1; }
  else
    echo "Alembic migration failed (production mode). Exiting."
    exit 1
  fi
fi

echo "Starting backend service"
exec "$@"

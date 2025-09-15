#!/bin/bash
set -e

# Ensure DATABASE_URL is provided; if not, build it from POSTGRES_* envs commonly set by compose
if [ -z "${DATABASE_URL}" ]; then
  : "${POSTGRES_USER:=postgres}"
  : "${POSTGRES_PASSWORD:=postgres}"
  : "${POSTGRES_HOST:=db}"
  : "${POSTGRES_PORT:=5432}"
  : "${POSTGRES_DB:=hindsight_db}"
  export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"
  echo "INFO: DATABASE_URL not set, constructed from POSTGRES_* envs: ${DATABASE_URL}"
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

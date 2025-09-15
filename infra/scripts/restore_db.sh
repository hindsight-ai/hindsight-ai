#!/bin/bash

# Database connection details
DB_NAME="hindsight_db"
DB_USER="user"
DB_PASSWORD="password"
# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Define paths relative to the script's location
# Use the main docker-compose files to ensure the correct context for the 'db' service
DOCKER_COMPOSE_FILES="-f $SCRIPT_DIR/../../docker-compose.yml -f $SCRIPT_DIR/../../docker-compose.dev.yml -f $SCRIPT_DIR/../postgres/docker-compose.yml"
DB_SERVICE_NAME="db"
HINDSIGHT_SERVICE_DIR="$SCRIPT_DIR/../../apps/hindsight-service"

# Backup directory
BACKUP_DIR="$SCRIPT_DIR/../../hindsight_db_backups/data"

echo "Available backups:"
select BACKUP_FILE_PATH in "$BACKUP_DIR"/hindsight_db_backup_*.sql; do
  if [ -n "$BACKUP_FILE_PATH" ]; then
    echo "Selected backup: $BACKUP_FILE_PATH"
    break
  else
    echo "Invalid selection. Please try again."
  fi
done

echo "Stopping PostgreSQL container..."
docker compose $DOCKER_COMPOSE_FILES stop "$DB_SERVICE_NAME"

if [ $? -ne 0 ]; then
  echo "Failed to stop PostgreSQL container. Exiting."
  exit 1
fi

echo "Starting PostgreSQL container to ensure it's running for psql commands..."
docker compose $DOCKER_COMPOSE_FILES start "$DB_SERVICE_NAME"

if [ $? -ne 0 ]; then
  echo "Failed to start PostgreSQL container. Exiting."
  exit 1
fi

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
until docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up and running."

echo "Restoring database from $BACKUP_FILE_PATH..."

# Drop and recreate the database to ensure a clean restore
# This requires connecting as a superuser or a user with CREATE DATABASE privileges
# For simplicity, we'll use the same user, assuming it has sufficient privileges
# In a production environment, you might connect as 'postgres' user for this step
docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" \
  psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"

docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" \
  psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER \"$DB_USER\";"

if [ $? -ne 0 ]; then
  echo "Failed to drop/create database. Exiting."
  exit 1
fi

# Restore the database
docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" \
  psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE_PATH"

if [ $? -eq 0 ]; then
  echo "Database restoration successful."
else
  echo "Database restoration failed!"
  echo "Please check the logs for errors."
  exit 1
fi

echo "Running Alembic migrations to ensure schema is up-to-date..."

# Extract Alembic revision from the backup filename
# Filename format: hindsight_db_backup_YYYYMMDD_HHMMSS_ALEMBICREV.sql
ALEMBIC_REVISION=$(echo "$BACKUP_FILE_PATH" | grep -oE '[0-9a-f]{12}\.sql$' | sed 's/\.sql$//')

if [ -z "$ALEMBIC_REVISION" ] || [ "$ALEMBIC_REVISION" == "unknown" ]; then
  echo "Warning: Could not determine specific Alembic revision from backup filename. Attempting to upgrade to 'head'."
  TARGET_REVISION="head"
else
  echo "Migrating database to Alembic revision: $ALEMBIC_REVISION"
  TARGET_REVISION="$ALEMBIC_REVISION"
fi

# Run Alembic migrations inside the service container to avoid requiring local 'uv'
# This uses the compose configuration so the container has the correct env (DATABASE_URL)
# Run Alembic directly, bypassing the service entrypoint to avoid dev-mode resets
docker compose $DOCKER_COMPOSE_FILES run --rm --entrypoint "" hindsight-service \
  sh -lc "cd /app && uv run alembic upgrade \"$TARGET_REVISION\""

if [ $? -eq 0 ]; then
  echo "Alembic migrations applied successfully."
else
  echo "Alembic migrations failed! Please check the logs."
  exit 1
fi

echo "Database restore and migration process finished."

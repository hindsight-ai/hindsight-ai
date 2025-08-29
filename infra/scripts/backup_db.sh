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
HINDSIGHT_SERVICE_DIR="$SCRIPT_DIR/../../apps/hindsight-service" # Added for Alembic revision lookup

# Backup directory and file prefix
BACKUP_DIR="$SCRIPT_DIR/../../hindsight_db_backups/data"
FILENAME_PREFIX="hindsight_db_backup"
MAX_BACKUPS=100 # Configurable roll on 100 files

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "Starting PostgreSQL backup for database '$DB_NAME'..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL database to be ready..."
until docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is up and running."

# Get current Alembic revision
echo "Getting current Alembic revision..."
ALEMBIC_REVISION=$(cd "$HINDSIGHT_SERVICE_DIR" && uv run alembic current | grep -oE '[0-9a-f]{12}' | head -n 1)

if [ -z "$ALEMBIC_REVISION" ]; then
  echo "Warning: Could not determine Alembic revision. Backup will proceed without revision in filename."
  ALEMBIC_REVISION="unknown"
fi

BACKUP_FILE="$BACKUP_DIR/${FILENAME_PREFIX}_${TIMESTAMP}_${ALEMBIC_REVISION}.sql"
echo "Backup file will be: $BACKUP_FILE"

# Use docker exec to run pg_dump inside the container
# This ensures pg_dump uses the container's environment and connects directly to the service
docker compose $DOCKER_COMPOSE_FILES exec -T "$DB_SERVICE_NAME" \
  pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "Backup successful: $BACKUP_FILE"

  # Clean up old backups
  echo "Checking for old backups to remove..."
  cd "$BACKUP_DIR" || exit
  NUM_BACKUPS=$(ls -1 "${FILENAME_PREFIX}_"*.sql | wc -l)

  if [ "$NUM_BACKUPS" -gt "$MAX_BACKUPS" ]; then
    NUM_TO_REMOVE=$((NUM_BACKUPS - MAX_BACKUPS))
    echo "Found $NUM_BACKUPS backups, exceeding limit of $MAX_BACKUPS. Removing $NUM_TO_REMOVE oldest files."
    ls -1t "${FILENAME_PREFIX}_"*.sql | tail -n "$NUM_TO_REMOVE" | xargs rm --
    echo "Old backups removed."
  else
    echo "Number of backups ($NUM_BACKUPS) is within the limit ($MAX_BACKUPS)."
  fi
else
  echo "Backup failed!"
  exit 1
fi

echo "Backup process finished."

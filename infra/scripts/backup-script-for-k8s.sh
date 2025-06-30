#!/bin/bash

# This script creates a PostgreSQL database backup from a K3s cluster.

# --- Configuration ---
# Retrieve configuration from Kubernetes ConfigMap
CONFIG_MAP_NAME="postgres-backup-restore-config"

DB_NAME=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.DB_NAME}')
DB_USER=$(kubectl get secret postgres-secret -o jsonpath='{.data.POSTGRES_USER}' | base64 --decode)
DB_PASSWORD=$(kubectl get secret postgres-secret -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 --decode)
POSTGRES_SERVICE_HOST=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.POSTGRES_SERVICE_HOST}')
POSTGRES_SERVICE_PORT=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.POSTGRES_SERVICE_PORT}')
BACKUP_DIR=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.BACKUP_DIR_LOCAL}')
FILENAME_PREFIX=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.FILENAME_PREFIX}')
MAX_BACKUPS=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.MAX_BACKUPS}')

# Validate retrieved configurations
if [ -z "$DB_NAME" ] || \
   [ -z "$POSTGRES_SERVICE_HOST" ] || [ -z "$POSTGRES_SERVICE_PORT" ] || \
   [ -z "$BACKUP_DIR" ] || [ -z "$FILENAME_PREFIX" ] || [ -z "$MAX_BACKUPS" ]; then
  echo "Error: Failed to retrieve all necessary configurations from ConfigMap '$CONFIG_MAP_NAME'."
  echo "Please ensure the ConfigMap exists and contains all required keys (excluding DB_USER and DB_PASSWORD)."
  exit 1
fi

if [ -z "$DB_USER" ]; then
  echo "Error: Failed to retrieve DB_USER from Kubernetes Secret 'postgres-secret'."
  echo "Please ensure the Secret exists and contains the 'POSTGRES_USER' key."
  exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
  echo "Error: Failed to retrieve DB_PASSWORD from Kubernetes Secret 'postgres-secret'."
  echo "Please ensure the Secret exists and contains the 'POSTGRES_PASSWORD' key."
  exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate timestamp for filename
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo "Starting PostgreSQL backup for database '$DB_NAME' in Kubernetes..."

# Find the PostgreSQL pod name
echo "Finding PostgreSQL pod..."
POSTGRES_POD=$(kubectl get pods -l app=postgres -o jsonpath='{.items[0].metadata.name}')

if [ -z "$POSTGRES_POD" ]; then
  echo "Error: PostgreSQL pod not found. Ensure 'app=postgres' label is correct and pod is running."
  exit 1
fi

echo "Found PostgreSQL pod: $POSTGRES_POD"

# Wait for PostgreSQL to be ready inside the pod
echo "Waiting for PostgreSQL database to be ready in pod '$POSTGRES_POD'..."
until kubectl exec "$POSTGRES_POD" -- pg_isready -h "$POSTGRES_SERVICE_HOST" -p "$POSTGRES_SERVICE_PORT" -U "$DB_USER"; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is up and running."

BACKUP_FILE="$BACKUP_DIR/${FILENAME_PREFIX}_${TIMESTAMP}.sql"
echo "Backup file will be: $BACKUP_FILE"

# Use kubectl exec to run pg_dump inside the container and redirect output to a local file
kubectl exec "$POSTGRES_POD" -- env PGPASSWORD="$DB_PASSWORD" pg_dump -h "$POSTGRES_SERVICE_HOST" -p "$POSTGRES_SERVICE_PORT" -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
  echo "Backup successful: $BACKUP_FILE"

  # Clean up old backups
  echo "Checking for old backups to remove..."
  cd "$BACKUP_DIR" || exit
  NUM_BACKUPS=$(ls -1 "${FILENAME_PREFIX}_"*.sql 2>/dev/null | wc -l) # Added 2>/dev/null to suppress error if no files

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

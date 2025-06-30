#!/bin/bash

# This script restores a PostgreSQL database in a K3s cluster.
# It expects the path to the backup .sql file as its first argument.

# --- Configuration ---
# Retrieve configuration from Kubernetes ConfigMap
CONFIG_MAP_NAME="postgres-backup-restore-config"

DB_NAME=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.DB_NAME}')
DB_USER=$(kubectl get secret postgres-secret -o jsonpath='{.data.POSTGRES_USER}' | base64 --decode)
DB_PASSWORD=$(kubectl get secret postgres-secret -o jsonpath='{.data.POSTGRES_PASSWORD}' | base64 --decode)
POSTGRES_SERVICE_HOST=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.POSTGRES_SERVICE_HOST}')
POSTGRES_SERVICE_PORT=$(kubectl get configmap "$CONFIG_MAP_NAME" -o jsonpath='{.data.POSTGRES_SERVICE_PORT}')

# Validate retrieved configurations
if [ -z "$DB_NAME" ] || \
   [ -z "$POSTGRES_SERVICE_HOST" ] || [ -z "$POSTGRES_SERVICE_PORT" ]; then
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

# --- Input Validation ---
if [ -z "$1" ]; then
  echo "Usage: $0 <path_to_backup_file.sql>"
  exit 1
fi

BACKUP_FILE_PATH="$1"

if [ ! -f "$BACKUP_FILE_PATH" ]; then
  echo "Error: Backup file not found at '$BACKUP_FILE_PATH'"
  exit 1
fi

echo "Starting PostgreSQL database restoration in Kubernetes..."

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

echo "Restoring database '$DB_NAME' from '$BACKUP_FILE_PATH'..."

# Drop and recreate the database
# We connect to the 'postgres' default database to drop/create 'hindsight_db'
echo "Dropping existing database '$DB_NAME'..."
kubectl exec "$POSTGRES_POD" -- env PGPASSWORD="$DB_PASSWORD" psql -h "$POSTGRES_SERVICE_HOST" -p "$POSTGRES_SERVICE_PORT" -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME WITH (FORCE);"

echo "Creating new database '$DB_NAME'..."
kubectl exec "$POSTGRES_POD" -- env PGPASSWORD="$DB_PASSWORD" psql -h "$POSTGRES_SERVICE_HOST" -p "$POSTGRES_SERVICE_PORT" -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER \"$DB_USER\";"

if [ $? -ne 0 ]; then
  echo "Failed to drop/create database. Exiting."
  exit 1
fi

# Restore the database using kubectl exec and piping the backup file
echo "Importing data into '$DB_NAME'..."
cat "$BACKUP_FILE_PATH" | kubectl exec -i "$POSTGRES_POD" -- env PGPASSWORD="$DB_PASSWORD" psql -h "$POSTGRES_SERVICE_HOST" -p "$POSTGRES_SERVICE_PORT" -U "$DB_USER" -d "$DB_NAME"

if [ $? -eq 0 ]; then
  echo "Database restoration successful."
else
  echo "Database restoration failed! Please check the logs."
  exit 1
fi

echo "Database restore process finished."
echo "Note: Alembic migrations are typically handled by the application deployment (e.g., hindsight-service) itself."

#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
COMPOSE_FILE="$ROOT_DIR/docker-compose.app.yml"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

usage() {
  cat <<'USAGE'
Usage: restore_db.sh [--file path/to/backup.sql] [--dry-run]

Drops and recreates the database, restores the selected backup, and reapplies migrations.

Options:
  --file PATH  Use the specified SQL dump instead of prompting.
  --dry-run    Print the commands that would run without executing them.
  -h, --help   Show this help message.
USAGE
}

DRY_RUN=0
BACKUP_FILE_PATH=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "--file requires a path argument" >&2
        usage >&2
        exit 1
      fi
      BACKUP_FILE_PATH="$1"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "docker-compose.app.yml not found at $COMPOSE_FILE" >&2
  exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

DB_NAME="${POSTGRES_DB:-${DB_NAME:-hindsight_db}}"
DB_USER="${POSTGRES_USER:-${DB_USER:-user}}"
DB_PASSWORD="${POSTGRES_PASSWORD:-${DB_PASSWORD:-password}}"
DB_SERVICE_NAME="${DB_SERVICE_NAME:-db}"
BACKUP_DIR_DEFAULT="$ROOT_DIR/hindsight_db_backups/data"

if [[ -z "$BACKUP_FILE_PATH" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    BACKUP_FILE_PATH="$BACKUP_DIR_DEFAULT/<selected_backup.sql>"
  else
    mapfile -t backups < <(ls -1 "$BACKUP_DIR_DEFAULT"/hindsight_db_backup_*.sql 2>/dev/null || true)
    if [[ ${#backups[@]} -eq 0 ]]; then
      echo "No backup files found in $BACKUP_DIR_DEFAULT" >&2
      exit 1
    fi
    echo "Available backups:" >&2
    select choice in "${backups[@]}"; do
      if [[ -n "$choice" ]]; then
        BACKUP_FILE_PATH="$choice"
        if [[ ! -f "$BACKUP_FILE_PATH" && -f "$BACKUP_DIR_DEFAULT/${choice##*/}" ]]; then
          BACKUP_FILE_PATH="$BACKUP_DIR_DEFAULT/${choice##*/}"
        fi
        if [[ ! -f "$BACKUP_FILE_PATH" ]]; then
          echo "Selected backup not found: $choice" >&2
          continue
        fi
        break
      else
        echo "Invalid selection. Please try again." >&2
      fi
    done
  fi
else
  if [[ ! -f "$BACKUP_FILE_PATH" ]]; then
    echo "Backup file not found: $BACKUP_FILE_PATH" >&2
    exit 1
  fi
fi

PG_ENV=()
if [[ -n "$DB_PASSWORD" ]]; then
  PG_ENV=(-e "PGPASSWORD=$DB_PASSWORD")
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat <<EOF
[dry-run] Compose file: $COMPOSE_FILE
[dry-run] Would stop database container: docker compose -f $COMPOSE_FILE stop $DB_SERVICE_NAME
[dry-run] Would start database container: docker compose -f $COMPOSE_FILE up -d $DB_SERVICE_NAME
[dry-run] Would wait for pg_isready on database '$DB_NAME' as user '$DB_USER'.
[dry-run] Would drop and recreate database '$DB_NAME' using psql commands.
[dry-run] Would restore from: $BACKUP_FILE_PATH
[dry-run] Would run migrations via: docker compose -f $COMPOSE_FILE run --rm --entrypoint "" hindsight-service "sh -lc 'cd /app && uv run alembic upgrade <revision>'"
EOF
  exit 0
fi

BACKUP_REVISION=$(echo "$BACKUP_FILE_PATH" | grep -oE '[0-9a-f]{12}\.sql$' | sed 's/\.sql$//')
if [[ -z "$BACKUP_REVISION" || "$BACKUP_REVISION" == "unknown" ]]; then
  TARGET_REVISION="head"
else
  TARGET_REVISION="$BACKUP_REVISION"
fi

echo "Stopping PostgreSQL container..."
docker compose -f "$COMPOSE_FILE" stop "$DB_SERVICE_NAME" >/dev/null || true

echo "Starting PostgreSQL container..."
docker compose -f "$COMPOSE_FILE" up -d "$DB_SERVICE_NAME" >/dev/null

echo "Waiting for PostgreSQL database '$DB_NAME'..."
until docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  sleep 1
done

echo "Dropping database '$DB_NAME'..."
if [[ ${#PG_ENV[@]} -gt 0 ]]; then
  docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE);"
else
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE);"
fi

echo "Recreating database '$DB_NAME'..."
if [[ ${#PG_ENV[@]} -gt 0 ]]; then
  docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
else
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE \"$DB_NAME\" OWNER \"$DB_USER\";"
fi

echo "Restoring backup: $BACKUP_FILE_PATH"
if [[ ${#PG_ENV[@]} -gt 0 ]]; then
  docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE_PATH"
else
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE_NAME" psql -U "$DB_USER" -d "$DB_NAME" < "$BACKUP_FILE_PATH"
fi

echo "Applying migrations (target revision: $TARGET_REVISION)..."
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "" hindsight-service \
  sh -lc "cd /app && uv run alembic upgrade \"$TARGET_REVISION\""

echo "Restore complete."

exit 0

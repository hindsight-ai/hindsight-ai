#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ROOT_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
COMPOSE_FILE="$ROOT_DIR/docker-compose.app.yml"
ENV_FILE="${ENV_FILE:-$ROOT_DIR/.env}"

usage() {
  cat <<'USAGE'
Usage: backup_db.sh [--dry-run]

Creates a timestamped PostgreSQL dump inside hindsight_db_backups/data/.

Options:
  --dry-run   Print the commands that would run without executing them.
  -h, --help  Show this help message.
USAGE
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
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
FILENAME_PREFIX="${FILENAME_PREFIX:-hindsight_db_backup}"
MAX_BACKUPS="${MAX_BACKUPS:-100}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/hindsight_db_backups/data}"
TIMESTAMP="$(date +"%Y%m%d_%H%M%S")"

if [[ "$DRY_RUN" -eq 1 ]]; then
  cat <<EOF
[dry-run] Compose file: $COMPOSE_FILE
[dry-run] Would ensure backup directory exists: $BACKUP_DIR
[dry-run] Would start database container: docker compose -f $COMPOSE_FILE up -d $DB_SERVICE_NAME
[dry-run] Would wait for pg_isready on database '$DB_NAME' as user '$DB_USER'.
[dry-run] Would determine Alembic revision with: docker compose -f $COMPOSE_FILE run --rm --entrypoint "" hindsight-service "sh -lc 'cd /app && uv run alembic current'"
[dry-run] Would write dump to: $BACKUP_DIR/${FILENAME_PREFIX}_${TIMESTAMP}_<revision>.sql
[dry-run] Would prune backups above limit $MAX_BACKUPS.
EOF
  exit 0
fi

mkdir -p "$BACKUP_DIR"

docker compose -f "$COMPOSE_FILE" up -d "$DB_SERVICE_NAME" >/dev/null

echo "Waiting for PostgreSQL database '$DB_NAME'..."
PG_ENV=()
if [[ -n "$DB_PASSWORD" ]]; then
  PG_ENV=(-e "PGPASSWORD=$DB_PASSWORD")
fi
until docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" pg_isready -U "$DB_USER" -d "$DB_NAME" >/dev/null 2>&1; do
  sleep 1
done

echo "Database is ready. Determining Alembic revision..."
ALEMBIC_RAW=$(docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "" hindsight-service \
  sh -lc "cd /app && uv run alembic current" 2>/dev/null || true)
ALEMBIC_REVISION=$(echo "$ALEMBIC_RAW" | grep -oE '[0-9a-f]{12}' | head -n 1)
if [[ -z "$ALEMBIC_REVISION" ]]; then
  ALEMBIC_REVISION="unknown"
  echo "Warning: Could not determine Alembic revision; proceeding with 'unknown'."
fi

BACKUP_FILE="$BACKUP_DIR/${FILENAME_PREFIX}_${TIMESTAMP}_${ALEMBIC_REVISION}.sql"
echo "Creating backup: $BACKUP_FILE"
if [[ ${#PG_ENV[@]} -gt 0 ]]; then
  docker compose -f "$COMPOSE_FILE" exec -T "${PG_ENV[@]}" "$DB_SERVICE_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"
else
  docker compose -f "$COMPOSE_FILE" exec -T "$DB_SERVICE_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" > "$BACKUP_FILE"
fi

echo "Backup successful: $BACKUP_FILE"

mapfile -t backups < <(ls -1t "$BACKUP_DIR"/${FILENAME_PREFIX}_*.sql 2>/dev/null || true)
NUM_BACKUPS=${#backups[@]}
if (( NUM_BACKUPS > MAX_BACKUPS )); then
  TO_REMOVE=$((NUM_BACKUPS - MAX_BACKUPS))
  echo "Pruning $TO_REMOVE old backup(s)."
  for (( i=MAX_BACKUPS; i<NUM_BACKUPS; i++ )); do
    echo "Removing ${backups[i]}"
    rm -f "${backups[i]}"
  done
else
  echo "Backup retention within limit ($NUM_BACKUPS/$MAX_BACKUPS)."
fi

exit 0

# Infrastructure Setup and Migrations

Infra for local dev and prod: PostgreSQL, initial schema, migrations, and DB backup/restore.

Contents
- `migrations/` — initial SQL schema; subsequent changes are Alembic migrations in `apps/hindsight-service/migrations/`
- `postgres/` — standalone Docker Compose for DB only
- `scripts/` — DB backup/restore helpers

Most users don’t need to touch this directly — running `./start_hindsight.sh` at repo root brings up everything for local development.

## Database Only (optional)

Start Postgres alone if you want to run the API without Docker:
```bash
cd infra/postgres
docker compose up -d
```

## Initial Schema and Migrations

- First creation uses `infra/migrations/V1__initial_schema.sql`.
- Ongoing changes are managed by Alembic from `apps/hindsight-service`.

Apply initial SQL inside the DB container (if you’re bootstrapping manually):
```bash
CONTAINER_ID=$(docker ps --filter "name=db" --format "{{.ID}}")
PGPASSWORD=password docker exec -i "$CONTAINER_ID" \
  psql -U postgres -d hindsight_db < infra/migrations/V1__initial_schema.sql
```

## Backup and Restore

See the full guide: `apps/hindsight-service/docs/DATABASE_BACKUP.md` — covers timestamped dumps, restore flow, Alembic revision matching, and cron.

Important: On a fresh database, current Alembic migrations may not apply cleanly. The recommended way to get a working environment is to run:
```bash
./infra/scripts/restore_db.sh
```
and select the provided backup in `hindsight_db_backups/data/…sql`.

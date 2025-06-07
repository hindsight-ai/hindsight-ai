# Alembic Migrations for Hindsight Service

This directory contains the Alembic migration scripts for the `hindsight-service` database. Alembic is a lightweight database migration tool for SQLAlchemy.

## Purpose

Alembic migrations are used to manage changes to the database schema over time. Each migration script represents a set of changes (e.g., adding a table, modifying a column) that can be applied or reverted.

## How to Use

The `alembic.ini` configuration file in the `apps/hindsight-service` root directory controls Alembic. All Alembic commands should be run from the `apps/hindsight-service` directory.

### 1. Generate a New Migration Script

When you make changes to your SQLAlchemy models (e.g., in `apps/hindsight-service/core/db/models.py`), you need to generate a new migration script to reflect these changes in the database schema.

```bash
cd apps/hindsight-service
alembic revision --autogenerate -m "descriptive_message_for_changes"
```
Replace `"descriptive_message_for_changes"` with a brief, meaningful description of the changes you've made (e.g., "add user table", "rename memory_id to id"). This will create a new Python file in the `versions/` directory within this `migrations` folder. Review the generated script to ensure it accurately captures your intended changes.

### 2. Apply Migrations to the Database

To apply pending migration scripts to your database, use the `upgrade` command. This will bring your database schema up to the latest version defined by your migration scripts.

```bash
cd apps/hindsight-service
alembic upgrade head
```
This command will apply all unapplied migrations in chronological order.

### 3. Revert Migrations (Downgrade)

If you need to revert a migration (e.g., to fix an issue or roll back a change), you can use the `downgrade` command.

To revert the last applied migration:
```bash
cd apps/hindsight-service
alembic downgrade -1
```

To downgrade to a specific revision (e.g., `a17d8c8efa28`):
```bash
cd apps/hindsight-service
alembic downgrade a17d8c8efa28
```
Use `alembic history` to see the revision IDs and their order.

### Important Notes:

*   **Database Connection:** Ensure your database is running and accessible according to the configuration in `alembic.ini` (which typically pulls connection details from environment variables or a `.env` file).
*   **Review Generated Scripts:** Always review the auto-generated migration scripts before applying them, especially in production environments. Alembic's autogenerate feature is powerful but may not always capture complex changes perfectly.
*   **Initial Schema:** This Alembic setup manages schema changes *after* the initial database setup. For the very first database schema creation, refer to the `infra/migrations/V1__initial_schema.sql` script and the `infra/README.md` for instructions on setting up the base database.

# PostgreSQL Database Persistence and Backup Guide

This document explains how your PostgreSQL database data is kept safe and how you can create backups to prevent data loss, especially for the `hindsight_db` used by the `memory-service`.

## 1. Understanding Data Persistence with Docker Volumes

When you run the PostgreSQL database using `docker-compose.yml` (located at `infra/postgres/docker-compose.yml`), your data is stored in something called a "Docker Volume."

**What is a Docker Volume?**
Imagine a Docker container as a temporary, isolated box where your application runs. If you just store data inside this box, it disappears when the box is closed or thrown away (i.e., when the container is removed). A Docker Volume is like a special, persistent storage area on your computer's hard drive that is *outside* of the temporary container.

**How it works in `docker-compose.yml`:**
In our `docker-compose.yml` file, you'll see a section like this:

```yaml
services:
  db:
    # ... other configurations ...
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

*   `- db_data:/var/lib/postgresql/data`: This line tells Docker to connect our named volume `db_data` (which is defined later in the file) to the `/var/lib/postgresql/data` directory *inside* the PostgreSQL container. This is where PostgreSQL stores all its actual database files.
*   `volumes: db_data:`: This section formally declares `db_data` as a named volume. Docker manages this volume for you.

**What this means for your data:**
Because your data is stored in the `db_data` named volume, it will **persist** (remain safe) even if:
*   You stop and start the PostgreSQL container (`docker compose stop db` then `docker compose start db`).
*   You remove and recreate the PostgreSQL container (`docker compose rm db` then `docker compose up -d db`).

**When data might be lost:**
Your data will only be lost if you explicitly remove the Docker volume itself. This usually happens if you run commands like:
*   `docker volume rm db_data` (removes the specific volume)
*   `docker compose down -v` (removes all volumes associated with the `docker-compose.yml` file)

To protect against accidental removal of the volume, it's crucial to create backups.

## 2. Automated Database Backup and Restore

To simplify database backup and restoration, two shell scripts have been created: `backup_db.sh` and `restore_db.sh`. These scripts are located in `infra/scripts/`.

### 2.1. Backup Script (`infra/scripts/backup_db.sh`)

This script automates the process of creating a timestamped backup of the `hindsight_db` database. It also captures the current Alembic migration revision and includes it in the backup filename. It manages old backups, ensuring only a configurable number of recent backups are kept.

*   **Location:** `infra/scripts/backup_db.sh`
*   **Backup Storage:** Backups are stored in `./hindsight_db_backups/data/`.
*   **Filename Format:** Backups are named `hindsight_db_backup_YYYYMMDD_HHMMSS_ALEMBICREV.sql`. The `ALEMBICREV` is the 12-character hexadecimal revision ID of the database schema at the time of backup. If the revision cannot be determined, `unknown` will be used.
*   **File Roll:** The script is configured to keep a maximum of `100` backup files by default. When a new backup is created, if the total number of backups exceeds this limit, the oldest files are automatically removed. This `MAX_BACKUPS` value can be changed by editing the `infra/scripts/backup_db.sh` script.

**How to use:**

1.  **Ensure the script is executable:**
    ```bash
    chmod +x infra/scripts/backup_db.sh
    ```
    (This should have been done automatically during setup.)

2.  **Run a manual backup:**
    ```bash
    ./infra/scripts/backup_db.sh
    ```
    This will create a new backup file (e.g., `hindsight_db_backup_20250609_213000_2a9c8674c949.sql`) in the `./hindsight_db_backups/data/` directory.

### 2.2. Restore Script (`infra/scripts/restore_db.sh`)

This script allows you to restore the `hindsight_db` database from a previously created backup file. It handles stopping and starting the PostgreSQL container and running Alembic migrations to ensure the database schema is precisely aligned with the backup.

*   **Location:** `infra/scripts/restore_db.sh`

**How to use:**

1.  **Ensure the script is executable:**
    ```bash
    chmod +x infra/scripts/restore_db.sh
    ```
    (This should have been done automatically during setup.)

2.  **Run the restore process:**
    ```bash
    ./infra/scripts/restore_db.sh
    ```
    The script will list all available backup files in `./hindsight_db_backups/data/` and prompt you to select which one to restore.
    It will then:
    *   Stop the `db` Docker container.
    *   Drop and recreate the `hindsight_db` database.
    *   Restore the selected backup into the `hindsight_db`.
    *   Start the `db` Docker container.
    *   **Crucially, it extracts the Alembic revision from the selected backup filename and runs `uv run alembic upgrade <extracted_revision>` to migrate the database to the exact schema version that existed when the backup was taken.** If the revision cannot be determined, it will attempt to upgrade to `head`.

    **Important Note:** Restoring a database will **overwrite** the current data in the `hindsight_db` database. Use with caution, especially in production environments.

### 2.3. Automating Hourly Backups with Cron Jobs (Linux/macOS)

To ensure regular, automatic backups, you can schedule the `backup_db.sh` script to run hourly using a "cron job."

**How to set up an hourly backup:**

1.  **Open your crontab for editing.**
    In your terminal, type:
    ```bash
    crontab -e
    ```
    This will open a text editor (often `nano` or `vi`) where you can add your scheduled tasks.

2.  **Add the backup command.**
    Add the following line to the end of the file:

    ```cron
    0 * * * * /home/jean/git/hindsight-ai/infra/scripts/backup_db.sh >> /home/jean/hindsight_db_backups/logs/backup.log 2>&1
    ```

    **Explanation of the cron entry:**
    *   `0 * * * *`: This is the schedule part. It means:
        *   `0`: At minute 0 (the start of the hour)
        *   `*`: Every hour
        *   `*`: Every day of the month
        *   `*`: Every month
        *   `*`: Every day of the week
        So, this job will run every hour at the start of the hour (e.g., 1:00, 2:00, 3:00, etc.).
    *   `./infra/scripts/backup_db.sh`: This is the relative path to the backup script.
    *   `>> ./hindsight_db_backups/logs/backup.log`: This redirects the standard output of the script to a log file, appending new output to the end of the file. You might need to create the `logs` directory first: `mkdir -p ./hindsight_db_backups/logs`.
    *   `2>&1`: This redirects any error messages (standard error) to the same log file as the regular output. This is useful for debugging if your cron job doesn't work as expected.

3.  **Save and exit the crontab editor.**
    *   If using `nano`: Press `Ctrl+X`, then `Y` to confirm saving, then `Enter`.
    *   If using `vi`: Press `Esc`, then type `:wq` and press `Enter`.

Your cron job is now set up! It will automatically create hourly backups. Remember to create the `logs` directory: `mkdir -p ./hindsight_db_backups/logs`.

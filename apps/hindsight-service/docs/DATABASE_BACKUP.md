# PostgreSQL Database Persistence and Backup Guide

This document explains how your PostgreSQL database data is kept safe and how you can create backups to prevent data loss, especially for the `memory_db` used by the `memory-service`.

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

## 2. Creating Backups of Your PostgreSQL Database (`pg_dump`)

`pg_dump` is a command-line utility that comes with PostgreSQL. It allows you to "dump" (export) the contents of a PostgreSQL database into a single file, usually a `.sql` file. This file contains all the commands needed to recreate your database, including its structure (tables, indexes, etc.) and all your data.

### How to Perform a Manual Backup

You can run `pg_dump` from your computer's terminal. The easiest way is to run it directly from your running PostgreSQL Docker container.

**Step-by-step guide:**

1.  **Ensure your PostgreSQL container is running.** You can check its status with:
    ```bash
    docker ps
    ```
    Look for a container named something like `infra-db-1` or similar, with `postgres:13` as its image. Note down its `CONTAINER ID` or `NAMES`.

2.  **Execute the `pg_dump` command.**
    Open your terminal and run the following command. Replace `<container_id_or_name>` with the actual ID or name you found in the previous step.

    ```bash
    docker exec -t <container_id_or_name> pg_dump -U user memory_db > backup_$(date +%Y%m%d_%H%M%S).sql
    ```

    **Let's break down this command:**
    *   `docker exec -t <container_id_or_name>`: This tells Docker to run a command *inside* your specified container. `-t` allocates a pseudo-TTY, which is good practice.
    *   `pg_dump`: This is the PostgreSQL backup utility.
    *   `-U user`: This specifies the username to connect to the database. In our `docker-compose.yml`, the `POSTGRES_USER` is `user`.
    *   `memory_db`: This is the name of the database you want to back up. In our `docker-compose.yml`, the `POSTGRES_DB` is `memory_db`.
    *   `>`: This is a standard Linux/macOS shell operator that redirects the output of the `pg_dump` command (which is the SQL dump) into a file.
    *   `backup_$(date +%Y%m%d_%H%M%S).sql`: This creates a unique filename for your backup.
        *   `backup_`: A prefix for your backup file.
        *   `$(date +%Y%m%d_%H%M%S)`: This part automatically generates the current date and time (YearMonthDay_HourMinuteSecond), making each backup file unique (e.g., `backup_20250607_130000.sql`).
        *   `.sql`: The standard file extension for SQL dump files.

    After running this command, you will find a new `.sql` file in the directory where you executed the command. This file is your database backup!

### Automating Backups with Cron Jobs (Linux/macOS)

For regular, automatic backups, you can use a "cron job." A cron job is a task that your operating system (Linux or macOS) runs automatically at a scheduled time or interval.

**What is a Cron Job?**
Think of it as a built-in alarm clock for your computer that can run specific commands. You tell it *when* to run and *what* command to run.

**Step-by-step guide to set up a daily backup:**

1.  **Open your crontab for editing.**
    In your terminal, type:
    ```bash
    crontab -e
    ```
    This will open a text editor (often `nano` or `vi`) where you can add your scheduled tasks.

2.  **Add the backup command.**
    Add the following line to the end of the file. Remember to replace `<container_id_or_name>` with your actual container ID/name and `/path/to/your/backups/` with the directory where you want to store your backup files.

    ```cron
    0 2 * * * docker exec -t <container_id_or_name> pg_dump -U user memory_db > /path/to/your/backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql 2>&1
    ```

    **Explanation of the cron entry:**
    *   `0 2 * * *`: This is the schedule part. It means:
        *   `0`: At minute 0 (the start of the hour)
        *   `2`: At hour 2 (2 AM)
        *   `*`: Every day of the month
        *   `*`: Every month
        *   `*`: Every day of the week
        So, this job will run every day at 2:00 AM.
    *   `docker exec -t <container_id_or_name> pg_dump -U user memory_db`: This is the same `pg_dump` command we used for manual backup.
    *   `> /path/to/your/backups/backup_$(date +\%Y\%m\%d_\%H\%M\%S).sql`: This redirects the output to a file in your specified backup directory. Note the `\%` before `Y`, `m`, `d`, `H`, `M`, `S` – this is important in cron jobs to prevent `%` from being interpreted as a newline.
    *   `2>&1`: This redirects any error messages (standard error) to the same place as the regular output (standard output). This is useful for debugging if your cron job doesn't work as expected, as errors will be logged.

3.  **Save and exit the crontab editor.**
    *   If using `nano`: Press `Ctrl+X`, then `Y` to confirm saving, then `Enter`.
    *   If using `vi`: Press `Esc`, then type `:wq` and press `Enter`.

Your cron job is now set up! It will automatically create backups at the scheduled time.

## 3. Restoring Your PostgreSQL Database from a Backup (`psql`)

If you ever need to restore your database from a backup file, you can use the `psql` command-line utility. `psql` is a terminal-based front-end to PostgreSQL.

**Step-by-step guide:**

1.  **Ensure your PostgreSQL container is running.** (Same as step 1 for backup).

2.  **Restore the database.**
    Open your terminal and run the following command. Replace `<container_id_or_name>` with your actual container ID/name and `backup_file.sql` with the name of your backup file.

    ```bash
    docker exec -i <container_id_or_name> psql -U user memory_db < backup_file.sql
    ```

    **Let's break down this command:**
    *   `docker exec -i <container_id_or_name>`: Runs a command inside your container. `-i` keeps `STDIN` open, which is necessary for piping a file into the command.
    *   `psql`: The PostgreSQL interactive terminal.
    *   `-U user`: Specifies the username (`user`).
    *   `memory_db`: Specifies the database name (`memory_db`).
    *   `< backup_file.sql`: This is a standard Linux/macOS shell operator that redirects the content of `backup_file.sql` as input to the `psql` command. `psql` will then execute all the SQL commands in the file, effectively restoring your database.

    **Important Note:** Restoring a database typically overwrites existing data in the target database. Be careful when restoring, especially in production environments. You might want to create a fresh, empty database or drop the existing one before restoring if you want a clean slate.

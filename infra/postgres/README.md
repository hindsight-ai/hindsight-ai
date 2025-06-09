# PostgreSQL Database Setup with Docker Compose

This directory contains the `docker-compose.yml` file for setting up and managing the PostgreSQL database instance required by the Hindsight AI `hindsight-service`.

## Purpose

Using Docker Compose simplifies the process of running a local PostgreSQL database without needing to install PostgreSQL directly on your host machine. This setup ensures a consistent and isolated database environment for development and testing.

## How to Use

### 1. Start the PostgreSQL Container

Navigate to this directory (`infra/postgres`) and run the following command to start the PostgreSQL database in the background:

```bash
docker compose up -d
```
This will pull the PostgreSQL Docker image (if not already present) and start a container named `hindsight-ai-db` (or similar, as defined in `docker-compose.yml`).

### 2. Verify the Database is Running

You can check the status of the running container:

```bash
docker ps
```
Look for a container with an image like `postgres:latest` and a name related to `hindsight-ai-db`.

### 3. Stop the PostgreSQL Container

To stop the database container without removing its data:

```bash
docker compose stop
```

To stop and remove the container and its associated volumes (which means losing all data in the database):

```bash
docker compose down -v
```
**Use `docker compose down -v` with caution, as it will delete all your database data.**

### 4. Accessing the Database (Optional)

You can connect to the running PostgreSQL database using `psql` or another database client.

First, find the container ID:
```bash
docker ps --filter "name=hindsight-ai-db" --format "{{.ID}}"
```
Then, connect using `psql` from your host machine (assuming `psql` is installed):
```bash
psql -h localhost -p 5432 -U user -d hindsight_db
```
*   **Host**: `localhost` (or the IP address of your Docker host)
*   **Port**: `5432` (default PostgreSQL port)
*   **User**: `user` (as defined in `docker-compose.yml`)
*   **Database**: `hindsight_db` (as defined in `docker-compose.yml`)

Alternatively, you can execute `psql` directly inside the container:
```bash
docker exec -it [CONTAINER_ID] psql -U user hindsight_db
```
Replace `[CONTAINER_ID]` with the actual ID obtained from `docker ps`.

### Default Credentials

The `docker-compose.yml` file defines the default credentials for the PostgreSQL database. For this setup, the default user is `user` and the password is `password`. The database name is `hindsight_db`.

**It is highly recommended to change these default credentials for production deployments.**

## Database Backup and Restore

For instructions on how to back up and restore the PostgreSQL database, including managing Alembic migrations, please refer to the dedicated documentation: `apps/hindsight-service/docs/DATABASE_BACKUP.md`.

## Further Information

For instructions on applying the initial database schema or managing subsequent database migrations for the `hindsight-service`, please refer to the main `infra/README.md` and `apps/hindsight-service/migrations/README.md` files.

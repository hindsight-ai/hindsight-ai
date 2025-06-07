# Infrastructure Setup and Migrations

This directory contains all infrastructure-related components and configurations for the Hindsight AI project. It includes:

*   **`migrations/`**: SQL scripts for setting up the initial database schema.
*   **`postgres/`**: Docker Compose setup for the PostgreSQL database service.

These components are designed to provide a robust and easily deployable database environment for the `hindsight-service`.

## PostgreSQL Database Setup

The PostgreSQL database is set up using Docker Compose.

### Initial Database Migration

To set up the initial database schema, follow these steps:

1.  **Ensure Docker and Docker Compose are running.**
2.  **Start the PostgreSQL container:**
    Navigate to the `infra/postgres` directory and run:
    ```bash
    docker compose up -d
    ```
3.  **Apply the initial schema migration:**
    The initial schema is defined in `infra/migrations/V1__initial_schema.sql`.
    To apply this migration, you need the container ID of the running PostgreSQL service.
    First, get the container ID:
    ```bash
    docker ps --filter "name=db" --format "{{.ID}}"
    ```
    (Replace `db` with the actual service name if it differs in `docker-compose.yml`).
    
    Then, execute the SQL script inside the container. Replace `[CONTAINER_ID]` with the ID obtained from the previous step:
    ```bash
    PGPASSWORD=password docker exec -i [CONTAINER_ID] psql -U postgres -d hindsight_db < infra/migrations/V1__initial_schema.sql
    ```
    This command will create all necessary tables and indexes as defined in the SQL file.

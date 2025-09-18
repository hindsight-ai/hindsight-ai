# ADR 0002: Single Docker Compose file with environment-scoped secrets

- Status: Accepted
- Date: 2025-09-07

## Context
We previously duplicated compose files for staging and production. This added maintenance cost and risk of drift. GitHub Actions supports environment-scoped secrets and environments per job.

## Decision
Use a single `docker-compose.app.yml` for both environments, parameterized by a `.env` file written by the deploy job. The workflow selects the environment based on branch (`main` vs `staging`) and thus resolves to the correct secrets and hostnames.

## Consequences
- One source of truth; less duplication and drift.
- Environment divergence handled by values in `.env` (e.g., `APP_HOST`, `TRAEFIK_DASHBOARD_HOST`).
- Easier to audit and change.

## Alternatives Considered
- Separate compose files (rejected): recurring sync burden and increased failure surface.
- Templating compose (Helm/Kustomize): heavier toolchain than needed for simple two-env parameterization.


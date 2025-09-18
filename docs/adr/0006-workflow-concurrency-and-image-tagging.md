# ADR 0006: Workflow concurrency and image tagging strategy

- Status: Accepted
- Date: 2025-09-07

## Context
Deployments triggered by multiple pushes can overlap and cause race conditions. Images should be traceable to commits and easily promotable.

## Decision
- Add per-branch concurrency to the deploy job: `group: deploy-${{ github.ref }}`, `cancel-in-progress: true`.
- Tag images with the Git SHA; optionally maintain `latest` tags per branch (`latest` for `main`, `staging-latest` for `staging`).

## Consequences
- Only the most recent run for a branch deploys; avoids partial rollouts.
- Traceability from running containers to commits via SHA tags.

## Alternatives Considered
- No concurrency: risk of overlapping deploys.
- Semantic version tags only: insufficient traceability for CI-driven deployments.


# ADR 0004: Domain strategy for staging (single-level subdomains)

- Status: Accepted
- Date: 2025-09-07

## Context
Cloudflare Universal SSL does not cover two-level subdomains like `app.staging.example.com`. Using such names requires Advanced Certificates or a delegated sub-zone.

## Decision
Use single-level subdomains for staging, e.g., `app-staging.hindsight-ai.com` and `traefik-staging.hindsight-ai.com`.

## Consequences
- Works with Universal SSL; simpler DNS and cert management.
- Avoids recurring certificate errors and ACME rejections.

## Alternatives Considered
- Advanced Certificates ($): allows SANs like `*.staging.example.com`.
- Delegate `staging.example.com` to its own zone to regain wildcard coverage.


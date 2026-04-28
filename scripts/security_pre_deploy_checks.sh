#!/usr/bin/env bash
#
# Pre-deploy probes for the data-isolation security fixes.
#
# Run this against a production-equivalent database (or a recent backup
# snapshot) BEFORE deploying the fixes for findings A, F2, F5, and E. Each
# probe maps to a class of pre-existing data state that the fixes will
# either reject (and break a workflow) or surface (and trigger a lockout).
#
# Required env: DATABASE_URL or PGHOST/PGUSER/PGDATABASE/PGPASSWORD.
#
# Usage:
#   ./scripts/security_pre_deploy_checks.sh
#
# Exit code is non-zero if any probe returned rows; that means the
# operator needs to act before deploying (or accept the listed breakage).

set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]] && [[ -z "${PGHOST:-}" ]]; then
  echo "Set DATABASE_URL or PGHOST/PGUSER/PGDATABASE/PGPASSWORD." >&2
  exit 2
fi

PSQL_ARGS=(-X --tuples-only --quiet -v ON_ERROR_STOP=1)
if [[ -n "${DATABASE_URL:-}" ]]; then
  PSQL_ARGS+=("$DATABASE_URL")
fi

run_probe() {
  local name="$1"
  local sql="$2"
  local advisory="$3"
  local output
  output=$(psql "${PSQL_ARGS[@]}" -c "$sql" 2>&1 | sed '/^$/d')
  if [[ -n "$output" ]]; then
    echo "==[$name]==============================================="
    echo "$output"
    echo
    echo "Advisory: $advisory"
    echo
    return 1
  else
    echo "[$name] OK (no rows)"
    return 0
  fi
}

failures=0

# A — pending consolidation suggestions whose originals span owners.
# After A lands these will return 409 forever from /validate/.
if ! run_probe \
  "A.cross_owner_pending_suggestions" \
  "SELECT cs.suggestion_id, cs.status, COUNT(DISTINCT mb.owner_user_id) AS distinct_owners
   FROM consolidation_suggestions cs,
        jsonb_array_elements_text(cs.original_memory_ids) AS oid
   JOIN memory_blocks mb ON mb.id = oid::uuid
   WHERE cs.status = 'pending'
   GROUP BY cs.suggestion_id, cs.status
   HAVING COUNT(DISTINCT mb.owner_user_id) > 1;" \
  "Each suggestion above will return 409 from /validate/ after the A fix lands. Either DELETE these rows pre-deploy or accept the breakage."; then
  failures=$((failures + 1))
fi

# F2 — users with non-NULL external_subject (should be empty pre-deploy).
# After F2 deploys and users sign in, this column populates via TOFU. If
# anyone has it set BEFORE deploy, that means the column already has stale
# values that may not match what the new oauth2-proxy claim mapping emits.
if ! run_probe \
  "F2.users_with_pre_existing_external_subject" \
  "SELECT id, email, external_subject FROM users WHERE external_subject IS NOT NULL;" \
  "If F2 has been partially deployed before this run, these rows may need their external_subject cleared (use scripts/rebind_user_subject.py) before reconfiguring oauth2-proxy."; then
  failures=$((failures + 1))
fi

# F5 — personal-scoped agents whose memory_blocks span multiple owners.
# Symptom of the migration backfill picking owner non-deterministically.
if ! run_probe \
  "F5.cross_owner_personal_agents" \
  "SELECT agent_id, COUNT(DISTINCT owner_user_id) AS distinct_owners
   FROM memory_blocks
   WHERE visibility_scope = 'personal' AND owner_user_id IS NOT NULL
   GROUP BY agent_id
   HAVING COUNT(DISTINCT owner_user_id) > 1;" \
  "Each agent above has memory blocks owned by multiple users — historical mis-attribution from the 2024-09-15 backfill. Quarantine the affected blocks and pick a single owner per agent."; then
  failures=$((failures + 1))
fi

# E — personal-scoped memory blocks with NULL owner_user_id. Should be
# zero (the ck_*_personal_owner constraint forbids it). If non-zero,
# the constraint is missing or has been bypassed; the E fix is the only
# remaining defense.
if ! run_probe \
  "E.null_owner_personal_memory_blocks" \
  "SELECT id, agent_id, visibility_scope FROM memory_blocks
   WHERE visibility_scope = 'personal' AND owner_user_id IS NULL;" \
  "Personal-scoped blocks with NULL owner. The DB constraint ck_memory_blocks_personal_owner should forbid this — verify the constraint is present."; then
  failures=$((failures + 1))
fi

if [[ $failures -gt 0 ]]; then
  echo
  echo "$failures probe(s) reported rows. Review above and act before deploying." >&2
  exit 1
fi

echo
echo "All probes clean. Safe to deploy the security-fix branch."

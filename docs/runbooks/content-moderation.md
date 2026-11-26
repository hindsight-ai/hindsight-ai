# Runbook: content moderation and public-visibility incidents

Use this when someone reports inappropriate content, or content that should not
be visible to other people. It covers how to find out who created something,
who can currently see it, and how to take it out of view while keeping a record
of what was done.

## 1. Who can see a row?

Every memory block, agent and keyword has a `visibility_scope`:

| Scope | Who can read it |
|---|---|
| `personal` | Only its owner (`owner_user_id`), plus superadmins. |
| `organization` | Members of `organization_id`, plus superadmins. |
| `public` | Everyone, including anonymous visitors of `api.<domain>` and `/guest-api`. |

Only a superadmin may create public rows or move rows to `public`.
`apps/hindsight-service/docs/PUBLIC_CONTENT_GOVERNANCE.md` lists every
write path and the test that enforces this rule.

Superadmins see **every** row, including other users' personal rows. If you
come across someone's content while logged in as a superadmin, it is not
necessarily public. Check its `visibility_scope` before deciding whether it
leaked.

## 2. Is anything public that should not be?

Read-only. Run it on the server with
`docker exec -i <db-container> psql -U <user> -d <db>`. Start the session with
`SET default_transaction_read_only = on;`.

```sql
-- What is public, when was it created, and by whom (NULL owner = legacy/seed data)
SELECT visibility_scope, count(*), min(created_at)::date, max(created_at)::date
FROM memory_blocks GROUP BY 1;

SELECT id, agent_id, owner_user_id, organization_id, created_at, left(content, 80)
FROM memory_blocks WHERE visibility_scope = 'public' ORDER BY created_at DESC LIMIT 50;

-- Same for agents and keywords
SELECT agent_id, agent_name, owner_user_id, created_at FROM agents WHERE visibility_scope = 'public';
SELECT keyword_id, keyword_text, owner_user_id FROM keywords WHERE visibility_scope = 'public';

-- Who published, or tried to publish (refusals are logged with status 'failure')
SELECT created_at, actor_user_id, action_type, status, target_type, target_id, metadata
FROM audit_logs
WHERE action_type IN ('memory_create','memory_scope_change','agent_create','agent_scope_change','keyword_create','keyword_update')
ORDER BY created_at DESC LIMIT 100;
```

You can also check from the outside exactly what an anonymous visitor sees:
`curl 'https://api.<domain>/memory-blocks/?limit=200'` (also `/agents/` and `/keywords/`).

## 3. Take content out of public view

Prefer **making it private to its creator** over deleting it. It is reversible
and keeps the evidence.

```sql
BEGIN;
-- 1) Record the decision (actor = the superadmin doing the moderation).
INSERT INTO audit_logs (actor_user_id, action_type, status, target_type, target_id, reason, metadata)
SELECT '<your-superadmin-user-id>', 'memory_scope_change', 'success', 'memory_block', id,
       'moderation: removed from public view',
       jsonb_build_object('from_scope', visibility_scope, 'to_scope', 'personal')
FROM memory_blocks WHERE id IN ('<id1>', '<id2>') AND visibility_scope = 'public';
-- 2) Make it private to its owner (rows with an owner only).
UPDATE memory_blocks SET visibility_scope = 'personal', organization_id = NULL, updated_at = now()
WHERE id IN ('<id1>', '<id2>') AND visibility_scope = 'public' AND owner_user_id IS NOT NULL;
COMMIT;
```

Rows without an owner cannot be `personal` (a database constraint requires an
owner). Assign them to an owner first, or archive them (`archived = true`).
Archived rows are still returned by `/memory-blocks/archived/` to anyone who
can see their scope.

Take a backup before any bulk change:
`docker exec <db-container> pg_dump -U <user> -d <db> -Fc > backup.dump`.

## 4. Identity spoofing (incident of 2026-11)

The backend trusts the `X-Auth-Request-*` and `X-Forwarded-*` identity headers.
Only oauth2-proxy may set them. Traefik strips any client-supplied copy at the
`websecure` entry point (middleware `strip-identity-headers` in
`config/dynamic.yml`). CI enforces this in two places:

* `scripts/check_edge_identity_headers.py` fails the build if a header the
  backend trusts is not stripped at the edge.
* The post-deploy step in `.github/workflows/deploy.yml` sends a spoofed header
  to the live API host. The deploy fails if that header authenticates.

To check by hand, run
`curl -s -o /dev/null -w '%{http_code}' -H 'X-Auth-Request-Email: probe@invalid.example' https://api.<domain>/organizations/`.
It must print `401`.

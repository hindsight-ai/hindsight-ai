# PAT Revision Plan: Ensure PATs cannot exceed current user rights

Status: In Progress

Owner: repo maintainer / engineering

Date: 2025-09-15

Summary
-------
This document describes a plan to change Personal Access Token (PAT) behavior so PATs cannot be used to perform actions that the associated user no longer has permission to perform. Currently PATs store scopes at creation time and request handling only validates the PAT's stored scopes; this allows a user who had write permissions at token creation to retain write access via an existing PAT after their account or membership has been downgraded.

Goals
-----
- Prevent PATs from allowing access broader than the user's current permissions.
- Prevent creation of PATs whose scopes exceed the creating user's current permissions.
- Keep behavior backward-compatible where reasonable, and add tests to avoid regressions.

Scope
-----
Files likely affected:

- `core/api/deps.py` — PAT auth dependency and helpers (`get_current_user_context_or_pat`, `ensure_pat_allows_*`, `get_scoped_user_and_context`).
- `core/db/repositories/tokens.py` — token creation/rotation/revoke functions (creation-time validation may reference user rights).
- `core/api/users.py` (or wherever `POST /users/me/tokens` is implemented) — enforce creation-time constraints.
- Tests: `tests/unit/test_token_crypto_and_pat.py`, `tests/unit/test_pat_dependency.py`, `tests/integration/*` where PATs are used.

Rationale
---------
Security principle: a token should represent a subset of the owner's active privileges. If a user's privileges are reduced, existing tokens should not continue to grant previously-held powers. This avoids privilege escalation through stale credentials and supports immediate revocation of access by changing user roles/membership flags.

Design decisions
----------------
1) Runtime enforcement (must):
   - On every request authenticated by PAT, require both:
     - The PAT's stored scopes include the required scope (read/write).
     - The PAT's associated user currently has the required permission on the target organization (via membership.can_write / can_read).
   - Implement by enhancing `ensure_pat_allows_write` and `ensure_pat_allows_read` in `core/api/deps.py` to consult `current_user['memberships_by_org']` when a PAT is present.

2) Creation-time guard (recommended):
   - When creating a PAT (`POST /users/me/tokens`), validate the requested scopes against the creator's current effective rights and reject requests that would widen access (HTTP 400/403).

3) Token metadata: keep storing scopes and `organization_id` as before. Do not change token encoding/secret format.

4) Backwards compatibility & migration:
   - No DB migration required for data model changes.
   - Tests must be updated and new tests added to cover demotion scenarios.

Detailed change list
--------------------

1) Runtime enforcement (Core change)
   - File: `core/api/deps.py`
   - Functions to modify: `ensure_pat_allows_write`, `ensure_pat_allows_read`
   - Behaviour:
     - If `current_user` contains a `pat` entry, after checking PAT scopes and (optionally) PAT org restriction, find the effective org id for the check (prefer `target_org_id`, fallback to `pat.organization_id`).
     - Look up membership = current_user.get('memberships_by_org', {}).get(str(effective_org_id)). If membership is absent or membership['can_write'] (or can_read) is False, raise HTTP 403.
     - If effective_org_id is None (personal/no-org), decide policy: ensure the user account is active (non-revoked) and has applicable rights — at minimum, ensure the user still exists.

2) Creation-time guard (API change)
   - File: wherever token creation endpoint is implemented (search `POST /users/me/tokens` in `core/api/users.py` or related).
   - Behaviour: before calling repository `create_token`, validate `payload.scopes` against the creating user's current memberships and reject if any requested scope is not permitted in the indicated org.

3) Tests
   - Add unit test(s) that create a PAT with write scope for a user, then change the user's membership to remove can_write and assert that the PAT-authenticated request is rejected for write operations.
   - Add unit test that attempts to create a write PAT for a user who lacks write and assert creation fails.

4) Docs and UX
   - Update `TOKEN_IMPLEMENTATION_PLAN.md` and user-facing docs to explain that PATs are constrained by current user rights and can be revoked or filtered by owners.

Security considerations
-----------------------
- Ensure we don't accidentally leak membership internals in error messages (use standard 403 messages).
- Consider whether automatic revocation is desirable for tokens that become over-privileged; propose an audit endpoint instead to list such tokens for admin action.

Implementation timeline & tasks
-----------------------------
- T1: Draft plan (this file) — Done (In Progress -> Completed when the file is added).
- T2: Add runtime enforcement checks in `core/api/deps.py` — In progress.
- T3: Add unit tests for runtime enforcement — next.
- T4: Add creation-time validation in token creation endpoint — follow-up.
- T5: Add tests for creation-time validation — follow-up.
- T6: Update docs and open PR — follow-up.

Status matrix (live)
--------------------
- T1 Draft plan: Completed (this document).
- T2 Runtime enforcement: In Progress (work started).
- T3 Runtime tests: Not started.
- T4 Creation-time guard: Not started.
- T5 Creation-time tests: Not started.
- T6 Docs / PR: Not started.

Acceptance criteria
-------------------
1. Existing PATs cannot be used to write to an organization if the associated user no longer has can_write for that organization.
2. Creating a PAT requesting write for an org where the creating user lacks can_write is rejected with 4xx.
3. Unit tests and integration tests demonstrate the behavior.
4. No breaking change for OAuth2-authenticated requests.

Next action (immediate)
-----------------------
- Implement runtime enforcement changes in `core/api/deps.py` (`ensure_pat_allows_*`) and run relevant unit tests. Update the task list and status while progressing.

Appendix: quick code sketch for runtime check
-------------------------------------------
Add to `ensure_pat_allows_write` after existing scope checks:

    # determine effective org to check
    pat_org = pat.get('organization_id')
    effective_org = target_org_id or pat_org
    if effective_org is not None:
        mem = current_user.get('memberships_by_org', {}).get(str(effective_org))
        if not mem or not mem.get('can_write'):
            raise HTTPException(status_code=403, detail='Token user lacks write permission for organization')

And similarly for read (respecting write_implies_read).

---

End of plan.

Iteration note (2025-09-15)
--------------------------
Unit tests related to PAT behavior were executed locally with the coverage gate intentionally ignored for focused iteration. The focused PAT unit tests and the organization role->permission regression test pass when run individually. The repository-wide coverage gate remains and will be addressed separately.

Next recommended engineering steps
--------------------------------
- Merge the runtime enforcement changes behind a feature branch and open a PR with the updated tests and this plan attached.
- Add telemetry/audit events when a PAT request is denied due to membership drift.
- Schedule creation-time validation as a follow-up (separate PR) and add admin tooling for inspecting over-privileged tokens.

Progress update (2025-09-15)
----------------------------
- Runtime enforcement finalized in `core/api/deps.py` (membership-aware checks; token-org mismatch enforced unconditionally).
- Focused unit tests (`tests/unit/test_token_crypto_and_pat.py`) and the role->permission regression integration test (`tests/integration/organizations/test_role_permissions_regression.py`) pass when run individually. The repo-level coverage gate still fails full-suite runs; this is being tracked separately.
- Per direction: creation-time validation is deferred — PAT creation may accept broad scopes, but runtime checks prevent misuse.

Status matrix (updated)
-----------------------
- Runtime enforcement: Done
- Focused PAT unit tests: Done (pass individually)
- Update PAT revision plan: Done (this file)
- Org integration regression tests: Done (pass individually)


"""
End-to-end verification of the data-leak audit findings.

Each test asserts the *current* (vulnerable) behavior — i.e. it PASSES today
and would FAIL after the corresponding finding is fixed. This makes the suite
a regression harness for the eventual patches.

Findings under test (see RFC at /tmp/hindsight-security-audit/RFC-data-leak-audit.md):

  F2  email-only identity
  F1  _basic_search_fallback bypasses scope filter when current_user is None
      and agent_id is supplied
  A   apply_consolidation mints new block under original_memory_ids[0].owner
  B   bulk_move accepts arbitrary destination_owner_user_id
  F6  bulk_delete dry-run leaks resource counts to non-members
  D   /user-info local-dev fallback fires on Host: localhost*

Runs against a real Postgres testcontainer (pgvector/pgvector:pg16) configured
in tests/conftest.py with full Alembic migrations. Per-test transactional
rollback handles teardown.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from core.api.main import app as main_app
from core.db import models


pytestmark = pytest.mark.e2e


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _h(user: str, *, scope: str = "personal") -> dict:
    """Header set for an oauth2-proxy authenticated user."""
    return {
        "x-auth-request-user": user,
        "x-auth-request-email": f"{user}@example.com",
        "x-active-scope": scope,
    }


def _client(extra_headers: dict | None = None) -> TestClient:
    headers = {"x-active-scope": "personal"}
    if extra_headers:
        headers.update(extra_headers)
    return TestClient(main_app, headers=headers)


def _guest_client() -> TestClient:
    """A TestClient that sends no auth headers and no default scope header."""
    return TestClient(main_app)


def _create_personal_memory(client: TestClient, headers: dict, content: str, agent_name: str | None = None) -> dict:
    agent_name = agent_name or f"agent-{uuid.uuid4().hex[:8]}"
    r = client.post(
        "/agents/",
        json={"agent_name": agent_name, "visibility_scope": "personal"},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    agent_id = r.json()["agent_id"]

    r = client.post(
        "/memory-blocks/",
        json={
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "content": content,
            "visibility_scope": "personal",
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    mb = r.json()
    mb["_agent_id"] = agent_id
    return mb


# ---------------------------------------------------------------------------
# F2 — Email-only identity: the same email used by two different "people"
#       resolves to the same User row, so the second person inherits all data
#       owned by the first.
# ---------------------------------------------------------------------------


def test_F2_email_collision_grants_account_takeover(db_session):
    """
    Two sign-ins with the same email but different display names ("Alice First"
    vs "Alice Second") MUST resolve to one User row today, since the auth path
    only filters on `User.email`. The second person's `/user-info` reflects
    the same user_id and the same personal memory blocks.

    This reproduces the user's reported symptom of "legit data appears in my
    account" via legitimate (non-malicious) email reassignment.
    """
    email = "alice-recycled@example.com"

    # First human signs up as "Alice First", creates a personal memory block.
    h_first = {
        "x-auth-request-user": "Alice First",
        "x-auth-request-email": email,
        "x-active-scope": "personal",
    }
    client_first = _client()
    secret_content = f"ALICE_FIRST_SECRET_{uuid.uuid4().hex}"
    mb_first = _create_personal_memory(client_first, h_first, secret_content)

    r_info_first = client_first.get("/user-info", headers=h_first)
    assert r_info_first.status_code == 200, r_info_first.text
    user_id_first = r_info_first.json()["user_id"]

    # Second human is given the same email later (e.g. corporate alias reuse)
    # and signs in with a different display name.
    h_second = {
        "x-auth-request-user": "Alice Second",
        "x-auth-request-email": email,
        "x-active-scope": "personal",
    }
    client_second = _client()
    r_info_second = client_second.get("/user-info", headers=h_second)
    assert r_info_second.status_code == 200, r_info_second.text
    user_id_second = r_info_second.json()["user_id"]

    # BUG: same email -> same user_id -> account takeover.
    assert user_id_second == user_id_first, (
        "Email-only identity bug: a second sign-in with the same email got a different "
        "user_id, which would mean the bug is fixed."
    )

    # The second human's personal memory listing now contains the first person's secret.
    r_list = client_second.get("/memory-blocks/", headers=h_second)
    assert r_list.status_code == 200, r_list.text
    items = r_list.json()["items"]
    contents = [it["content"] for it in items]
    assert secret_content in contents, (
        "Expected the first user's personal memory block to leak into the second user's listing."
    )

    # Confirm at the DB layer that exactly one User row exists for this email.
    rows = db_session.query(models.User).filter(models.User.email == email).all()
    assert len(rows) == 1, f"Expected 1 User row for {email}, found {len(rows)}"


# ---------------------------------------------------------------------------
# F1 — _basic_search_fallback exposes personal data to guests when agent_id
#       is supplied.
# ---------------------------------------------------------------------------


def test_F1_guest_basic_search_with_agent_id_does_not_leak_personal_data(db_session):
    """
    Regression guard for F1: `_basic_search_fallback` must apply the public-only
    filter for guest callers regardless of whether `agent_id` or
    `conversation_id` is supplied. The previous carve-out treated those as a
    permission grant, which let any anonymous caller read personal memory
    blocks for a known agent.
    """
    secret_content = f"PERSONAL_LEAK_TARGET_{uuid.uuid4().hex}"
    h_alice = _h("alice-leak-target")
    client_authed = _client()
    mb = _create_personal_memory(client_authed, h_alice, secret_content)
    agent_id = mb["_agent_id"]

    # Guest: no Authorization, no X-API-Key, no X-Auth-Request-* headers.
    guest = _guest_client()
    r = guest.get(
        "/memory-blocks/search/",
        params={
            "keywords": "PERSONAL_LEAK_TARGET",
            "agent_id": agent_id,
            "search_type": "basic",
            "limit": 50,
        },
    )
    assert r.status_code == 200, r.text
    contents = [item["content"] for item in r.json()]
    assert secret_content not in contents, (
        "REGRESSION (F1): guest with agent_id received a personal memory block. "
        "_basic_search_fallback must not honor agent_id as a permission grant."
    )

    # Same call without agent_id was the previously-correct branch and must stay safe.
    r2 = guest.get(
        "/memory-blocks/search/",
        params={
            "keywords": "PERSONAL_LEAK_TARGET",
            "search_type": "basic",
            "limit": 50,
        },
    )
    assert r2.status_code == 200, r2.text
    assert secret_content not in [item["content"] for item in r2.json()]

    # Authenticated user reading their own data through the same path still works.
    r3 = client_authed.get(
        "/memory-blocks/search/",
        params={
            "keywords": "PERSONAL_LEAK_TARGET",
            "agent_id": agent_id,
            "search_type": "basic",
            "limit": 50,
        },
        headers=h_alice,
    )
    assert r3.status_code == 200, r3.text
    assert secret_content in [item["content"] for item in r3.json()], (
        "Owner should still be able to find their own memory block."
    )


# ---------------------------------------------------------------------------
# A — Consolidation validate mis-attributes ownership and archives without
#       checking write permission on every original.
# ---------------------------------------------------------------------------


def test_A_consolidation_validate_minted_under_first_id_owner(db_session):
    """
    Build a consolidation suggestion whose original_memory_ids = [bob_mb, alice_mb].
    Have alice (NOT bob) validate. The new merged block is created with
    owner_user_id = bob.id (from original_memory_ids[0]) and bob's personal
    memory is archived without bob's consent or write check.

    The user's reported symptom: bob sees a new "personal" memory in his list
    that contains content (the LLM-merged suggested_content) he never wrote.
    """
    h_alice = _h("alice-consol")
    h_bob = _h("bob-consol")
    client_alice = _client()
    client_bob = _client()

    alice_secret = f"ALICE_PIECE_{uuid.uuid4().hex}"
    bob_secret = f"BOB_PIECE_{uuid.uuid4().hex}"
    mb_alice = _create_personal_memory(client_alice, h_alice, alice_secret)
    mb_bob = _create_personal_memory(client_bob, h_bob, bob_secret)

    # Resolve user ids from /user-info
    alice_id = client_alice.get("/user-info", headers=h_alice).json()["user_id"]
    bob_id = client_bob.get("/user-info", headers=h_bob).json()["user_id"]

    merged_content = f"MERGED_FROM_BOTH_{uuid.uuid4().hex}"

    # Insert a consolidation_suggestion row directly (the worker normally does
    # this; we shortcut the LLM step). original_memory_ids[0] is bob's id, so
    # the new block will be minted under bob.
    suggestion = models.ConsolidationSuggestion(
        group_id=uuid.uuid4(),
        suggested_content=merged_content,
        suggested_lessons_learned="MERGED_LESSONS",
        suggested_keywords=["alpha", "beta"],
        original_memory_ids=[mb_bob["id"], mb_alice["id"]],
        status="pending",
    )
    db_session.add(suggestion)
    db_session.commit()
    suggestion_id = str(suggestion.suggestion_id)

    # Alice validates the suggestion (she can read at least one original — her own).
    r = client_alice.post(
        f"/consolidation-suggestions/{suggestion_id}/validate/",
        headers=h_alice,
    )
    assert r.status_code == 200, r.text

    # Refresh from DB and assert the new memory block landed under BOB.
    db_session.expire_all()
    new_blocks = (
        db_session.query(models.MemoryBlock)
        .filter(models.MemoryBlock.content == merged_content)
        .all()
    )
    assert len(new_blocks) == 1, (
        f"Expected exactly 1 new merged block, got {len(new_blocks)}"
    )
    new_mb = new_blocks[0]
    assert str(new_mb.owner_user_id) == str(bob_id), (
        f"BUG NOT REPRODUCED: merged block owner is {new_mb.owner_user_id}, "
        f"expected bob ({bob_id})."
    )
    assert new_mb.visibility_scope == "personal"
    assert new_mb.archived is False

    # Bob (the unwitting "owner") now sees the merged content in his personal listing.
    r_list_bob = client_bob.get("/memory-blocks/", headers=h_bob)
    assert r_list_bob.status_code == 200
    contents = [it["content"] for it in r_list_bob.json()["items"]]
    assert merged_content in contents, (
        "Bob's personal listing should include the merged block he never created."
    )

    # Both originals are archived (note: alice's was archived by alice's own action,
    # bob's was archived by alice WITHOUT a write check on bob's row).
    db_session.expire_all()
    bob_orig = db_session.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(mb_bob["id"])).first()
    alice_orig = db_session.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(mb_alice["id"])).first()
    assert bob_orig.archived is True, "Bob's original should have been archived (without his consent)."
    assert alice_orig.archived is True


# ---------------------------------------------------------------------------
# B — bulk_move executor honors arbitrary destination_owner_user_id with no
#       check on the recipient. Tested at the executor layer (the API endpoint
#       wraps the executor in asyncio.create_task which is fire-and-forget
#       under TestClient).
# ---------------------------------------------------------------------------


def test_B_bulk_move_executor_does_not_update_visibility_scope(db_session):
    """
    `core/async_bulk_operations.py:_move_memory_blocks` (lines 207-227) sets
    `organization_id = dest_org_id` and `owner_user_id = dest_owner_id` but
    *does not* update `visibility_scope`. For org→personal moves this produces
    a row with `visibility_scope='organization'` AND `organization_id=NULL`,
    which violates the `ck_memory_blocks_org_has_org` check constraint.

    The DB constraint is therefore the *only* thing preventing this code path
    from silently dropping organization data into a non-member's personal scope.
    If the constraint is ever relaxed or the executor is patched without also
    fixing the dest_owner validation, the leak becomes real.

    To avoid SQLAlchemy session-state issues with the conftest's transactional
    rollback, we exercise the executor's two write statements via a fresh
    short-lived session. This isolates the IntegrityError to its own session
    while the suite's outer rollback still cleans up.
    """
    from sqlalchemy.exc import IntegrityError
    from sqlalchemy.orm import sessionmaker

    h_admin = _h("orgadmin-b", scope="personal")
    h_carol = _h("carol-b", scope="personal")
    client = _client()
    carol_info = client.get("/user-info", headers=h_carol).json()
    carol_id = uuid.UUID(carol_info["user_id"])

    r_org = client.post(
        "/organizations/",
        json={"name": "Org B", "slug": f"org-b-{uuid.uuid4().hex[:8]}"},
        headers=h_admin,
    )
    assert r_org.status_code == 201, r_org.text
    org_id = uuid.UUID(r_org.json()["id"])

    h_admin_org = {**h_admin, "x-active-scope": "organization", "x-organization-id": str(org_id)}
    r_agent = client.post(
        "/agents/",
        json={"agent_name": f"OrgAgent-{uuid.uuid4().hex[:8]}", "visibility_scope": "organization", "organization_id": str(org_id)},
        headers=h_admin_org,
    )
    agent_id = r_agent.json()["agent_id"]

    r_mb = client.post(
        "/memory-blocks/",
        json={
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "content": f"ORG_DATA_LEAK_{uuid.uuid4().hex}",
            "visibility_scope": "organization",
            "organization_id": str(org_id),
        },
        headers=h_admin_org,
    )
    assert r_mb.status_code == 201, r_mb.text
    mb_id = uuid.UUID(r_mb.json()["id"])

    # Reproduce the executor's exact write logic in a fresh session to avoid
    # poisoning the conftest session.
    bind = db_session.get_bind()
    LocalSession = sessionmaker(bind=bind, autoflush=False, autocommit=False)
    s2 = LocalSession()
    try:
        mb = s2.query(models.MemoryBlock).filter(models.MemoryBlock.id == mb_id).first()
        assert mb is not None, "Memory block should be visible from the fresh session."
        # NOTE: the executor does NOT touch visibility_scope. Mirror that.
        mb.organization_id = None
        mb.owner_user_id = carol_id
        leaked_silently = False
        try:
            s2.commit()
            leaked_silently = True
        except IntegrityError as e:
            s2.rollback()
            assert "ck_memory_blocks_org_has_org" in str(e), (
                f"Expected the org-has-org check constraint to fire; got: {e}"
            )
        assert not leaked_silently, (
            "REGRESSION: the executor's UPDATE was accepted by the DB. The "
            "ck_memory_blocks_org_has_org constraint that currently saves us "
            "has been weakened/removed, and `_move_memory_blocks` is missing "
            "both (a) destination_owner_user_id validation and (b) a "
            "visibility_scope update. This is now an exploitable silent leak."
        )
    finally:
        s2.close()


def test_B_bulk_move_api_accepts_arbitrary_destination_owner_dry_run(db_session):
    """
    Independent reproduction at the API layer: the bulk-move dry-run path runs
    synchronously and is allowed even when destination_owner_user_id is a
    user the actor has no relationship with. This proves the *authorisation*
    half of the bug — the recipient's identity is never validated.
    """
    h_admin = _h("orgadmin-b2", scope="personal")
    h_carol = _h("carol-b2", scope="personal")
    client = _client()
    carol_info = client.get("/user-info", headers=h_carol).json()
    carol_id = carol_info["user_id"]

    r_org = client.post(
        "/organizations/",
        json={"name": "Org B2", "slug": f"org-b2-{uuid.uuid4().hex[:8]}"},
        headers=h_admin,
    )
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]

    # Dry-run accepts arbitrary recipient with no relationship to actor or org.
    r = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-move",
        json={
            "destination_owner_user_id": carol_id,
            "resource_types": ["memory_blocks"],
            "dry_run": True,
        },
        headers=h_admin,
    )
    assert r.status_code == 200, (
        f"BUG NOT REPRODUCED: bulk-move dry-run with arbitrary destination_owner_user_id "
        f"was rejected (status={r.status_code}): {r.text}"
    )


# ---------------------------------------------------------------------------
# F6 — bulk_delete dry-run leaks resource counts to non-members.
# ---------------------------------------------------------------------------


def test_F6_bulk_delete_dry_run_leaks_counts_to_non_member(db_session):
    """
    `bulk_operations.py:262-298` lets any authenticated user submit a delete
    plan against any organization and learn agent_count / memory_block_count /
    keyword_count. A small information disclosure, included for completeness.
    """
    h_admin = _h("orgadmin-f6", scope="personal")
    h_outsider = _h("outsider-f6", scope="personal")
    client = _client()

    r_org = client.post(
        "/organizations/",
        json={"name": "Org F6", "slug": f"org-f6-{uuid.uuid4().hex[:8]}"},
        headers=h_admin,
    )
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]

    # Outsider (not a member) requests dry-run delete plan and gets a 200 with counts.
    r = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-delete",
        json={"dry_run": True, "resource_types": ["memory_blocks", "agents", "keywords"]},
        headers=h_outsider,
    )
    assert r.status_code == 200, (
        f"BUG NOT REPRODUCED: outsider was rejected by bulk-delete dry-run "
        f"(status={r.status_code}): {r.text}"
    )
    body = r.json()
    assert "resources_to_delete" in body
    assert "memory_blocks" in body["resources_to_delete"]
    assert "agents" in body["resources_to_delete"]
    assert "keywords" in body["resources_to_delete"]


# ---------------------------------------------------------------------------
# D — /user-info host-spoof local-dev fallback. Default ALLOW_LOCAL_DEV_AUTH=true.
# ---------------------------------------------------------------------------


def test_D_user_info_localhost_host_fallback_returns_dev_user(db_session, monkeypatch):
    """
    `core/api/main.py:361-387`: when no auth headers and no PAT are present,
    if Host starts with 'localhost' OR client_ip is in (127.0.0.1, ::1, None),
    `/user-info` returns the dev user `dev@localhost` with full memberships.

    TestClient sets `host = testserver` by default, so we override it.
    """
    monkeypatch.setenv("ALLOW_LOCAL_DEV_AUTH", "true")
    # Make sure DEV_MODE itself is OFF so we hit the local-dev fallback branch,
    # not the dev-mode branch.
    monkeypatch.delenv("DEV_MODE", raising=False)

    client = _guest_client()
    r = client.get("/user-info", headers={"host": "localhost.evil.example.com"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("authenticated") is True, (
        f"BUG NOT REPRODUCED: localhost-host fallback did not authenticate the request. "
        f"Body: {body}"
    )
    assert body.get("email") == "dev@localhost"

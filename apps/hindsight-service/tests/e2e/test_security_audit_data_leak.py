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


def test_A_consolidation_validate_rejects_cross_owner_suggestion(db_session):
    """
    Regression guard for A: validating a consolidation suggestion whose
    `original_memory_ids` span more than one (scope, owner, org) tuple must
    be refused. Otherwise the new merged block is minted under
    `original_memory_ids[0].owner_user_id` and originals are archived
    without a write-access check on every original.
    """
    h_alice = _h("alice-consol")
    h_bob = _h("bob-consol")
    client_alice = _client()
    client_bob = _client()

    alice_secret = f"ALICE_PIECE_{uuid.uuid4().hex}"
    bob_secret = f"BOB_PIECE_{uuid.uuid4().hex}"
    mb_alice = _create_personal_memory(client_alice, h_alice, alice_secret)
    mb_bob = _create_personal_memory(client_bob, h_bob, bob_secret)

    merged_content = f"MERGED_FROM_BOTH_{uuid.uuid4().hex}"
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

    # Alice attempts to validate — she lacks write access on bob's original AND
    # the originals span owners. Either the 403 (write-on-every-original) or
    # the 409 (cross-owner) check should reject; the bug previously returned 200.
    r = client_alice.post(
        f"/consolidation-suggestions/{suggestion_id}/validate/",
        headers=h_alice,
    )
    assert r.status_code in (403, 409), (
        f"REGRESSION (A): cross-owner validation returned {r.status_code}. "
        f"Body: {r.text}"
    )

    # No merged block was created and no original was archived.
    db_session.expire_all()
    new_blocks = (
        db_session.query(models.MemoryBlock)
        .filter(models.MemoryBlock.content == merged_content)
        .all()
    )
    assert new_blocks == [], (
        f"REGRESSION (A): a merged block was created despite rejection. Found: {new_blocks}"
    )
    bob_orig = db_session.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(mb_bob["id"])).first()
    alice_orig = db_session.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(mb_alice["id"])).first()
    assert bob_orig.archived is False, "Bob's memory must not have been archived by alice's failed attempt."
    assert alice_orig.archived is False, "Alice's memory must not have been archived by her failed attempt."

    # Positive case: a same-owner suggestion (alice over alice's own blocks) still works.
    alice_secret2 = f"ALICE_PIECE2_{uuid.uuid4().hex}"
    mb_alice2 = _create_personal_memory(client_alice, h_alice, alice_secret2)
    same_owner_suggestion = models.ConsolidationSuggestion(
        group_id=uuid.uuid4(),
        suggested_content=f"ALICE_MERGED_{uuid.uuid4().hex}",
        suggested_lessons_learned="MERGED_LESSONS",
        suggested_keywords=["alpha"],
        original_memory_ids=[mb_alice["id"], mb_alice2["id"]],
        status="pending",
    )
    db_session.add(same_owner_suggestion)
    db_session.commit()
    sid = str(same_owner_suggestion.suggestion_id)
    r2 = client_alice.post(
        f"/consolidation-suggestions/{sid}/validate/",
        headers=h_alice,
    )
    assert r2.status_code == 200, r2.text


# ---------------------------------------------------------------------------
# B — bulk_move executor honors arbitrary destination_owner_user_id with no
#       check on the recipient. Tested at the executor layer (the API endpoint
#       wraps the executor in asyncio.create_task which is fire-and-forget
#       under TestClient).
# ---------------------------------------------------------------------------


def test_B_bulk_move_executor_now_updates_visibility_scope(db_session):
    """
    Regression guard for B (executor half): `_move_memory_blocks` must set
    `visibility_scope` to a value consistent with the new (organization_id,
    owner_user_id). Without that update, org→personal moves produced rows
    that violated `ck_memory_blocks_org_has_org`, and the DB constraint was
    the only line of defense.
    """
    import asyncio
    from sqlalchemy.orm import sessionmaker

    from core.async_bulk_operations import BulkOperationTask

    h_admin = _h("orgadmin-bx", scope="personal")
    client = _client()
    admin_info = client.get("/user-info", headers=h_admin).json()
    admin_id = uuid.UUID(admin_info["user_id"])

    r_org = client.post(
        "/organizations/",
        json={"name": "Org Bx", "slug": f"org-bx-{uuid.uuid4().hex[:8]}"},
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
            "content": f"ORG_BX_{uuid.uuid4().hex}",
            "visibility_scope": "organization",
            "organization_id": str(org_id),
        },
        headers=h_admin_org,
    )
    assert r_mb.status_code == 201, r_mb.text
    mb_id = uuid.UUID(r_mb.json()["id"])

    # Run the executor in a fresh session to avoid the conftest's transactional
    # session getting in the way of asyncio commits.
    bind = db_session.get_bind()
    LocalSession = sessionmaker(bind=bind, autoflush=False, autocommit=False)
    s2 = LocalSession()
    try:
        task = BulkOperationTask(
            operation_id=uuid.uuid4(),
            task_type="bulk_move",
            actor_user_id=admin_id,
            organization_id=org_id,
            payload={},
        )
        errors: list = []
        moved = asyncio.run(
            task._move_memory_blocks(
                db=s2,
                org_id=org_id,
                dest_org_id=None,
                dest_owner_id=admin_id,  # admin moves the org's data to their own personal scope
                errors=errors,
            )
        )
        assert errors == [], f"Move errors: {errors}"
        assert moved == 1
    finally:
        s2.close()

    db_session.expire_all()
    mb = db_session.query(models.MemoryBlock).filter(models.MemoryBlock.id == mb_id).first()
    assert mb is not None
    assert mb.visibility_scope == "personal", (
        f"Executor must update visibility_scope to 'personal' on org→personal moves; got {mb.visibility_scope}"
    )
    assert str(mb.owner_user_id) == str(admin_id)
    assert mb.organization_id is None


def test_B_bulk_move_api_rejects_destination_owner_other_than_actor(db_session):
    """
    Regression guard for B (auth half): a non-superadmin must not be able to
    set destination_owner_user_id to anyone but themselves. This blocks the
    "org admin dumps org data into a stranger's personal scope" path.
    Moving to the actor's own personal scope is still allowed.
    """
    h_admin = _h("orgadmin-b2", scope="personal")
    h_carol = _h("carol-b2", scope="personal")
    client = _client()
    admin_info = client.get("/user-info", headers=h_admin).json()
    carol_info = client.get("/user-info", headers=h_carol).json()
    admin_id = admin_info["user_id"]
    carol_id = carol_info["user_id"]

    r_org = client.post(
        "/organizations/",
        json={"name": "Org B2", "slug": f"org-b2-{uuid.uuid4().hex[:8]}"},
        headers=h_admin,
    )
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]

    # Negative case: arbitrary recipient (carol) is rejected.
    r = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-move",
        json={
            "destination_owner_user_id": carol_id,
            "resource_types": ["memory_blocks"],
            "dry_run": True,
        },
        headers=h_admin,
    )
    assert r.status_code == 403, (
        f"REGRESSION (B): non-superadmin admin was permitted to set "
        f"destination_owner_user_id to a third-party user. Status={r.status_code}: {r.text}"
    )

    # Positive case: actor moves to their own personal scope.
    r2 = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-move",
        json={
            "destination_owner_user_id": admin_id,
            "resource_types": ["memory_blocks"],
            "dry_run": True,
        },
        headers=h_admin,
    )
    assert r2.status_code == 200, r2.text


# ---------------------------------------------------------------------------
# F6 — bulk_delete dry-run leaks resource counts to non-members.
# ---------------------------------------------------------------------------


def test_F6_bulk_delete_dry_run_rejects_non_member(db_session):
    """
    Regression guard for F6: bulk-delete dry-run must require source-org
    membership, matching bulk-move dry-run. Otherwise it discloses
    per-resource counts (agents / memory_blocks / keywords) to outsiders.
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

    # Outsider (not a member) is rejected.
    r = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-delete",
        json={"dry_run": True, "resource_types": ["memory_blocks", "agents", "keywords"]},
        headers=h_outsider,
    )
    assert r.status_code == 403, (
        f"REGRESSION (F6): outsider got {r.status_code} from bulk-delete dry-run; "
        f"expected 403. Body: {r.text}"
    )

    # Member of the org still gets the plan (positive case).
    r2 = client.post(
        f"/bulk-operations/organizations/{org_id}/bulk-delete",
        json={"dry_run": True, "resource_types": ["memory_blocks", "agents", "keywords"]},
        headers=h_admin,
    )
    assert r2.status_code == 200, r2.text
    assert "resources_to_delete" in r2.json()


# ---------------------------------------------------------------------------
# D — /user-info host-spoof local-dev fallback. Default ALLOW_LOCAL_DEV_AUTH=true.
# ---------------------------------------------------------------------------


def test_D_user_info_no_longer_spoofable_via_host_header(db_session, monkeypatch):
    """
    Regression guard for D: the local-dev fallback in /user-info must NOT
    fire purely because the Host header starts with 'localhost'. Production
    safety previously relied entirely on Traefik filtering Host; any direct
    backend access (port-forward, debug, internal) bypassed it.

    We assert two cases:
      1. ALLOW_LOCAL_DEV_AUTH=true + spoofed Host: localhost.* → 401 unauth
         (because client_ip from TestClient is 'testclient', not loopback)
      2. ALLOW_LOCAL_DEV_AUTH unset → default off → 401 unauth
    """
    monkeypatch.delenv("DEV_MODE", raising=False)

    # Case 1: env explicitly opts in, but client_ip is not loopback.
    monkeypatch.setenv("ALLOW_LOCAL_DEV_AUTH", "true")
    client = _guest_client()
    r = client.get("/user-info", headers={"host": "localhost.evil.example.com"})
    assert r.status_code in (401, 200), r.text
    if r.status_code == 200:
        # If the endpoint still returns 200 it must be the unauthenticated marker, not a dev user.
        body = r.json()
        assert body.get("authenticated") is not True, (
            f"REGRESSION (D): Host-header spoof produced an authenticated response: {body}"
        )
        assert body.get("email") != "dev@localhost"

    # Case 2: env unset → default off.
    monkeypatch.delenv("ALLOW_LOCAL_DEV_AUTH", raising=False)
    client2 = _guest_client()
    r2 = client2.get("/user-info", headers={"host": "localhost.evil.example.com"})
    assert r2.status_code in (401, 200), r2.text
    if r2.status_code == 200:
        body2 = r2.json()
        assert body2.get("authenticated") is not True
        assert body2.get("email") != "dev@localhost"

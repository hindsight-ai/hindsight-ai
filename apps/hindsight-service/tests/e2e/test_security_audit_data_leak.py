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

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport

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


def _async_client_with_loopback_ip() -> httpx.AsyncClient:
    """An httpx.AsyncClient that drives the FastAPI app via ASGITransport,
    with the request scope's `client` set to ('127.0.0.1', 50000). Needed
    to exercise the legitimate local-dev fallback path in /user-info,
    which checks `request.client.host in ('127.0.0.1', '::1')`. The
    default TestClient yields `client=('testclient', 50000)` and would
    never satisfy the check. ASGITransport is async-only in httpx 0.28+,
    so the test using this helper must be async.
    """
    transport = ASGITransport(app=main_app, client=("127.0.0.1", 50000))
    return httpx.AsyncClient(transport=transport, base_url="http://testserver")


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


def test_F2_email_recycle_attempt_is_rejected(db_session):
    """
    Regression guard for F2: when an existing User row was first registered
    with one external_subject (X-Auth-Request-User), a later sign-in using
    the same email but a *different* external_subject MUST be rejected. This
    blocks the silent account-inheritance path described in the audit RFC.
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
    _create_personal_memory(client_first, h_first, secret_content)

    r_info_first = client_first.get("/user-info", headers=h_first)
    assert r_info_first.status_code == 200, r_info_first.text

    # Confirm the User row was bound to the first subject.
    db_session.expire_all()
    user_row = db_session.query(models.User).filter(models.User.email == email).one()
    assert user_row.external_subject == "Alice First", (
        f"User row should have external_subject bound to the first sign-in's "
        f"X-Auth-Request-User, got {user_row.external_subject!r}."
    )

    # Second human attempts to sign in with the same email but a different
    # X-Auth-Request-User. /user-info must refuse with 401, NOT mint or
    # reuse the existing row.
    h_second = {
        "x-auth-request-user": "Alice Second",
        "x-auth-request-email": email,
        "x-active-scope": "personal",
    }
    client_second = _client()
    r_info_second = client_second.get("/user-info", headers=h_second)
    assert r_info_second.status_code == 401, (
        f"REGRESSION (F2): second sign-in with mismatched external_subject "
        f"returned {r_info_second.status_code}. Body: {r_info_second.text}"
    )

    # The unauthenticated second human cannot list /memory-blocks/ either.
    # (write paths are blocked by the read-only middleware; reads via
    # /memory-blocks/ require auth too because there's no PAT and no valid
    # oauth header pair.)
    r_list = client_second.get("/memory-blocks/", headers=h_second)
    if r_list.status_code == 200:
        # If the endpoint accepts the second client at all, it must NOT have
        # surfaced the first user's secret. With the F2 guard, reaching the
        # full memory-blocks listing requires a separate auth path; we only
        # care that the leak is gone.
        contents = [it["content"] for it in r_list.json().get("items", [])]
        assert secret_content not in contents, (
            "REGRESSION (F2): first user's personal memory block was visible "
            "to the second sign-in attempt."
        )

    # Exactly one User row for this email — no second was created.
    db_session.expire_all()
    rows = db_session.query(models.User).filter(models.User.email == email).all()
    assert len(rows) == 1, f"Expected 1 User row for {email}, found {len(rows)}"
    assert rows[0].external_subject == "Alice First"

    # Validate the global IdentityMismatchError handler also catches the
    # search-endpoint path (which previously surfaced the error as 500).
    r_search = client_second.get(
        "/memory-blocks/search/",
        params={"keywords": "anything", "search_type": "fulltext"},
        headers={
            "x-auth-request-user": "Alice Second",
            "x-auth-request-email": email,
        },
    )
    assert r_search.status_code == 401, (
        f"REGRESSION (F2 handler): mismatched second sign-in via /search/ "
        f"returned {r_search.status_code} instead of 401. The global "
        f"IdentityMismatchError exception handler is missing or scoped "
        f"too narrowly. Body: {r_search.text}"
    )


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

    # Alice attempts to validate — she lacks write access on bob's original.
    # The write check fires before the cross-owner check, so this MUST be 403.
    r = client_alice.post(
        f"/consolidation-suggestions/{suggestion_id}/validate/",
        headers=h_alice,
    )
    assert r.status_code == 403, (
        f"REGRESSION (A write check): alice has no write access on bob's block; "
        f"expected 403, got {r.status_code}. Body: {r.text}"
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


def test_A_consolidation_superadmin_cross_owner_returns_409(db_session):
    """
    Regression guard for A's cross-owner check at the apply layer. When the
    actor IS a superadmin (so `_user_can_write_suggestion` passes), the
    cross-owner refusal in apply_consolidation must still fire. The 409
    path is what proves the apply-layer invariant is active; the 403 path
    in test_A_consolidation_validate_rejects_cross_owner_suggestion only
    proves the write-check exists.
    """
    h_alice = _h("alice-admin-A409")
    h_bob = _h("bob-A409")
    client_alice = _client()
    client_bob = _client()

    mb_alice = _create_personal_memory(client_alice, h_alice, f"ALICE_{uuid.uuid4().hex}")
    mb_bob = _create_personal_memory(client_bob, h_bob, f"BOB_{uuid.uuid4().hex}")

    # Promote alice to superadmin via DB so the write check passes.
    alice_id = client_alice.get("/user-info", headers=h_alice).json()["user_id"]
    alice_row = db_session.query(models.User).filter(models.User.id == uuid.UUID(alice_id)).one()
    alice_row.is_superadmin = True
    db_session.commit()

    suggestion = models.ConsolidationSuggestion(
        group_id=uuid.uuid4(),
        suggested_content=f"MERGED_409_{uuid.uuid4().hex}",
        suggested_lessons_learned="MERGED_LESSONS",
        suggested_keywords=["alpha"],
        original_memory_ids=[mb_bob["id"], mb_alice["id"]],
        status="pending",
    )
    db_session.add(suggestion)
    db_session.commit()

    r = client_alice.post(
        f"/consolidation-suggestions/{suggestion.suggestion_id}/validate/",
        headers=h_alice,
    )
    assert r.status_code == 409, (
        f"REGRESSION (A apply-layer): superadmin validation of a cross-owner "
        f"suggestion should still hit the apply-time invariant and return 409, "
        f"got {r.status_code}. Body: {r.text}"
    )


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


def test_change_scope_non_superadmin_cannot_set_new_owner_user_id(db_session):
    """
    Single-block sibling of the B fix: `change_memory_block_scope` (in
    main.py) accepts a `new_owner_user_id` but only a superadmin may use it.
    Confirm the guard fires for a non-superadmin.
    """
    h_alice = _h("alice-changescope")
    h_bob = _h("bob-changescope")
    client_alice = _client()
    client_bob = _client()

    bob_id = client_bob.get("/user-info", headers=h_bob).json()["user_id"]
    mb = _create_personal_memory(client_alice, h_alice, f"CS_{uuid.uuid4().hex}")

    # Alice is not superadmin; she cannot redirect a personal block to bob.
    r = client_alice.post(
        f"/memory-blocks/{mb['id']}/change-scope",
        json={"visibility_scope": "personal", "new_owner_user_id": bob_id},
        headers=h_alice,
    )
    assert r.status_code == 403, (
        f"REGRESSION: non-superadmin was allowed to set new_owner_user_id. "
        f"Status={r.status_code}: {r.text}"
    )


def test_E_apply_scope_filter_treats_id_less_user_as_guest(db_session):
    """
    Regression guard for E: a malformed `current_user` dict that lacks an
    `id` key must not produce `owner_user_id IS NULL`, which would match
    every organization-scoped row (NULL owner is the canonical org-row
    signature) and silently leak all org data.
    """
    from core.db import models, scope_utils
    from core.services.search_service import _apply_user_scope_filter

    # Seed: one personal block with explicit owner, one org block with NULL owner.
    user = models.User(email=f"e_user_{uuid.uuid4().hex}@ex.com", display_name="E", is_superadmin=False)
    db_session.add(user); db_session.commit(); db_session.refresh(user)
    agent_p = models.Agent(agent_name=f"E-agent-{uuid.uuid4().hex[:6]}", visibility_scope="personal", owner_user_id=user.id)
    db_session.add(agent_p); db_session.commit(); db_session.refresh(agent_p)
    org = models.Organization(name=f"E-org-{uuid.uuid4().hex[:6]}", slug=f"e-org-{uuid.uuid4().hex[:6]}", created_by=user.id)
    db_session.add(org); db_session.commit(); db_session.refresh(org)
    agent_o = models.Agent(agent_name=f"E-org-agent-{uuid.uuid4().hex[:6]}", visibility_scope="organization", organization_id=org.id)
    db_session.add(agent_o); db_session.commit(); db_session.refresh(agent_o)

    mb_personal = models.MemoryBlock(agent_id=agent_p.agent_id, conversation_id=uuid.uuid4(), content="E_PERSONAL", visibility_scope="personal", owner_user_id=user.id)
    mb_org = models.MemoryBlock(agent_id=agent_o.agent_id, conversation_id=uuid.uuid4(), content="E_ORG", visibility_scope="organization", organization_id=org.id)
    db_session.add_all([mb_personal, mb_org]); db_session.commit()

    malformed_ctx = {}  # truthy dict, no 'id' — the dangerous shape.

    # scope_utils.apply_scope_filter must treat the malformed dict as a guest.
    q1 = scope_utils.apply_scope_filter(db_session.query(models.MemoryBlock), malformed_ctx, models.MemoryBlock)
    rows1 = q1.all()
    org_rows_1 = [r for r in rows1 if r.visibility_scope == "organization"]
    personal_rows_1 = [r for r in rows1 if r.visibility_scope == "personal"]
    assert org_rows_1 == [], (
        f"REGRESSION (E): scope_utils.apply_scope_filter leaked {len(org_rows_1)} org rows to a "
        f"malformed user_ctx (no 'id')."
    )
    assert personal_rows_1 == [], (
        f"REGRESSION (E): scope_utils.apply_scope_filter leaked {len(personal_rows_1)} personal rows."
    )

    # search_service._apply_user_scope_filter same invariant.
    q2 = _apply_user_scope_filter(db_session.query(models.MemoryBlock), malformed_ctx, models.MemoryBlock)
    rows2 = q2.all()
    assert all(r.visibility_scope == "public" for r in rows2), (
        f"REGRESSION (E): search_service._apply_user_scope_filter returned non-public rows for a "
        f"malformed user_ctx: {[(r.id, r.visibility_scope) for r in rows2]}"
    )


def test_bulk_move_dry_run_requires_source_org_membership(db_session):
    """
    Regression guard for the asymmetry that the F6 fix surfaced: bulk_move's
    dry-run used to permit "member of destination org but not source org",
    leaking the source org's per-resource counts and name conflicts. The
    parallel of F6 must apply: source-org membership is always required
    for dry-run, regardless of whether destination_organization_id is set.
    """
    h_admin_src = _h("orgadmin-bm-src", scope="personal")
    h_admin_dest = _h("orgadmin-bm-dest", scope="personal")
    client = _client()

    r_src = client.post(
        "/organizations/",
        json={"name": "Src Org", "slug": f"src-{uuid.uuid4().hex[:8]}"},
        headers=h_admin_src,
    )
    assert r_src.status_code == 201, r_src.text
    src_org_id = r_src.json()["id"]

    r_dest = client.post(
        "/organizations/",
        json={"name": "Dest Org", "slug": f"dest-{uuid.uuid4().hex[:8]}"},
        headers=h_admin_dest,
    )
    assert r_dest.status_code == 201, r_dest.text
    dest_org_id = r_dest.json()["id"]

    # admin_dest is in dest_org but NOT src_org; previously this was sufficient
    # to dry-run a move out of src_org and learn its per-resource counts.
    r = client.post(
        f"/bulk-operations/organizations/{src_org_id}/bulk-move",
        json={
            "destination_organization_id": dest_org_id,
            "resource_types": ["agents", "memory_blocks", "keywords"],
            "dry_run": True,
        },
        headers=h_admin_dest,
    )
    assert r.status_code == 403, (
        f"REGRESSION (B asymmetry): dest-only member was permitted to "
        f"dry-run a bulk-move from a source org they don't belong to. "
        f"Status={r.status_code}: {r.text}"
    )


# ---------------------------------------------------------------------------
# D — /user-info host-spoof local-dev fallback. Default ALLOW_LOCAL_DEV_AUTH=true.
# ---------------------------------------------------------------------------


def test_D_host_header_spoof_does_not_grant_dev_user(db_session, monkeypatch):
    """
    Regression guard for D (negative case): a non-loopback caller sending
    `Host: localhost.*` plus `ALLOW_LOCAL_DEV_AUTH=true` and no auth
    headers must not get the dev user. Pre-fix, `host.startswith('localhost')`
    was sufficient to mint a `dev@localhost` superadmin context regardless of
    the actual peer.
    """
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.setenv("ALLOW_LOCAL_DEV_AUTH", "true")

    client = _guest_client()  # client_ip = 'testclient'
    r = client.get("/user-info", headers={"host": "localhost.evil.example.com"})
    assert r.status_code == 401, (
        f"REGRESSION (D): host-header spoof from non-loopback peer "
        f"returned {r.status_code} instead of 401. Body: {r.text}"
    )


@pytest.mark.asyncio
async def test_D_default_off_blocks_loopback_when_env_unset(db_session, monkeypatch):
    """
    Regression guard for D's env default: with ALLOW_LOCAL_DEV_AUTH unset,
    even a real loopback caller must NOT get the dev fallback.
    """
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.delenv("ALLOW_LOCAL_DEV_AUTH", raising=False)

    async with _async_client_with_loopback_ip() as client:
        r = await client.get("/user-info")
        assert r.status_code == 401, (
            f"REGRESSION (D): default-off was bypassed even from loopback. "
            f"Status={r.status_code} body={r.text}"
        )


@pytest.mark.asyncio
async def test_D_loopback_with_env_on_still_works(db_session, monkeypatch):
    """
    Positive case for D: when ALLOW_LOCAL_DEV_AUTH=true AND the peer is
    actually loopback (real local-dev workflow), the fallback must still
    produce the dev user. Without this case, an over-tight fix that
    accidentally broke the legitimate local-dev path would go unnoticed.
    """
    monkeypatch.delenv("DEV_MODE", raising=False)
    monkeypatch.setenv("ALLOW_LOCAL_DEV_AUTH", "true")

    async with _async_client_with_loopback_ip() as client:
        r = await client.get("/user-info")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("authenticated") is True
        assert body.get("email") == os.getenv("DEV_LOCAL_EMAIL", "dev@localhost")

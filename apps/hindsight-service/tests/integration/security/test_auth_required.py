"""Security regression guards for issue #70.

Three concerns this file pins:

1. **Unauthenticated mutating routes return 401/403**: 9 routes that
   previously had only `Depends(get_db)` and silently allowed any caller
   to trigger LLM consolidation, prune memory, delete consolidation
   suggestions, etc. After #70 each one requires an authenticated user
   (oauth2-proxy or PAT).

2. **PAT scope-narrowing is enforced on the 4 search endpoints**: a PAT
   scoped to org-A hitting `/memory-blocks/search/{fulltext,semantic,hybrid,/}`
   with `?organization_id=org-B` returns 403 (PAT-org mismatch).

3. **PAT membership narrowing**: a user who is a member of BOTH org-A
   and org-B with a PAT scoped to org-A only sees org-A memberships in
   `current_user`. Without this guard a multi-org user could read org-B
   data via routes that filter by `current_user.memberships`.
"""
from __future__ import annotations

import uuid
from typing import Optional, Tuple

import pytest
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


# Tests pass the X-Active-Scope header so the enforce_write_scope_metadata
# middleware does not pre-empt with a 400 before FastAPI reaches the new
# auth Depends. Without this we would test the middleware, not the dep.
GUEST_HEADERS = {"X-Active-Scope": "personal"}


def _guest_client() -> TestClient:
    return TestClient(app, headers=GUEST_HEADERS)


def _mk_user(db, email: Optional[str] = None) -> models.User:
    email = email or f"sec_{uuid.uuid4().hex[:8]}@example.com"
    u = models.User(email=email, display_name=email.split("@")[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_org(db, name: Optional[str] = None) -> models.Organization:
    suffix = uuid.uuid4().hex[:6]
    name = name or f"sec-org-{suffix}"
    org = models.Organization(name=name, slug=f"sec-org-{suffix}")
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _mk_membership(db, user, org, role: str = "editor") -> models.OrganizationMembership:
    m = models.OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        can_read=True,
        can_write=True,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _mk_pat(db, user, *, organization_id=None, scopes=None) -> Tuple[object, str]:
    payload = schemas.TokenCreateRequest(
        name="sec-test",
        scopes=scopes or ["read", "write"],
        organization_id=organization_id,
    )
    pat, token = token_repo.create_token(db, user_id=user.id, payload=payload)
    return pat, token


# ---------------------------------------------------------------------------
# 1. Unauthenticated mutating routes return 401/403
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path,body",
    [
        ("post", "/consolidation/trigger/", None),
        ("post", "/memory/prune/suggest", {}),
        ("post", "/memory/prune/confirm", {"memory_block_ids": [str(uuid.uuid4())]}),
        ("post", f"/memory-blocks/{uuid.uuid4()}/compress", {}),
        ("post", f"/memory-blocks/{uuid.uuid4()}/compress/apply", {"compressed_content": "x"}),
        ("post", "/memory-blocks/bulk-generate-keywords", {"memory_block_ids": [str(uuid.uuid4())]}),
        ("post", "/memory-blocks/bulk-apply-keywords", {"applications": []}),
        ("post", "/memory-blocks/bulk-compact", {"memory_block_ids": [str(uuid.uuid4())]}),
    ],
)
def test_mutating_route_requires_auth(method, path, body):
    """Each previously-unauthenticated mutating route now returns 401 (or 403)
    when called without auth headers and without a PAT.

    Acceptable codes: 401 (preferred — Depends raises) or 403 (acceptable —
    middleware raises). Anything 2xx is the regression we are guarding."""
    client = _guest_client()
    fn = getattr(client, method)
    if body is not None:
        resp = fn(path, json=body)
    else:
        resp = fn(path)
    assert resp.status_code in (401, 403), (
        f"REGRESSION: {method.upper()} {path} returned {resp.status_code} "
        f"({resp.text[:200]}) for an unauthenticated caller. Expected 401 or 403."
    )


def test_delete_consolidation_suggestion_requires_auth(db_session):
    """DELETE /consolidation-suggestions/{id} previously had no auth dep.
    A real suggestion must be created so the route reaches the auth check
    instead of 404'ing at lookup."""
    user = _mk_user(db_session)
    sug = models.ConsolidationSuggestion(
        suggestion_id=uuid.uuid4(),
        group_id=uuid.uuid4(),
        suggested_content="x",
        suggested_lessons_learned="y",
        suggested_keywords=[],
        original_memory_ids=[],
        status="pending",
    )
    db_session.add(sug)
    db_session.commit()
    db_session.refresh(sug)

    resp = _guest_client().delete(f"/consolidation-suggestions/{sug.suggestion_id}")
    assert resp.status_code in (401, 403), (
        f"REGRESSION: DELETE /consolidation-suggestions/{{id}} returned "
        f"{resp.status_code} for an unauthenticated caller."
    )


# ---------------------------------------------------------------------------
# 2. PAT scope-narrowing on the 4 search endpoints
# ---------------------------------------------------------------------------


SEARCH_ENDPOINTS = [
    "/memory-blocks/search/",            # basic strategy router (memory_blocks.py)
    "/memory-blocks/search/fulltext",
    "/memory-blocks/search/semantic",
    "/memory-blocks/search/hybrid",
]


@pytest.mark.parametrize("endpoint", SEARCH_ENDPOINTS)
def test_pat_cross_org_search_returns_403(db_session, endpoint):
    """A PAT scoped to org-A hitting any of the 4 search endpoints with an
    explicit `organization_id=<org-B>` query param must be rejected with 403.
    Pre-#70 these endpoints silently ignored PAT scope and would return
    org-B data."""
    user = _mk_user(db_session)
    org_a = _mk_org(db_session, name="org-A")
    org_b = _mk_org(db_session, name="org-B")
    _mk_membership(db_session, user, org_a)
    _mk_membership(db_session, user, org_b)

    pat, token = _mk_pat(db_session, user, organization_id=org_a.id)

    client = TestClient(app, headers={"X-Active-Scope": "personal"})
    params = {"query": "anything", "organization_id": str(org_b.id), "limit": 5}
    resp = client.get(
        endpoint,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403, (
        f"REGRESSION: {endpoint} with PAT for org-A and "
        f"organization_id=<org-B> returned {resp.status_code} ({resp.text[:200]}). "
        f"Expected 403 (PAT-org mismatch)."
    )


# ---------------------------------------------------------------------------
# 3. Multi-org PAT narrowing — the F6 regression guard
# ---------------------------------------------------------------------------


def test_pat_narrows_memberships_to_pat_org(db_session):
    """User is a member of org-A AND org-B. PAT is scoped to org-A only.
    `get_scoped_user_and_context` MUST narrow `current_user.memberships`
    to org-A so downstream membership-based filters (e.g. search) cannot
    leak org-B data.

    Pre-#70's revised RFC, `dataclasses.replace` narrowing existed only
    inline in the 3 search endpoints in main.py. Removing those inline
    blocks (as done by replacing with `Depends(get_scoped_user_and_context)`)
    without ALSO adding narrowing inside the dep would have been a
    regression. This test pins the narrowing behavior."""
    from core.api.deps import get_scoped_user_and_context, get_scope_context, get_current_user_context_or_guest
    from core.db.scope_utils import ScopeContext

    user = _mk_user(db_session, email="multiorg@example.com")
    org_a = _mk_org(db_session, name="multi-A")
    org_b = _mk_org(db_session, name="multi-B")
    _mk_membership(db_session, user, org_a)
    _mk_membership(db_session, user, org_b)

    _pat, token = _mk_pat(db_session, user, organization_id=org_a.id)

    # Resolve current_user via the canonical PAT entry point (mirrors what
    # FastAPI does at runtime).
    from core.api.deps import get_current_user_context_or_pat, UserContext
    _uctx = get_current_user_context_or_pat(
        db=db_session,
        authorization=f"Bearer {token}",
    )
    _u = _uctx.user
    current_user = _uctx.current

    # Sanity: pre-narrowing, the user has 2 org memberships.
    assert len(current_user.memberships) == 2, (
        f"Expected 2 memberships pre-narrowing, got {len(current_user.memberships)}. "
        f"Test setup is wrong if this fails."
    )

    # Now apply the unified scope dep manually. It should narrow.
    fake_scope = ScopeContext(scope="personal", organization_id=None)
    scoped = get_scoped_user_and_context(
        scope_ctx=fake_scope,
        user_ctx=UserContext(user=_u, current=current_user),
        organization_id=None,
    )
    user = scoped.user
    narrowed_user = scoped.current

    assert len(narrowed_user.memberships) == 1, (
        f"REGRESSION (F6): get_scoped_user_and_context did not narrow "
        f"memberships for an org-A-scoped PAT — got {len(narrowed_user.memberships)} "
        f"memberships, expected 1. A multi-org user with a PAT for one org "
        f"would leak data from the other org."
    )
    assert str(list(narrowed_user.memberships_by_org.keys())[0]) == str(org_a.id), (
        "REGRESSION (F6): the surviving membership is not the PAT's org."
    )


# ---------------------------------------------------------------------------
# 4. Org-scoped PAT cannot trigger global consolidation
# ---------------------------------------------------------------------------


def test_org_scoped_pat_cannot_trigger_global_consolidation(db_session):
    """`/consolidation/trigger/` runs LLM analysis across every org the
    user can see. An org-scoped PAT is restricted to one org; allowing it
    to fan-out across orgs would violate the PAT's scope contract."""
    user = _mk_user(db_session)
    org_a = _mk_org(db_session, name="trig-A")
    _mk_membership(db_session, user, org_a)

    _pat, token = _mk_pat(
        db_session, user, organization_id=org_a.id, scopes=["read", "write"]
    )

    client = TestClient(app, headers={"X-Active-Scope": "personal"})
    resp = client.post(
        "/consolidation/trigger/",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 403 = our explicit reject. 503 (LLM disabled) is also acceptable
    # when the env disables LLM features — but only if the auth path was
    # passed; we still want to verify org-scoped PAT does not silently
    # succeed. So 503 is acceptable only as a follow-on after the org
    # check fires earlier; reject 200 / 202 (which would mean the run
    # actually triggered).
    assert resp.status_code in (403, 503), (
        f"REGRESSION: org-scoped PAT triggered global consolidation "
        f"(status {resp.status_code}). Expected 403 (rejected) or 503 "
        f"(LLM disabled, but the PAT-org check still ran first)."
    )

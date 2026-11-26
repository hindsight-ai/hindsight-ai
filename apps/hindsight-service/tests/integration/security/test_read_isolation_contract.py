"""Read-isolation contract: private content is never readable by non-owners.

Seeds personal / organization / public rows (memory blocks, agents, keywords,
consolidation suggestions) and replays EVERY GET content route as:

* anonymous (also as the dashboard ``/guest-api`` proxy would: no identity),
* user B (not a member of the org, not an admin), via oauth2-proxy headers and
  via a PAT,
* the owner A and an org member C (positive checks, so the negative checks
  cannot pass vacuously).

A route-enumerating guard fails if a GET route exists that is neither covered
here nor on the explicit non-content allowlist, so new read endpoints cannot
ship without being added to this contract.
"""
from __future__ import annotations

import json
import uuid
from typing import Dict, Optional

import pytest
from fastapi.testclient import TestClient

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo

TAG = uuid.uuid4().hex[:10]
PRIV = f"zzprivmarker{TAG}"      # lives only in user A's personal rows
ORGM = f"zzorgmarker{TAG}"       # lives only in the org's rows
PUBM = f"zzpubmarker{TAG}"       # lives in public rows

SEARCH_PATHS = [
    "/memory-blocks/search/",
    "/memory-blocks/search/fulltext",
    "/memory-blocks/search/semantic",
    "/memory-blocks/search/hybrid",
]

# Scope hints an attacker may try to widen the view with.
HINT_SETS = [
    {},
    {"X-Active-Scope": "personal"},
    {"X-Active-Scope": "public"},
]


def _identity(email: str) -> Dict[str, str]:
    local = email.split("@")[0]
    return {"x-auth-request-user": local, "x-auth-request-email": email}


@pytest.fixture
def world(db_session):
    db = db_session

    def mk_user(label):
        u = models.User(email=f"{label}-{TAG}@example.com", display_name=label)
        db.add(u)
        db.flush()
        return u

    a, b, c = mk_user("usera"), mk_user("userb"), mk_user("userc")
    org = models.Organization(name=f"org-{TAG}", slug=f"org-{TAG}")
    db.add(org)
    db.flush()
    for u in (a, c):
        db.add(models.OrganizationMembership(
            organization_id=org.id, user_id=u.id, role="editor", can_read=True, can_write=True))
    db.flush()

    def mk_agent(name, scope, owner=None, org_id=None):
        ag = models.Agent(agent_name=name, visibility_scope=scope,
                          owner_user_id=owner, organization_id=org_id)
        db.add(ag)
        db.flush()
        return ag

    def mk_kw(text, scope, owner=None, org_id=None):
        k = models.Keyword(keyword_text=text, visibility_scope=scope,
                           owner_user_id=owner, organization_id=org_id)
        db.add(k)
        db.flush()
        return k

    def mk_block(agent, content, scope, owner=None, org_id=None, kw=None, archived=False):
        mb = models.MemoryBlock(
            agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content=content,
            errors=content, lessons_learned=content, visibility_scope=scope,
            owner_user_id=owner, organization_id=org_id, archived=archived)
        db.add(mb)
        db.flush()
        if kw is not None:
            db.add(models.MemoryBlockKeyword(memory_id=mb.id, keyword_id=kw.keyword_id))
            db.flush()
        return mb

    agent_priv = mk_agent(f"agent-{PRIV}", "personal", owner=a.id)
    kw_priv = mk_kw(f"kw-{PRIV}", "personal", owner=a.id)
    blk_priv = mk_block(agent_priv, f"secret {PRIV} body", "personal", owner=a.id, kw=kw_priv)
    blk_priv_arch = mk_block(agent_priv, f"secret archived {PRIV}", "personal", owner=a.id, archived=True)

    agent_org = mk_agent(f"agent-{ORGM}", "organization", org_id=org.id)
    kw_org = mk_kw(f"kw-{ORGM}", "organization", org_id=org.id)
    blk_org = mk_block(agent_org, f"team {ORGM} body", "organization", org_id=org.id, kw=kw_org)

    agent_pub = mk_agent(f"agent-{PUBM}", "public", owner=a.id)
    kw_pub = mk_kw(f"kw-{PUBM}", "public", owner=a.id)
    blk_pub = mk_block(agent_pub, f"open {PUBM} body", "public", owner=a.id, kw=kw_pub)

    # Consolidation suggestions derived from private / org / public blocks.
    def mk_sug(text, ids):
        s = models.ConsolidationSuggestion(
            group_id=uuid.uuid4(), suggested_content=text,
            suggested_lessons_learned=text, suggested_keywords=[text],
            original_memory_ids=[str(i) for i in ids], status="pending")
        db.add(s)
        db.flush()
        return s

    # A long private block with no keyword: feeds the optimisation analysers.
    blk_priv_long = mk_block(agent_priv, f"long {PRIV} " + ("x" * 1600), "personal", owner=a.id)
    # A public block that also carries A's private keyword.
    blk_pub_tagged = mk_block(agent_pub, f"open tagged {PUBM}", "public", owner=a.id, kw=kw_priv)

    sug_priv = mk_sug(f"merged {PRIV}", [blk_priv.id])
    # Suggestion merging a private AND a public block: its text embeds private content.
    sug_mixed = mk_sug(f"mixed {PRIV}", [blk_pub.id, blk_priv.id])
    sug_org = mk_sug(f"merged {ORGM}", [blk_org.id])
    sug_pub = mk_sug(f"merged {PUBM}", [blk_pub.id])
    db.commit()

    def pat_for(user):
        payload = schemas.TokenCreateRequest(name="iso", scopes=["read"])
        _p, token = token_repo.create_token(db, user_id=user.id, payload=payload)
        return {"Authorization": f"Bearer {token}"}

    class W:
        pass

    w = W()
    w.a, w.b, w.c, w.org = a, b, c, org
    w.priv_ids = {str(blk_priv.id), str(blk_priv_arch.id), str(agent_priv.agent_id),
                  str(kw_priv.keyword_id), str(sug_priv.suggestion_id),
                  str(sug_mixed.suggestion_id), str(blk_priv_long.id)}
    w.org_ids = {str(blk_org.id), str(agent_org.agent_id), str(kw_org.keyword_id),
                 str(sug_org.suggestion_id)}
    w.blk_priv, w.blk_priv_arch, w.blk_org, w.blk_pub = blk_priv, blk_priv_arch, blk_org, blk_pub
    w.agent_priv, w.agent_org, w.agent_pub = agent_priv, agent_org, agent_pub
    w.kw_priv, w.kw_org, w.kw_pub = kw_priv, kw_org, kw_pub
    w.sug_mixed, w.blk_priv_long, w.blk_pub_tagged = sug_mixed, blk_priv_long, blk_pub_tagged
    w.sug_priv, w.sug_org, w.sug_pub = sug_priv, sug_org, sug_pub
    w.pat_b = pat_for(b)
    w.pat_a = pat_for(a)
    return w


def _client() -> TestClient:
    return TestClient(app)


def _routes(w):
    """(label, path, params) for every GET content route."""
    r = []
    r += [("blocks-list", "/memory-blocks/", {}),
          ("blocks-by-id", f"/memory-blocks/{w.blk_priv.id}", {}),
          ("blocks-by-id-archived", f"/memory-blocks/{w.blk_priv_arch.id}", {}),
          ("blocks-keywords", f"/memory-blocks/{w.blk_priv.id}/keywords/", {}),
          ("blocks-archived", "/memory-blocks/archived/", {})]
    for p in SEARCH_PATHS:
        r.append((f"search {p}", p, {"query": PRIV, "limit": 50}))
        r.append((f"search-org {p}", p, {"query": ORGM, "limit": 50}))
    r += [("agents-list", "/agents/", {}),
          ("agents-by-id", f"/agents/{w.agent_priv.agent_id}", {}),
          ("agents-search", "/agents/search/", {"query": PRIV}),
          ("keywords-list", "/keywords/", {}),
          ("keywords-by-id", f"/keywords/{w.kw_priv.keyword_id}", {}),
          ("keyword-blocks", f"/keywords/{w.kw_priv.keyword_id}/memory-blocks/", {}),
          ("keyword-blocks-count", f"/keywords/{w.kw_priv.keyword_id}/memory-blocks/count", {}),
          ("consol-list", "/consolidation-suggestions/", {}),
          ("consol-by-id", f"/consolidation-suggestions/{w.sug_priv.suggestion_id}", {}),
          ("optim-suggestions", "/memory-optimization/suggestions", {}),
          ("optim-preview", f"/memory-optimization/suggestions/{uuid.uuid4()}/preview", {}),
          ("conv-count", "/conversations/count", {}),
          ("notifications", "/notifications/", {}),
          ("audits", "/audits/", {}),
          ("inventory", f"/bulk-operations/organizations/{w.org.id}/inventory", {})]
    return r


def _assert_no_leak(label, resp, w, hints, forbidden_markers, forbidden_ids):
    body = resp.text
    for m in forbidden_markers:
        assert m not in body, f"LEAK [{label}] hints={hints}: marker {m} in {resp.status_code} {body[:300]}"
    for i in forbidden_ids:
        assert i not in body, f"LEAK [{label}] hints={hints}: id {i} in {resp.status_code} {body[:300]}"
    # by-id style routes must refuse
    if "by-id" in label or label in ("blocks-keywords", "keyword-blocks", "keyword-blocks-count"):
        assert resp.status_code in (401, 403, 404) or resp.status_code == 200 and not _has_content(resp), (
            f"[{label}] hints={hints}: {resp.status_code} {body[:200]}")


def _has_content(resp):
    try:
        data = resp.json()
    except Exception:
        return True
    return bool(data) and data not in ({"count": 0}, 0)


def _extra_hint_variants(w):
    out = list(HINT_SETS)
    out.append({"X-Active-Scope": "organization", "X-Organization-Id": str(w.org.id)})
    return out


def _run_denied(w, base_headers, *, include_org=False):
    leaks_markers = [PRIV, ORGM] if include_org else [PRIV]
    leak_ids = w.priv_ids | w.org_ids if include_org else w.priv_ids
    for hints in _extra_hint_variants(w):
        headers = {**base_headers, **hints}
        for label, path, params in _routes(w):
            resp = _client().get(path, params=params, headers=headers)
            _assert_no_leak(label, resp, w, hints, leaks_markers, leak_ids)
            # also try explicit org narrowing via query
            q = {**params, "scope": "organization", "organization_id": str(w.org.id)}
            resp = _client().get(path, params=q, headers=headers)
            _assert_no_leak(label + "+orgq", resp, w, hints, leaks_markers, leak_ids)


def test_anonymous_never_sees_private(world):
    _run_denied(world, {})


def test_guest_api_prefix_style_anonymous_never_sees_private(world):
    # The dashboard proxies /guest-api/* to the same routes with no identity;
    # a hostile client may also forge identity-looking headers the proxy strips.
    _run_denied(world, {"x-active-scope": "personal"})


def test_anonymous_never_sees_org_rows(world):
    for hints in _extra_hint_variants(world):
        for label, path, params in _routes(world):
            resp = _client().get(path, params=params, headers=hints)
            _assert_no_leak(label, resp, world, hints, [ORGM], world.org_ids)
            resp = _client().get(path, params={**params, "scope": "organization",
                                               "organization_id": str(world.org.id)}, headers=hints)
            _assert_no_leak(label + "+orgq", resp, world, hints, [ORGM], world.org_ids)


def test_other_user_never_sees_private_or_org(world):
    _run_denied(world, _identity(world.b.email), include_org=True)


def test_other_user_pat_never_sees_private_or_org(world):
    _run_denied(world, world.pat_b, include_org=True)


def test_org_scoped_pat_of_other_user_blocked(world, db_session):
    payload = schemas.TokenCreateRequest(name="iso-org", scopes=["read"], organization_id=world.org.id)
    _p, token = token_repo.create_token(db_session, user_id=world.b.id, payload=payload)
    headers = {"Authorization": f"Bearer {token}"}
    for label, path, params in _routes(world):
        resp = _client().get(path, params=params, headers=headers)
        _assert_no_leak(label, resp, world, {}, [PRIV, ORGM], world.priv_ids | world.org_ids)


# --------------------------- positive controls ----------------------------

def _get(w, path, headers, **params):
    return _client().get(path, params=params, headers=headers)


def test_owner_sees_own_private_rows(world):
    h = {**_identity(world.a.email), "X-Active-Scope": "personal"}
    assert _get(world, f"/memory-blocks/{world.blk_priv.id}", h).status_code == 200
    assert _get(world, f"/agents/{world.agent_priv.agent_id}", h).status_code == 200
    assert _get(world, f"/keywords/{world.kw_priv.keyword_id}", h).status_code == 200
    for path in ("/memory-blocks/", "/agents/", "/keywords/"):
        assert PRIV in _get(world, path, h, limit=100).text, path
    assert PRIV in _get(world, "/memory-blocks/archived/", h).text
    assert PRIV in _get(world, "/agents/search/", h, query=PRIV).text
    for p in ("/memory-blocks/search/", "/memory-blocks/search/fulltext"):
        assert PRIV in _get(world, p, h, query=PRIV).text, p
    assert PRIV in _get(world, f"/keywords/{world.kw_priv.keyword_id}/memory-blocks/", h).text
    assert PRIV in _get(world, f"/memory-blocks/{world.blk_priv.id}/keywords/", h).text
    assert _get(world, f"/consolidation-suggestions/{world.sug_priv.suggestion_id}", h).status_code == 200


def test_owner_pat_sees_own_private_rows(world):
    h = {**world.pat_a, "X-Active-Scope": "personal"}
    assert _get(world, f"/memory-blocks/{world.blk_priv.id}", h).status_code == 200
    assert PRIV in _get(world, "/memory-blocks/search/fulltext", h, query=PRIV).text


def test_org_member_sees_org_rows_but_not_other_members_private(world):
    h = {**_identity(world.c.email), "X-Active-Scope": "organization",
         "X-Organization-Id": str(world.org.id)}
    assert _get(world, f"/memory-blocks/{world.blk_org.id}", h).status_code == 200
    assert ORGM in _get(world, "/memory-blocks/", h, limit=100).text
    assert ORGM in _get(world, "/memory-blocks/search/fulltext", h, query=ORGM).text
    assert ORGM in _get(world, "/agents/", h).text
    assert ORGM in _get(world, "/keywords/", h).text
    # C is an org member but NOT the owner of A's personal rows.
    assert _get(world, f"/memory-blocks/{world.blk_priv.id}", h).status_code in (403, 404)
    for label, path, params in _routes(world):
        resp = _client().get(path, params=params, headers=h)
        _assert_no_leak(label, resp, world, h, [PRIV], world.priv_ids)


def test_public_rows_visible_to_anonymous_with_true_scope_labels(world):
    resp = _get(world, f"/memory-blocks/{world.blk_pub.id}", {})
    assert resp.status_code == 200
    assert resp.json()["visibility_scope"] == "public"
    for p in SEARCH_PATHS[:2]:
        rows = _get(world, p, {}, query=PUBM).json()
        hit = [x for x in rows if x["id"] == str(world.blk_pub.id)]
        assert hit, p
        assert hit[0]["visibility_scope"] == "public", p
        assert hit[0]["owner_user_id"] == str(world.a.id), p


def test_basic_search_labels_reflect_db_scope(world):
    """Regression: basic search used to rebuild rows without scope/owner and
    serialise public rows as personal with owner_user_id=null."""
    h = {**_identity(world.c.email), "X-Active-Scope": "organization",
         "X-Organization-Id": str(world.org.id)}
    rows = _get(world, "/memory-blocks/search/", h, query=ORGM).json()
    row = next(x for x in rows if x["id"] == str(world.blk_org.id))
    assert row["visibility_scope"] == "organization"
    assert row["organization_id"] == str(world.org.id)


# ------------------------- aggregates / counts ----------------------------

def test_conversation_count_ignores_other_users_private_rows(world, db_session):
    public_convs = (
        db_session.query(models.MemoryBlock.conversation_id)
        .filter(models.MemoryBlock.visibility_scope == "public",
                models.MemoryBlock.archived == False)  # noqa: E712
        .distinct().count()
    )
    ha = {**_identity(world.a.email), "X-Active-Scope": "personal"}
    assert _get(world, "/conversations/count", ha).json()["count"] == 2  # A's two non-archived private blocks
    for hints in _extra_hint_variants(world):
        for headers in ({**hints}, {**_identity(world.b.email), **hints}, {**world.pat_b, **hints}):
            count = _get(world, "/conversations/count", headers).json()["count"]
            # Outsiders can only ever count public conversations: never A's
            # private block or the org's block.
            assert count <= public_convs, (headers, count, public_convs)


def test_optimization_suggestions_do_not_leak_other_users_data(world):
    for headers in ({}, {**_identity(world.b.email), "X-Active-Scope": "personal"}, world.pat_b):
        resp = _client().get("/memory-optimization/suggestions", headers=headers)
        assert PRIV not in resp.text
        for i in world.priv_ids:
            assert i not in resp.text


def test_consolidation_list_hides_private_and_org_for_outsiders(world):
    for headers in ({}, {**_identity(world.b.email), "X-Active-Scope": "personal"}, world.pat_b):
        resp = _client().get("/consolidation-suggestions/", params={"limit": 200}, headers=headers)
        assert PRIV not in resp.text and ORGM not in resp.text
        for i in (str(world.sug_priv.suggestion_id), str(world.sug_org.suggestion_id)):
            assert i not in resp.text
            r2 = _client().get(f"/consolidation-suggestions/{i}", headers=headers)
            assert r2.status_code in (401, 403, 404)


def test_mixed_private_and_public_consolidation_suggestion_is_hidden(world):
    sid = str(world.sug_mixed.suggestion_id)
    for headers in ({}, {**_identity(world.b.email), "X-Active-Scope": "public"},
                    {**_identity(world.b.email), "X-Active-Scope": "personal"},
                    {**world.pat_b, "X-Active-Scope": "public"}):
        r = _client().get(f"/consolidation-suggestions/{sid}", headers=headers)
        assert r.status_code in (401, 403, 404), (headers, r.status_code, r.text[:200])
        lst = _client().get("/consolidation-suggestions/", params={"limit": 200}, headers=headers)
        assert sid not in lst.text and PRIV not in lst.text, headers


def test_optimization_suggestions_are_scoped_for_owner_and_outsiders(world):
    ha = {**_identity(world.a.email), "X-Active-Scope": "personal"}
    mine = _client().get("/memory-optimization/suggestions", headers=ha).text
    assert str(world.blk_priv_long.id) in mine       # control: owner sees own
    for headers in ({}, {**_identity(world.b.email), "X-Active-Scope": "personal"}, world.pat_b):
        body = _client().get("/memory-optimization/suggestions", headers=headers).text
        assert str(world.blk_priv_long.id) not in body


def test_public_block_does_not_expose_owners_private_keyword_text(world):
    """A public block tagged with a private keyword must not reveal that
    keyword's text to outsiders."""
    for headers in ({}, {**_identity(world.b.email)}):
        r = _client().get(f"/memory-blocks/{world.blk_pub_tagged.id}", headers=headers)
        assert r.status_code == 200
        assert PRIV not in r.text, "private keyword text leaked through a public block"
        lst = _client().get("/memory-blocks/", params={"limit": 200}, headers=headers)
        assert PRIV not in lst.text
        kws = _client().get(f"/memory-blocks/{world.blk_pub_tagged.id}/keywords/", headers=headers)
        assert PRIV not in kws.text
        kb = _client().get(f"/keywords/{world.kw_pub.keyword_id}/memory-blocks/", headers=headers)
        assert PRIV not in kb.text
        ar = _client().get("/memory-blocks/search/", params={"query": PUBM}, headers=headers)
        assert PRIV not in ar.text
        sr = _client().get("/memory-blocks/search/fulltext", params={"query": PUBM}, headers=headers)
        assert PRIV not in sr.text


# --------------------------- route-enumerating guard ----------------------

# GET routes covered by the contract above (path templates as registered).
COVERED_GET_ROUTES = {
    "/memory-blocks/", "/memory-blocks/{memory_id}", "/memory-blocks/{memory_id}/keywords/",
    "/memory-blocks/archived/", "/memory-blocks/search/", "/memory-blocks/search/fulltext",
    "/memory-blocks/search/semantic", "/memory-blocks/search/hybrid",
    "/agents/", "/agents/{agent_id}", "/agents/search/",
    "/keywords/", "/keywords/{keyword_id}", "/keywords/{keyword_id}/memory-blocks/",
    "/keywords/{keyword_id}/memory-blocks/count",
    "/consolidation-suggestions/", "/consolidation-suggestions/{suggestion_id}",
    "/memory-optimization/suggestions", "/memory-optimization/suggestions/{suggestion_id}/preview",
    "/conversations/count", "/notifications/", "/audits/",
    "/bulk-operations/organizations/{org_id}/inventory",
}

# Routes that serve no user content or are identity-/admin-gated and covered
# by dedicated suites (tests/integration/permissions, beta_access, organizations).
ALLOWLIST_GET_ROUTES = {
    "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc",
    "/health", "/build-info", "/user-info",
    "/users/me/tokens", "/notifications/stats", "/notifications/preferences",
    "/organizations/", "/organizations/manageable", "/organizations/admin",
    "/organizations/{org_id}", "/organizations/{org_id}/members",
    "/organizations/{org_id}/invitations",
    "/beta-access/status", "/beta-access/pending", "/beta-access/pending/stuck",
    "/beta-access/admin/users",
    "/bulk-operations/admin/operations/{operation_id}", "/bulk-operations/admin/operations",
}


def test_every_get_route_is_covered_by_the_read_isolation_contract():
    registered = {
        r.path for r in app.routes
        if getattr(r, "methods", None) and "GET" in r.methods
    }
    unknown = registered - COVERED_GET_ROUTES - ALLOWLIST_GET_ROUTES
    assert not unknown, (
        "New GET route(s) not covered by tests/integration/security/"
        f"test_read_isolation_contract.py: {sorted(unknown)}. Add them to "
        "_routes() + COVERED_GET_ROUTES (content) or ALLOWLIST_GET_ROUTES (non-content)."
    )
    stale = (COVERED_GET_ROUTES | ALLOWLIST_GET_ROUTES) - registered
    assert not stale, f"Routes listed but no longer registered: {sorted(stale)}"


@pytest.mark.parametrize("path", [
    "/users/me/tokens", "/organizations/manageable", "/organizations/admin",
    "/beta-access/pending", "/beta-access/pending/stuck", "/beta-access/admin/users",
    "/bulk-operations/admin/operations", "/notifications/stats", "/notifications/preferences",
])
def test_allowlisted_identity_routes_refuse_anonymous(path):
    resp = _client().get(path)
    assert resp.status_code in (401, 403, 422), f"{path} -> {resp.status_code}"


def test_organizations_listing_hides_other_users_orgs(world):
    h = {**_identity(world.b.email)}
    for path in ("/organizations/", f"/organizations/{world.org.id}",
                 f"/organizations/{world.org.id}/members", f"/organizations/{world.org.id}/invitations"):
        resp = _client().get(path, headers=h)
        assert str(world.a.id) not in resp.text, path
        assert world.a.email not in resp.text, path
        assert str(world.c.id) not in resp.text, path

"""Governance: only a superadmin can make content public, and it is audited.

Covers every write path that can create or modify a row so that it ends up with
visibility_scope='public' (memory blocks, agents, keywords), plus a route
enumerating guard that fails CI when a new write route exposing a scope field is
not accounted for in PUBLISH_ROUTE_ALLOWLIST below.

See docs/PUBLIC_CONTENT_GOVERNANCE.md for the written inventory.
"""
import uuid

import pytest
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


PUBLIC = {"X-Active-Scope": "public"}


# --------------------------------------------------------------------------- helpers

def _user(db: Session, tag: str, *, superadmin: bool = False) -> models.User:
    email = f"{tag}-{uuid.uuid4().hex[:8]}@example.com"
    u = models.User(email=email, display_name=tag, is_superadmin=superadmin)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _hdr(user: models.User, **extra) -> dict:
    h = {"x-auth-request-user": user.display_name, "x-auth-request-email": user.email}
    h.update(extra)
    return h


def _org_with(db: Session, user: models.User, role: str) -> models.Organization:
    org = models.Organization(name=f"Org-{uuid.uuid4().hex[:6]}")
    db.add(org)
    db.commit()
    db.refresh(org)
    db.add(models.OrganizationMembership(
        organization_id=org.id, user_id=user.id, role=role, can_read=True, can_write=True))
    db.commit()
    return org


def _pat_hdr(db: Session, user: models.User, **extra) -> dict:
    _pat, token = token_repo.create_token(
        db, user_id=user.id,
        payload=schemas.TokenCreateRequest(name="gov", scopes=["read", "write"]))
    h = {"Authorization": f"Bearer {token}"}
    h.update(extra)
    return h


def _agent(db, scope="personal", owner=None, org=None) -> models.Agent:
    a = models.Agent(agent_name=f"A-{uuid.uuid4().hex[:8]}", visibility_scope=scope,
                     owner_user_id=owner.id if owner else None,
                     organization_id=org.id if org else None)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _memory(db, agent, scope="personal", owner=None, org=None) -> models.MemoryBlock:
    m = models.MemoryBlock(agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content="generic content",
                           visibility_scope=scope,
                           owner_user_id=owner.id if owner else None,
                           organization_id=org.id if org else None)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def _keyword(db, scope="personal", owner=None) -> models.Keyword:
    k = models.Keyword(keyword_text=f"kw{uuid.uuid4().hex[:8]}", visibility_scope=scope,
                       owner_user_id=owner.id if owner else None)
    db.add(k)
    db.commit()
    db.refresh(k)
    return k


def _public_counts(db: Session) -> dict:
    db.expire_all()
    return {
        "agents": db.query(models.Agent).filter(models.Agent.visibility_scope == "public").count(),
        "keywords": db.query(models.Keyword).filter(models.Keyword.visibility_scope == "public").count(),
        "memory_blocks": db.query(models.MemoryBlock).filter(models.MemoryBlock.visibility_scope == "public").count(),
    }


def _audit(db: Session, actor: models.User, action: str, status: str | None = None):
    db.expire_all()
    q = db.query(models.AuditLog).filter(models.AuditLog.actor_user_id == actor.id,
                                         models.AuditLog.action_type == action)
    if status:
        q = q.filter(models.AuditLog.status == status)
    return q.all()


# Actor factories: (label, builder returning (user, headers, extra_scope_headers_ok))
def _actor_user(db):
    u = _user(db, "plain")
    return u, _hdr(u, **PUBLIC)


def _actor_org_owner(db):
    u = _user(db, "orgowner")
    _org_with(db, u, "owner")
    return u, _hdr(u, **PUBLIC)


def _actor_org_admin(db):
    u = _user(db, "orgadmin")
    _org_with(db, u, "admin")
    return u, _hdr(u, **PUBLIC)


def _actor_pat(db):
    u = _user(db, "patholder")
    return u, _pat_hdr(db, u, **PUBLIC)


NON_SUPER_ACTORS = [_actor_user, _actor_org_owner, _actor_org_admin, _actor_pat]
ACTOR_IDS = ["user", "org_owner", "org_admin", "pat_holder"]


def _body(kind: str, db: Session) -> tuple[str, dict]:
    if kind == "agent":
        return "/agents/", {"agent_name": f"Gov-{uuid.uuid4().hex[:6]}"}
    if kind == "keyword":
        return "/keywords/", {"keyword_text": f"gov{uuid.uuid4().hex[:6]}"}
    ag = _agent(db, "personal", owner=_user(db, "agentowner"))
    return "/memory-blocks/", {"agent_id": str(ag.agent_id), "conversation_id": str(uuid.uuid4()),
                               "content": "generic content"}


KINDS = ["agent", "keyword", "memory_block"]
CREATE_ACTION = {"agent": "agent_create", "keyword": "keyword_create", "memory_block": "memory_create"}


# --------------------------------------------------------------------------- create

@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("make_actor", NON_SUPER_ACTORS, ids=ACTOR_IDS)
def test_create_public_refused_for_non_superadmin(client, db_session, kind, make_actor):
    user, headers = make_actor(db_session)
    path, body = _body(kind, db_session)
    before = _public_counts(db_session)
    r = client.post(path, json=body, headers=headers)
    assert r.status_code == 403, r.text
    assert _public_counts(db_session) == before
    # Refusal is audited ("who tried to publish").
    rows = _audit(db_session, user, CREATE_ACTION[kind], "failure")
    assert len(rows) == 1
    assert rows[0].metadata_json["to_scope"] == "public"
    assert _audit(db_session, user, CREATE_ACTION[kind], "success") == []


@pytest.mark.parametrize("kind", KINDS)
def test_create_public_via_query_param_refused_for_non_superadmin(client, db_session, kind):
    user = _user(db_session, "plain")
    path, body = _body(kind, db_session)
    before = _public_counts(db_session)
    r = client.post(f"{path}?scope=public", json=body, headers=_hdr(user, **{"X-Active-Scope": ""}))
    assert r.status_code == 403, r.text
    assert _public_counts(db_session) == before
    assert len(_audit(db_session, user, CREATE_ACTION[kind], "failure")) == 1


@pytest.mark.parametrize("kind", KINDS)
def test_body_visibility_scope_cannot_force_public(client, db_session, kind):
    """A body field visibility_scope=public is ignored; the request scope wins."""
    user = _user(db_session, "plain")
    path, body = _body(kind, db_session)
    body["visibility_scope"] = "public"
    before = _public_counts(db_session)
    r = client.post(path, json=body, headers=_hdr(user, **{"X-Active-Scope": "personal"}))
    assert r.status_code in (201, 403), r.text
    assert _public_counts(db_session) == before


@pytest.mark.parametrize("kind", KINDS)
def test_create_public_allowed_for_superadmin_and_audited(client, db_session, kind):
    admin = _user(db_session, "root", superadmin=True)
    path, body = _body(kind, db_session)
    r = client.post(path, json=body, headers=_hdr(admin, **PUBLIC))
    assert r.status_code == 201, r.text
    assert r.json()["visibility_scope"] == "public"
    rows = _audit(db_session, admin, CREATE_ACTION[kind], "success")
    assert len(rows) == 1
    assert rows[0].metadata_json["to_scope"] == "public"
    assert rows[0].metadata_json["from_scope"] is None


@pytest.mark.parametrize("kind", KINDS)
def test_create_public_allowed_for_superadmin_pat(client, db_session, kind):
    admin = _user(db_session, "root", superadmin=True)
    path, body = _body(kind, db_session)
    r = client.post(path, json=body, headers=_pat_hdr(db_session, admin, **PUBLIC))
    assert r.status_code == 201, r.text
    assert len(_audit(db_session, admin, CREATE_ACTION[kind], "success")) == 1


def test_anonymous_cannot_publish_and_writes_no_audit(client, db_session):
    audit_before = db_session.query(models.AuditLog).count()
    before = _public_counts(db_session)
    for path, body in (("/agents/", {"agent_name": "anon"}), ("/keywords/", {"keyword_text": "anon"})):
        r = client.post(path, json=body, headers=PUBLIC)
        assert r.status_code in (401, 403), r.text
    assert _public_counts(db_session) == before
    assert db_session.query(models.AuditLog).count() == audit_before


def test_public_memory_create_keywords_inherit_public_scope(client, db_session):
    admin = _user(db_session, "root", superadmin=True)
    path, body = _body("memory_block", db_session)
    body["content"] = "alpha bravo charlie delta echo foxtrot"
    r = client.post(path, json=body, headers=_hdr(admin, **PUBLIC))
    assert r.status_code == 201, r.text
    kws = db_session.query(models.Keyword).join(
        models.MemoryBlockKeyword, models.MemoryBlockKeyword.keyword_id == models.Keyword.keyword_id
    ).filter(models.MemoryBlockKeyword.memory_id == uuid.UUID(r.json()["id"])).all()
    assert all(k.visibility_scope == "public" for k in kws)


def test_personal_memory_create_never_creates_public_keywords(client, db_session):
    user = _user(db_session, "plain")
    ag = _agent(db_session, "personal", owner=user)
    before = _public_counts(db_session)
    r = client.post("/memory-blocks/", headers=_hdr(user, **{"X-Active-Scope": "personal"}), json={
        "agent_id": str(ag.agent_id), "conversation_id": str(uuid.uuid4()),
        "content": "alpha bravo charlie delta echo foxtrot"})
    assert r.status_code == 201, r.text
    assert _public_counts(db_session) == before


# --------------------------------------------------------------------------- change-scope

def _scope_target(kind: str, db: Session, owner: models.User):
    ag = _agent(db, "personal", owner=owner)
    if kind == "agent":
        return f"/agents/{ag.agent_id}/change-scope", ag, "agent_scope_change", models.Agent
    m = _memory(db, ag, "personal", owner=owner)
    return f"/memory-blocks/{m.id}/change-scope", m, "memory_scope_change", models.MemoryBlock


@pytest.mark.parametrize("kind", ["agent", "memory_block"])
@pytest.mark.parametrize("make_actor", [_actor_user, _actor_pat], ids=["owner", "owner_pat"])
def test_change_scope_to_public_refused_for_owner(client, db_session, kind, make_actor):
    owner, headers = make_actor(db_session)
    path, obj, action, model = _scope_target(kind, db_session, owner)
    r = client.post(path, json={"visibility_scope": "public"}, headers=headers)
    assert r.status_code == 403, r.text
    db_session.refresh(obj)
    assert obj.visibility_scope == "personal"
    rows = _audit(db_session, owner, action, "failure")
    assert len(rows) == 1 and rows[0].metadata_json["from_scope"] == "personal"
    assert rows[0].metadata_json["to_scope"] == "public"


@pytest.mark.parametrize("kind", ["agent", "memory_block"])
@pytest.mark.parametrize("role", ["owner", "admin"])
def test_change_scope_to_public_refused_for_org_admin_on_org_content(client, db_session, kind, role):
    actor = _user(db_session, "orgman")
    org = _org_with(db_session, actor, role)
    ag = _agent(db_session, "organization", org=org)
    if kind == "agent":
        path, obj, action = f"/agents/{ag.agent_id}/change-scope", ag, "agent_scope_change"
    else:
        obj = _memory(db_session, ag, "organization", org=org)
        path, action = f"/memory-blocks/{obj.id}/change-scope", "memory_scope_change"
    r = client.post(path, json={"visibility_scope": "public"}, headers=_hdr(actor))
    assert r.status_code == 403, r.text
    db_session.refresh(obj)
    assert obj.visibility_scope == "organization"
    assert len(_audit(db_session, actor, action, "failure")) == 1


@pytest.mark.parametrize("kind", ["agent", "memory_block"])
def test_change_scope_to_public_allowed_for_superadmin_and_audited(client, db_session, kind):
    admin = _user(db_session, "root", superadmin=True)
    path, obj, action, _m = _scope_target(kind, db_session, _user(db_session, "someone"))
    r = client.post(path, json={"visibility_scope": "public"}, headers=_hdr(admin))
    assert r.status_code == 200, r.text
    db_session.refresh(obj)
    assert obj.visibility_scope == "public"
    rows = _audit(db_session, admin, action, "success")
    assert len(rows) == 1
    assert rows[0].metadata_json["from_scope"] == "personal"
    assert rows[0].metadata_json["to_scope"] == "public"


@pytest.mark.parametrize("kind", ["agent", "memory_block"])
def test_every_scope_change_is_audited_with_from_and_to(client, db_session, kind):
    owner = _user(db_session, "plain")
    org = _org_with(db_session, owner, "owner")
    path, obj, action, _m = _scope_target(kind, db_session, owner)
    r = client.post(path, json={"visibility_scope": "organization", "organization_id": str(org.id)},
                    headers=_hdr(owner))
    assert r.status_code == 200, r.text
    rows = _audit(db_session, owner, action, "success")
    assert len(rows) == 1
    assert (rows[0].metadata_json["from_scope"], rows[0].metadata_json["to_scope"]) == ("personal", "organization")


def test_change_scope_public_refused_for_read_only_pat_of_superadmin(client, db_session):
    admin = _user(db_session, "root", superadmin=True)
    path, obj, _a, _m = _scope_target("memory_block", db_session, admin)
    _pat, token = token_repo.create_token(
        db_session, user_id=admin.id, payload=schemas.TokenCreateRequest(name="ro", scopes=["read"]))
    r = client.post(path, json={"visibility_scope": "public"}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403, r.text
    db_session.refresh(obj)
    assert obj.visibility_scope == "personal"


# --------------------------------------------------------------------------- update bodies

def test_keyword_update_body_cannot_publish(client, db_session):
    owner = _user(db_session, "plain")
    kw = _keyword(db_session, "personal", owner)
    r = client.put(f"/keywords/{kw.keyword_id}", json={"visibility_scope": "public"}, headers=_hdr(owner))
    assert r.status_code == 403, r.text
    db_session.refresh(kw)
    assert kw.visibility_scope == "personal"
    assert len(_audit(db_session, owner, "keyword_update", "failure")) == 1


def test_keyword_update_body_scope_change_unsupported_even_for_superadmin(client, db_session):
    admin = _user(db_session, "root", superadmin=True)
    kw = _keyword(db_session, "personal", _user(db_session, "someone"))
    r = client.put(f"/keywords/{kw.keyword_id}", json={"visibility_scope": "public"}, headers=_hdr(admin))
    assert r.status_code == 422
    db_session.refresh(kw)
    assert kw.visibility_scope == "personal"


def test_keyword_update_same_scope_still_works(client, db_session):
    owner = _user(db_session, "plain")
    kw = _keyword(db_session, "personal", owner)
    r = client.put(f"/keywords/{kw.keyword_id}",
                   json={"keyword_text": "renamed", "visibility_scope": "personal"}, headers=_hdr(owner))
    assert r.status_code == 200, r.text


@pytest.mark.parametrize("kind", ["agent", "memory_block"])
def test_update_body_visibility_scope_is_ignored(client, db_session, kind):
    owner = _user(db_session, "plain")
    ag = _agent(db_session, "personal", owner=owner)
    if kind == "agent":
        obj, path, body = ag, f"/agents/{ag.agent_id}", {"agent_name": f"Renamed-{uuid.uuid4().hex[:4]}"}
    else:
        obj = _memory(db_session, ag, "personal", owner=owner)
        path, body = f"/memory-blocks/{obj.id}", {"content": "edited"}
    body.update({"visibility_scope": "public", "organization_id": None, "owner_user_id": None})
    r = client.put(path, json=body, headers=_hdr(owner))
    assert r.status_code == 200, r.text
    db_session.refresh(obj)
    assert obj.visibility_scope == "personal"
    assert obj.owner_user_id == owner.id


def test_non_superadmin_cannot_edit_public_content(client, db_session):
    admin_owned = _agent(db_session, "public")
    mem = _memory(db_session, admin_owned, "public")
    user = _user(db_session, "plain")
    r = client.put(f"/memory-blocks/{mem.id}", json={"content": "tamper"}, headers=_hdr(user))
    assert r.status_code == 403
    r = client.put(f"/agents/{admin_owned.agent_id}", json={"agent_name": "tamper"}, headers=_hdr(user))
    assert r.status_code == 403


# --------------------------------------------------------------------------- consolidation

def _suggestion(db, originals):
    s = models.ConsolidationSuggestion(
        group_id=uuid.uuid4(), suggested_content="merged", suggested_lessons_learned="l",
        suggested_keywords=["merged"], original_memory_ids=[str(m.id) for m in originals], status="pending")
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_consolidation_of_personal_blocks_never_yields_public(client, db_session):
    owner = _user(db_session, "plain")
    ag = _agent(db_session, "personal", owner=owner)
    mems = [_memory(db_session, ag, "personal", owner=owner) for _ in range(2)]
    s = _suggestion(db_session, mems)
    before = _public_counts(db_session)
    r = client.post(f"/consolidation-suggestions/{s.suggestion_id}/validate/",
                    headers=_hdr(owner, **{"X-Active-Scope": "personal"}))
    assert r.status_code == 200, r.text
    assert _public_counts(db_session) == before


def test_consolidation_of_public_blocks_requires_superadmin(client, db_session):
    ag = _agent(db_session, "public")
    mems = [_memory(db_session, ag, "public") for _ in range(2)]
    s = _suggestion(db_session, mems)
    user = _user(db_session, "plain")
    r = client.post(f"/consolidation-suggestions/{s.suggestion_id}/validate/", headers=_hdr(user, **PUBLIC))
    assert r.status_code in (403, 404), r.text
    db_session.expire_all()
    assert all(not m.archived for m in mems)
    admin = _user(db_session, "root", superadmin=True)
    r = client.post(f"/consolidation-suggestions/{s.suggestion_id}/validate/", headers=_hdr(admin, **PUBLIC))
    assert r.status_code == 200, r.text
    assert _audit(db_session, admin, "consolidation_validate", "success")


def test_consolidation_refuses_mixed_scope_originals(client, db_session):
    """Mixing a public original into a personal bundle must not mint a public merge."""
    owner = _user(db_session, "plain")
    ag = _agent(db_session, "personal", owner=owner)
    mems = [_memory(db_session, ag, "personal", owner=owner), _memory(db_session, ag, "public")]
    s = _suggestion(db_session, mems)
    before = _public_counts(db_session)
    r = client.post(f"/consolidation-suggestions/{s.suggestion_id}/validate/", headers=_hdr(owner))
    assert r.status_code in (403, 404, 409), r.text
    assert _public_counts(db_session) == before


# --------------------------------------------------------------------------- bulk move

def test_bulk_move_destination_scope_is_never_public():
    from core.async_bulk_operations import BulkOperationTask as S
    for dest_org in (None, uuid.uuid4()):
        for dest_owner in (None, uuid.uuid4()):
            assert S._destination_visibility_scope(dest_org, dest_owner) in ("organization", "personal")


# --------------------------------------------------------------------------- block write guards (compress/apply, prune, bulk keywords)

def _write_requests(mem_id):
    return {
        "compress_apply": lambda c, h: c.post(f"/memory-blocks/{mem_id}/compress/apply",
                                              json={"compressed_content": "overwritten"}, headers=h),
        "prune_confirm": lambda c, h: c.post("/memory/prune/confirm",
                                             json={"memory_block_ids": [str(mem_id)]}, headers=h),
        "bulk_keywords": lambda c, h: c.post(
            "/memory-blocks/bulk-apply-keywords",
            json={"applications": [{"memory_block_id": str(mem_id), "selected_keywords": ["govkw"]}]}, headers=h),
    }


def _ok(route: str, r) -> bool:
    """Did the call actually modify the block?"""
    if route == "compress_apply":
        return r.status_code == 200
    body = r.json() if r.status_code == 200 else {}
    return bool(body.get("archived_count") if route == "prune_confirm" else body.get("successful_count"))


ROUTES = ["compress_apply", "prune_confirm", "bulk_keywords"]


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("target", ["other_personal", "public"])
def test_non_owner_cannot_modify_block_via_write_routes(client, db_session, route, target):
    owner = _user(db_session, "owner")
    ag = _agent(db_session, "personal", owner=owner) if target == "other_personal" else _agent(db_session, "public")
    mem = _memory(db_session, ag, target.replace("other_", ""), owner=owner if target == "other_personal" else None)
    intruder = _user(db_session, "intruder")
    r = _write_requests(mem.id)[route](client, _hdr(intruder, **{"X-Active-Scope": "personal"}))
    assert not _ok(route, r), r.text
    if route == "compress_apply":
        assert r.status_code == 403
    db_session.expire_all()
    db_session.refresh(mem)
    assert mem.content == "generic content" and not mem.archived
    assert db_session.query(models.MemoryBlockKeyword).filter_by(memory_id=mem.id).count() == 0
    assert _audit(db_session, intruder, "memory_update" if route != "prune_confirm" else "memory_archive", "failure")


@pytest.mark.parametrize("route", ROUTES)
def test_owner_can_modify_own_block_via_write_routes(client, db_session, route):
    owner = _user(db_session, "owner")
    mem = _memory(db_session, _agent(db_session, "personal", owner=owner), "personal", owner=owner)
    r = _write_requests(mem.id)[route](client, _hdr(owner, **{"X-Active-Scope": "personal"}))
    assert _ok(route, r), r.text


@pytest.mark.parametrize("route", ROUTES)
def test_superadmin_can_modify_public_block_via_write_routes(client, db_session, route):
    admin = _user(db_session, "root", superadmin=True)
    mem = _memory(db_session, _agent(db_session, "public"), "public")
    r = _write_requests(mem.id)[route](client, _hdr(admin, **PUBLIC))
    assert _ok(route, r), r.text


def test_bulk_apply_keywords_uses_block_scope_and_owner(client, db_session):
    owner = _user(db_session, "owner")
    mem = _memory(db_session, _agent(db_session, "personal", owner=owner), "personal", owner=owner)
    r = _write_requests(mem.id)["bulk_keywords"](client, _hdr(owner, **{"X-Active-Scope": "personal"}))
    assert r.json()["successful_count"] == 1, r.text
    kw = db_session.query(models.Keyword).filter_by(keyword_text="govkw").one()
    assert (kw.visibility_scope, kw.owner_user_id) == ("personal", owner.id)


def test_bulk_apply_keywords_on_public_block_creates_public_keyword_only_for_superadmin(client, db_session):
    admin = _user(db_session, "root", superadmin=True)
    mem = _memory(db_session, _agent(db_session, "public"), "public")
    r = _write_requests(mem.id)["bulk_keywords"](client, _hdr(admin, **PUBLIC))
    assert r.json()["successful_count"] == 1, r.text
    kw = db_session.query(models.Keyword).filter_by(keyword_text="govkw").one()
    assert kw.visibility_scope == "public"


# --------------------------------------------------------------------------- scope hints on other write routes

def _sweep_requests(mem_id, kw_id, sugg_id):
    return [
        ("post", f"/memory-blocks/{mem_id}/suggest-keywords", {}),
        ("post", f"/consolidation-suggestions/{sugg_id}/reject/", None),
        ("delete", f"/consolidation-suggestions/{sugg_id}", None),
        ("post", "/memory/prune/suggest", {}),
        ("post", "/memory/prune/confirm", {"memory_block_ids": [str(mem_id)]}),
        ("post", f"/memory-blocks/{mem_id}/compress", {}),
        ("post", f"/memory-blocks/{mem_id}/compress/apply", {"compressed_content": "x"}),
        ("post", "/memory-blocks/bulk-generate-keywords", {"memory_block_ids": [str(mem_id)]}),
        ("post", "/memory-blocks/bulk-apply-keywords",
         {"applications": [{"memory_block_id": str(mem_id), "selected_keywords": ["sweepkw"]}]}),
        ("post", "/memory-blocks/bulk-compact", {"memory_block_ids": [str(mem_id)]}),
        ("post", "/memory-optimization/suggestions/does-not-exist/execute", None),
    ]


@pytest.mark.parametrize("make_actor", [_actor_user, _actor_pat], ids=["user", "pat"])
def test_scope_hint_on_other_write_routes_cannot_publish(client, db_session, make_actor):
    """Routes that merely accept a `scope` hint must never leave anything public."""
    user, headers = make_actor(db_session)
    ag = _agent(db_session, "personal", owner=user)
    mem = _memory(db_session, ag, "personal", owner=user)
    kw = _keyword(db_session, "personal", user)
    sugg = _suggestion(db_session, [mem])
    before = _public_counts(db_session)
    for method, path, body in _sweep_requests(mem.id, kw.keyword_id, sugg.suggestion_id):
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        getattr(client, method)(path, **kwargs)
        db_session.rollback()
        assert _public_counts(db_session) == before, f"{method} {path} produced public content"


# --------------------------------------------------------------------------- route guard

# Write routes whose request body/query exposes (or could hide, if the body is an
# untyped dict) a field named visibility_scope / scope / target_scope. Each must be
# deliberately classified. Add a governance test, then list the route here.
GATED = "publish-gated: ensure_can_publish + tests above"
SWEEP = "scope hint only; no publish path, covered by test_scope_hint_on_other_write_routes_cannot_publish"
BLOCKW = "writes an existing block: can_write on every target; tests: test_*_via_write_routes"
BULK = "cannot yield public: test_bulk_move_destination_scope_is_never_public"
UNRELATED = "opaque body unrelated to content visibility (users/orgs/support)"

PUBLISH_ROUTE_ALLOWLIST = {
    ("POST", "/agents/"): GATED,
    ("POST", "/agents/{agent_id}/change-scope"): GATED,
    ("POST", "/keywords/"): GATED,
    ("PUT", "/keywords/{keyword_id}"): GATED,
    ("POST", "/memory-blocks/"): GATED,
    ("POST", "/memory-blocks/{memory_id}/change-scope"): GATED,
    ("POST", "/memory-blocks/{memory_id}/suggest-keywords"): SWEEP,
    ("POST", "/consolidation-suggestions/{suggestion_id}/validate/"):
        "merged block inherits originals' scope; tests: test_consolidation_*",
    ("POST", "/consolidation-suggestions/{suggestion_id}/reject/"): SWEEP,
    ("DELETE", "/consolidation-suggestions/{suggestion_id}"): SWEEP,
    ("POST", "/memory/prune/suggest"): SWEEP,
    ("POST", "/memory/prune/confirm"): BLOCKW,
    ("POST", "/memory-blocks/{memory_id}/compress"): SWEEP,
    ("POST", "/memory-blocks/{memory_id}/compress/apply"): BLOCKW,
    ("POST", "/memory-blocks/bulk-generate-keywords"): SWEEP,
    ("POST", "/memory-blocks/bulk-apply-keywords"): BLOCKW,
    ("POST", "/memory-blocks/bulk-compact"): SWEEP,
    ("POST", "/memory-optimization/suggestions/{suggestion_id}/execute"): SWEEP,
    ("POST", "/bulk-operations/organizations/{org_id}/bulk-move"): BULK,
    ("POST", "/bulk-operations/organizations/{org_id}/bulk-delete"): BULK,
    ("PATCH", "/users/me"): UNRELATED,
    ("POST", "/organizations/"): UNRELATED,
    ("PUT", "/organizations/{org_id}"): UNRELATED,
    ("POST", "/organizations/{org_id}/members"): UNRELATED,
    ("PUT", "/organizations/{org_id}/members/{member_user_id}"): UNRELATED,
    ("POST", "/support/contact"): UNRELATED,
}

_SCOPE_FIELDS = {"visibility_scope", "scope", "target_scope"}
_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _query_names(dependant) -> set:
    names = {p.name for p in dependant.query_params}
    for d in dependant.dependencies:
        names |= _query_names(d)
    return names


def _scope_exposure(route: APIRoute) -> bool:
    if _query_names(route.dependant) & _SCOPE_FIELDS:
        return True
    field = route.body_field
    if field is None:
        return False
    model_fields = getattr(field.type_, "model_fields", None)
    if model_fields is None:  # untyped dict / Any body can carry any key
        return True
    return bool(set(model_fields) & _SCOPE_FIELDS)


def _flagged_routes() -> set:
    out = set()
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods & _WRITE_METHODS:
                if _scope_exposure(route):
                    out.add((method, route.path))
    return out


def test_every_write_route_exposing_a_scope_field_is_governed():
    flagged = _flagged_routes()
    unlisted = sorted(flagged - set(PUBLISH_ROUTE_ALLOWLIST))
    assert not unlisted, (
        "New write route(s) accept a scope field (or an untyped body) but are not covered by the "
        "public-publish governance tests. Route public decisions through "
        "core.api.permissions.ensure_can_publish, add a test in this file, then list the route in "
        f"PUBLISH_ROUTE_ALLOWLIST and docs/PUBLIC_CONTENT_GOVERNANCE.md: {unlisted}")


def test_allowlist_has_no_stale_entries():
    stale = sorted(set(PUBLISH_ROUTE_ALLOWLIST) - _flagged_routes())
    assert not stale, f"Allowlist entries no longer match a flagged route; remove them: {stale}"

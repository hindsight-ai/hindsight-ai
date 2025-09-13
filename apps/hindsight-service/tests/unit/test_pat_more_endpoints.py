import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


def _mk_user(db: Session, email: str) -> models.User:
    u = models.User(email=email, display_name=email.split('@')[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_org_membership(db: Session, user: models.User) -> models.Organization:
    org = models.Organization(name=f"Org-{uuid.uuid4().hex[:6]}")
    db.add(org)
    db.commit()
    db.refresh(org)
    m = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role="admin", can_read=True, can_write=True)
    db.add(m)
    db.commit()
    return org


def _mk_agent(db: Session, scope: str, *, owner_user_id=None, organization_id=None) -> models.Agent:
    a = models.Agent(agent_name=f"A-{uuid.uuid4().hex[:6]}", visibility_scope=scope, owner_user_id=owner_user_id, organization_id=organization_id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _mk_memory(db: Session, agent_id, scope: str, *, owner_user_id=None, organization_id=None) -> models.MemoryBlock:
    mb = models.MemoryBlock(agent_id=agent_id, conversation_id=uuid.uuid4(), content="c", visibility_scope=scope, owner_user_id=owner_user_id, organization_id=organization_id)
    db.add(mb)
    db.commit()
    db.refresh(mb)
    return mb


def test_memory_block_update_pat_write_enforced(client: TestClient, db_session: Session):
    user = _mk_user(db_session, "updscope@example.com")
    org = _mk_org_membership(db_session, user)
    agent = _mk_agent(db_session, scope="organization", organization_id=org.id)
    mb = _mk_memory(db_session, agent_id=agent.agent_id, scope="organization", organization_id=org.id)

    # PAT with read only -> 403 on update
    pat_r, token_r = token_repo.create_token(db_session, user_id=user.id, payload=schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org.id))
    r = client.put(f"/memory-blocks/{mb.id}", json={"content": "new"}, headers={"Authorization": f"Bearer {token_r}"})
    assert r.status_code == 403

    # PAT with write -> 200
    pat_w, token_w = token_repo.create_token(db_session, user_id=user.id, payload=schemas.TokenCreateRequest(name="t2", scopes=["write"], organization_id=org.id))
    r2 = client.put(f"/memory-blocks/{mb.id}", json={"content": "newer"}, headers={"Authorization": f"Bearer {token_w}"})
    assert r2.status_code == 200, r2.text
    assert r2.json()["content"] == "newer"


def test_agents_get_pat_org_mismatch(client: TestClient, db_session: Session):
    user = _mk_user(db_session, "agetpat@example.com")
    org_a = _mk_org_membership(db_session, user)
    org_b = _mk_org_membership(db_session, _mk_user(db_session, "other@example.com"))
    agent_b = _mk_agent(db_session, scope="organization", organization_id=org_b.id)

    # PAT for org_a, attempt to GET agent in org_b -> 403
    pat, token = token_repo.create_token(db_session, user_id=user.id, payload=schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org_a.id))
    r = client.get(f"/agents/{agent_b.agent_id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code in (403, 404)


def test_search_fulltext_and_semantic_with_pat_headers(client: TestClient, db_session: Session):
    user = _mk_user(db_session, "patsearch2@example.com")
    org = _mk_org_membership(db_session, user)
    pat, token = token_repo.create_token(db_session, user_id=user.id, payload=schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org.id))

    # Fulltext and semantic endpoints should accept PAT headers and return 200 even when empty
    r1 = client.get("/memory-blocks/search/fulltext?query=zzz", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200
    r2 = client.get("/memory-blocks/search/semantic?query=zzz", headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 200


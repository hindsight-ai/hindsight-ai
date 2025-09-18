from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


def _mk_user(db: Session, email: str = "reader@example.com") -> models.User:
    u = models.User(email=email, display_name=email.split("@")[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_org_and_membership(db: Session, user: models.User):
    org_a = models.Organization(name="OrgA")
    org_b = models.Organization(name="OrgB")
    db.add_all([org_a, org_b])
    db.commit()
    db.refresh(org_a)
    db.refresh(org_b)
    # Make user a writer in OrgA only
    m = models.OrganizationMembership(organization_id=org_a.id, user_id=user.id, role="admin", can_read=True, can_write=True)
    db.add(m)
    db.commit()
    return org_a, org_b


def _mk_agent(db: Session, scope: str, owner_user_id=None, organization_id=None) -> models.Agent:
    a = models.Agent(agent_name=f"Agent-{uuid.uuid4().hex[:6]}", visibility_scope=scope, owner_user_id=owner_user_id, organization_id=organization_id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _mk_memory(db: Session, agent_id, scope: str, owner_user_id=None, organization_id=None, content="hello") -> models.MemoryBlock:
    mb = models.MemoryBlock(
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content=content,
        errors=None,
        lessons_learned=None,
        metadata_col=None,
        feedback_score=0,
        visibility_scope=scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )
    db.add(mb)
    db.commit()
    db.refresh(mb)
    return mb


def test_memory_blocks_list_pat_org_narrowing(db_session: Session):
    client = TestClient(app)
    user = _mk_user(db_session)
    org_a, org_b = _mk_org_and_membership(db_session, user)
    # Agents for each scope
    agent_a = _mk_agent(db_session, scope="organization", organization_id=org_a.id)
    agent_b = _mk_agent(db_session, scope="organization", organization_id=org_b.id)
    agent_pub = _mk_agent(db_session, scope="public")
    agent_personal = _mk_agent(db_session, scope="personal", owner_user_id=user.id)

    # Memory blocks across different scopes/orgs
    _mk_memory(db_session, agent_id=agent_a.agent_id, scope="organization", organization_id=org_a.id, content="A1")
    _mk_memory(db_session, agent_id=agent_b.agent_id, scope="organization", organization_id=org_b.id, content="B1")
    _mk_memory(db_session, agent_id=agent_pub.agent_id, scope="public", content="PUB1")
    _mk_memory(db_session, agent_id=agent_personal.agent_id, scope="personal", owner_user_id=user.id, content="ME1")

    # PAT restricted to org_a
    payload = schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org_a.id)
    pat, token = token_repo.create_token(db_session, user_id=user.id, payload=payload)

    r = client.get("/memory-blocks/?limit=100", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    data = r.json()
    items = data.get("items") or []
    # All items must be organization-scope and in org_a due to server-side narrowing
    assert len(items) >= 1
    for it in items:
        assert it["visibility_scope"] == "organization"
        assert it["organization_id"] == str(org_a.id)


def test_memory_blocks_list_pat_org_mismatch_rejected(db_session: Session):
    client = TestClient(app)
    user = _mk_user(db_session, email="mismatch@example.com")
    org_a, org_b = _mk_org_and_membership(db_session, user)
    payload = schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org_a.id)
    pat, token = token_repo.create_token(db_session, user_id=user.id, payload=payload)

    r = client.get(f"/memory-blocks/?organization_id={org_b.id}", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403
    assert "organization" in r.text.lower()


def test_memory_blocks_list_with_x_api_key_header(db_session: Session):
    client = TestClient(app)
    user = _mk_user(db_session, email="apikey@example.com")
    org, _ = _mk_org_and_membership(db_session, user)
    payload = schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org.id)
    pat, token = token_repo.create_token(db_session, user_id=user.id, payload=payload)

    r = client.get("/memory-blocks/?limit=1", headers={"X-API-Key": token})
    # No data created; endpoint should still 200 with structure
    assert r.status_code == 200, r.text
    data = r.json()
    assert "items" in data and "total_items" in data

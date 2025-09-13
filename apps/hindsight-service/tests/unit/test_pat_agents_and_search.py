import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.api.main import app
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


def _mk_user(db: Session, email: str) -> models.User:
    user = models.User(email=email, display_name=email.split('@')[0])
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _mk_org(db: Session, name: str) -> models.Organization:
    org = models.Organization(name=name)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def _add_membership(db: Session, org: models.Organization, user: models.User, role="admin"):
    m = models.OrganizationMembership(
        organization_id=org.id,
        user_id=user.id,
        role=role,
        can_read=True,
        can_write=True,
    )
    db.add(m)
    db.commit()
    return m


def _mk_agent(db: Session, name: str, scope: str, *, owner_user_id=None, organization_id=None) -> models.Agent:
    a = models.Agent(
        agent_name=name,
        visibility_scope=scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _mk_memory(db: Session, *, agent_id, scope: str, owner_user_id=None, organization_id=None, content: str):
    mb = models.MemoryBlock(
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content=content,
        visibility_scope=scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(mb)
    db.commit()
    db.refresh(mb)
    return mb


def test_agents_list_pat_org_narrowing(client: TestClient, db_session: Session):
    user = _mk_user(db_session, "narrows@example.com")
    org_a = _mk_org(db_session, "OrgA")
    org_b = _mk_org(db_session, "OrgB")
    _add_membership(db_session, org_a, user)

    a_in_a = _mk_agent(db_session, "A-Agent", scope="organization", organization_id=org_a.id)
    a_in_b = _mk_agent(db_session, "B-Agent", scope="organization", organization_id=org_b.id)
    _mk_agent(db_session, "Pub-Agent", scope="public")

    pat, token = token_repo.create_token(
        db_session,
        user_id=user.id,
        payload=schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org_a.id),
    )

    r = client.get("/agents/?limit=50", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    names = [a["agent_name"] for a in r.json()]
    assert "A-Agent" in names
    assert "B-Agent" not in names


def test_hybrid_search_pat_org_narrowing(client: TestClient, db_session: Session):
    # Data
    user = _mk_user(db_session, "searchpat@example.com")
    org_a = _mk_org(db_session, "OrgA")
    org_b = _mk_org(db_session, "OrgB")
    _add_membership(db_session, org_a, user)
    agent_a = _mk_agent(db_session, "AgentA", scope="organization", organization_id=org_a.id)
    agent_b = _mk_agent(db_session, "AgentB", scope="organization", organization_id=org_b.id)
    _mk_memory(db_session, agent_id=agent_a.agent_id, scope="organization", organization_id=org_a.id, content="alpha alpha")
    _mk_memory(db_session, agent_id=agent_b.agent_id, scope="organization", organization_id=org_b.id, content="alpha beta")

    # PAT restricted to org_a
    pat, token = token_repo.create_token(
        db_session,
        user_id=user.id,
        payload=schemas.TokenCreateRequest(name="t", scopes=["read"], organization_id=org_a.id),
    )

    # Hybrid search will fall back to basic search if fulltext returns no rows (e.g., unpopulated search_vector)
    r = client.get("/memory-blocks/search/hybrid?query=alpha&limit=10", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    items = r.json()
    assert items, "Expected at least one result for hybrid fallback"
    # Only memory blocks from AgentA (org_a) allowed under PAT org restriction
    for it in items:
        assert it.get("agent_id") == str(agent_a.agent_id)

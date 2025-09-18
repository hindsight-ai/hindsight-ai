import uuid
import pytest
from core.db.database import SessionLocal, engine
from core.db import models, schemas
from core.db import crud


@pytest.fixture(scope="module")
def db():
    models.Base.metadata.create_all(bind=engine)
    try:
        yield SessionLocal()
    finally:
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture(autouse=True)
def clean(db):
    for table in reversed(models.Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()


def _user(db, email: str, superadmin: bool = False):
    u = models.User(email=email, display_name=email.split('@')[0], is_superadmin=superadmin)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _org(db, name: str):
    o = models.Organization(name=name)
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


def test_create_get_update_delete_agent(db):
    user = _user(db, "owner@example.com")
    agent = crud.create_agent(db, schemas.AgentCreate(agent_name="Alpha", visibility_scope="personal", owner_user_id=user.id))
    fetched = crud.get_agent(db, agent.agent_id)
    assert fetched.agent_name == "Alpha"

    updated = crud.update_agent(db, agent.agent_id, schemas.AgentUpdate(agent_name="Alpha2"))
    assert updated.agent_name == "Alpha2"

    # delete
    ok = crud.delete_agent(db, agent.agent_id)
    assert ok is True
    assert crud.get_agent(db, agent.agent_id) is None


def test_get_agents_scope_filtering(db):
    public_agent = crud.create_agent(db, schemas.AgentCreate(agent_name="PublicA", visibility_scope="public"))
    owner = _user(db, "me@example.com")
    personal_agent = crud.create_agent(db, schemas.AgentCreate(agent_name="PersA", visibility_scope="personal", owner_user_id=owner.id))
    org = _org(db, "OrgX")
    # membership record
    m = models.OrganizationMembership(user_id=owner.id, organization_id=org.id, role="owner", can_read=True, can_write=True)
    db.add(m)
    db.commit()
    org_agent = crud.create_agent(db, schemas.AgentCreate(agent_name="OrgA", visibility_scope="organization", organization_id=org.id))

    # Unauthenticated (current_user=None) sees only public
    unauth = crud.get_agents(db, current_user=None)
    assert {a.agent_name for a in unauth} == {"PublicA"}

    # Authenticated user with membership sees public + personal + org
    current_user = {"id": owner.id, "is_superadmin": False, "memberships": [{"organization_id": str(org.id)}]}
    visible = crud.get_agents(db, current_user=current_user)
    assert {a.agent_name for a in visible} == {"PublicA", "PersA", "OrgA"}

    # Scope narrowing
    only_public = crud.get_agents(db, current_user=current_user, scope="public")
    assert [a.agent_name for a in only_public] == ["PublicA"]
    only_personal = crud.get_agents(db, current_user=current_user, scope="personal")
    assert [a.agent_name for a in only_personal] == ["PersA"]
    only_org = crud.get_agents(db, current_user=current_user, scope="organization")
    assert [a.agent_name for a in only_org] == ["OrgA"]

    # Organization filter further
    filtered = crud.get_agents(db, current_user=current_user, organization_id=org.id)
    assert [a.agent_name for a in filtered] == ["OrgA"]

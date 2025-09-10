import uuid
from core.db import models, crud, schemas


def test_get_agent_by_name_and_update(db_session):
    db = db_session
    owner = models.User(email=f"agentown_{uuid.uuid4().hex}@ex.com", display_name="AgentOwner", is_superadmin=False)
    db.add(owner); db.commit(); db.refresh(owner)
    org = models.Organization(name=f"AgOrg_{uuid.uuid4().hex[:6]}", slug=f"agorg-{uuid.uuid4().hex[:6]}", created_by=owner.id)
    db.add(org); db.commit(); db.refresh(org)

    personal = models.Agent(agent_name=f"Agent Personal {uuid.uuid4().hex[:4]}", visibility_scope="personal", owner_user_id=owner.id)
    public = models.Agent(agent_name=f"Agent Public {uuid.uuid4().hex[:4]}", visibility_scope="public")
    org_agent = models.Agent(agent_name=f"Agent Org {uuid.uuid4().hex[:4]}", visibility_scope="organization", organization_id=org.id)
    db.add_all([personal, public, org_agent]); db.commit(); [db.refresh(a) for a in [personal, public, org_agent]]

    # By name (case-insensitive) public
    fetched_public = crud.get_agent_by_name(db, public.agent_name.upper(), visibility_scope='public')
    assert fetched_public.agent_id == public.agent_id

    # Personal requires owner id
    fetched_personal = crud.get_agent_by_name(db, personal.agent_name.lower(), visibility_scope='personal', owner_user_id=owner.id)
    assert fetched_personal.agent_id == personal.agent_id

    # Org requires org id as invalid string (should not find)
    fetched_org_invalid = crud.get_agent_by_name(db, org_agent.agent_name, visibility_scope='organization', organization_id=uuid.uuid4())
    assert fetched_org_invalid is None

    # Update agent name
    upd = schemas.AgentUpdate(agent_name=personal.agent_name + " X") if hasattr(schemas, 'AgentUpdate') else None
    if upd:
        updated_agent = crud.update_agent(db, personal.agent_id, upd)
        assert updated_agent.agent_name.endswith(" X")

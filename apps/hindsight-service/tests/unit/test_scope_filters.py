import uuid
import itertools
from core.db import models, crud

# Helper to build current_user dict

def _user_ctx(user, memberships=None, is_superadmin=False):
    memberships = memberships or []
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": is_superadmin,
        "memberships": memberships,
        "memberships_by_org": {m["organization_id"]: m for m in memberships},
    }



def _seed_base(db):
    # Users
    guest = None  # Represented by None current_user
    owner = models.User(email=f"owner_{uuid.uuid4().hex}@example.com", display_name="Owner", is_superadmin=False)
    org_user = models.User(email=f"orguser_{uuid.uuid4().hex}@example.com", display_name="OrgUser", is_superadmin=False)
    superadmin = models.User(email=f"sa_{uuid.uuid4().hex}@example.com", display_name="SA", is_superadmin=True)
    db.add_all([owner, org_user, superadmin])
    db.commit(); [db.refresh(u) for u in [owner, org_user, superadmin]]

    # Organization + memberships
    # Randomize org name/slug to avoid uniqueness collisions across test runs
    suffix = uuid.uuid4().hex[:6]
    org = models.Organization(name=f"Scope Org {suffix}", slug=f"scope-org-{suffix}", created_by=owner.id)
    db.add(org); db.commit(); db.refresh(org)
    mem_owner = models.OrganizationMembership(organization_id=org.id, user_id=owner.id, role="owner", can_read=True, can_write=True)
    mem_user = models.OrganizationMembership(organization_id=org.id, user_id=org_user.id, role="viewer", can_read=True, can_write=False)
    db.add_all([mem_owner, mem_user]); db.commit()

    # Agents (personal, org, public owned by different users)
    # Randomize names to avoid unique constraints (especially public lower() index)
    rand = uuid.uuid4().hex[:6]
    personal_agent = models.Agent(agent_name=f"Personal A {rand}", visibility_scope="personal", owner_user_id=owner.id)
    org_agent = models.Agent(agent_name=f"Org A {rand}", visibility_scope="organization", organization_id=org.id)
    public_agent = models.Agent(agent_name=f"Public A {rand}", visibility_scope="public")
    db.add_all([personal_agent, org_agent, public_agent]); db.commit()

    # Keywords
    personal_kw = models.Keyword(keyword_text=f"pkw_{rand}", visibility_scope="personal", owner_user_id=owner.id)
    org_kw = models.Keyword(keyword_text=f"okw_{rand}", visibility_scope="organization", organization_id=org.id)
    public_kw = models.Keyword(keyword_text=f"pukw_{rand}", visibility_scope="public")
    db.add_all([personal_kw, org_kw, public_kw]); db.commit()

    return {
        "users": {"owner": owner, "org_user": org_user, "superadmin": superadmin},
        "org": org,
        "agents": {"personal": personal_agent, "org": org_agent, "public": public_agent},
        "keywords": {"personal": personal_kw, "org": org_kw, "public": public_kw},
    }


def test_agent_scope_filters(db_session):
    db = db_session
    state = _seed_base(db)
    owner_ctx = _user_ctx(state["users"]["owner"], memberships=[{"organization_id": str(state["org"].id), "role": "owner", "can_read": True, "can_write": True}])
    org_user_ctx = _user_ctx(state["users"]["org_user"], memberships=[{"organization_id": str(state["org"].id), "role": "viewer", "can_read": True, "can_write": False}])
    superadmin_ctx = _user_ctx(state["users"]["superadmin"], memberships=[] , is_superadmin=True)

    # Guest should only see public
    guest_agents = crud.get_agents(db, current_user=None)
    # Derive expected names from seeded state
    all_names = {a.agent_name for a in crud.get_agents(db, current_user=superadmin_ctx)}
    public_name = [n for n in all_names if n.startswith("Public A ")][0]
    personal_name = [n for n in all_names if n.startswith("Personal A ")][0]
    org_name = [n for n in all_names if n.startswith("Org A ")][0]
    assert {a.agent_name for a in guest_agents} == {public_name}

    # Owner should see personal + org + public
    owner_agents = crud.get_agents(db, current_user=owner_ctx)
    assert {a.agent_name for a in owner_agents} == {personal_name, org_name, public_name}

    # Org viewer (no personal) should see org + public
    org_user_agents = crud.get_agents(db, current_user=org_user_ctx)
    assert {a.agent_name for a in org_user_agents} == {org_name, public_name}

    # Superadmin sees all
    sa_agents = crud.get_agents(db, current_user=superadmin_ctx)
    assert {a.agent_name for a in sa_agents} == {personal_name, org_name, public_name}


def test_keyword_scope_filters(db_session):
    db = db_session
    state = _seed_base(db)
    owner_ctx = _user_ctx(state["users"]["owner"], memberships=[{"organization_id": str(state["org"].id), "role": "owner", "can_read": True, "can_write": True}])
    org_user_ctx = _user_ctx(state["users"]["org_user"], memberships=[{"organization_id": str(state["org"].id), "role": "viewer", "can_read": True, "can_write": False}])
    superadmin_ctx = _user_ctx(state["users"]["superadmin"], memberships=[] , is_superadmin=True)

    guest_kws = crud.get_keywords(db, current_user=None)
    # Determine created keyword names dynamically
    all_kw = {k.keyword_text for k in crud.get_keywords(db, current_user=superadmin_ctx)}
    public_kw = [k for k in all_kw if k.startswith("pukw_")][0]
    personal_kw = [k for k in all_kw if k.startswith("pkw_")][0]
    org_kw = [k for k in all_kw if k.startswith("okw_")][0]
    assert {k.keyword_text for k in guest_kws} == {public_kw}

    owner_kws = crud.get_keywords(db, current_user=owner_ctx)
    assert {k.keyword_text for k in owner_kws} == {personal_kw, org_kw, public_kw}

    org_user_kws = crud.get_keywords(db, current_user=org_user_ctx)
    assert {k.keyword_text for k in org_user_kws} == {org_kw, public_kw}

    sa_kws = crud.get_keywords(db, current_user=superadmin_ctx)
    assert {k.keyword_text for k in sa_kws} == {personal_kw, org_kw, public_kw}

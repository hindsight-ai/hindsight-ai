import uuid
from typing import Tuple

from core.db import models


def create_agent(db, *, owner_user_id=None, organization_id=None, visibility_scope='personal') -> models.Agent:
    agent = models.Agent(
        agent_name=f"Agent {uuid.uuid4().hex[:6]}",
        visibility_scope=visibility_scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def create_memory_block(
    db,
    *,
    agent_id,
    visibility_scope='personal',
    owner_user_id=None,
    organization_id=None,
    content='c',
) -> models.MemoryBlock:
    mb = models.MemoryBlock(
        agent_id=agent_id,
        conversation_id=uuid.uuid4(),
        content=content,
        lessons_learned='ll',
        visibility_scope=visibility_scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )
    db.add(mb)
    db.commit()
    db.refresh(mb)
    return mb


def create_suggestion(db, original_ids) -> models.ConsolidationSuggestion:
    s = models.ConsolidationSuggestion(
        group_id=uuid.uuid4(),
        suggested_content='sc',
        suggested_lessons_learned='sll',
        suggested_keywords=['k1','k2'],
        original_memory_ids=[str(x) for x in original_ids],
        status='pending',
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def test_consolidation_suggestions_scoped_listing(client, db_session, user_factory, organization_factory, membership_factory):
    db = db_session
    # User and orgs
    user = user_factory('owner@example.com')
    org_a = organization_factory('Org A')
    org_b = organization_factory('Org B')
    membership_factory(org_a, user, role='owner', can_write=True)

    # Agents for each context
    agent_personal = create_agent(db, owner_user_id=user.id, visibility_scope='personal')
    agent_org_a = create_agent(db, organization_id=org_a.id, visibility_scope='organization')
    agent_org_b = create_agent(db, organization_id=org_b.id, visibility_scope='organization')
    agent_public = create_agent(db, visibility_scope='public')

    # Memory blocks for each scope
    mb_personal = create_memory_block(db, agent_id=agent_personal.agent_id, visibility_scope='personal', owner_user_id=user.id)
    mb_org_a = create_memory_block(db, agent_id=agent_org_a.agent_id, visibility_scope='organization', organization_id=org_a.id)
    mb_org_b = create_memory_block(db, agent_id=agent_org_b.agent_id, visibility_scope='organization', organization_id=org_b.id)
    mb_public = create_memory_block(db, agent_id=agent_public.agent_id, visibility_scope='public')

    # Suggestions referencing each block
    s_personal = create_suggestion(db, [mb_personal.id])
    s_org_a = create_suggestion(db, [mb_org_a.id])
    s_org_b = create_suggestion(db, [mb_org_b.id])
    s_public = create_suggestion(db, [mb_public.id])

    base = "/consolidation-suggestions/"
    headers = {"X-Auth-Request-Email": user.email}

    # Organization A scope: see only org A suggestion
    r = client.get(f"{base}?skip=0&limit=50", headers={**headers, "X-Active-Scope":"organization", "X-Organization-Id": str(org_a.id)})
    assert r.status_code == 200
    data = r.json()
    ids = {item['suggestion_id'] for item in data['items']}
    assert ids == {str(s_org_a.suggestion_id)}
    assert data['total_items'] == len(data['items'])

    # Personal scope: only personal
    r = client.get(f"{base}?skip=0&limit=50", headers={**headers, "X-Active-Scope":"personal"})
    assert r.status_code == 200
    data = r.json()
    ids = {item['suggestion_id'] for item in data['items']}
    assert ids == {str(s_personal.suggestion_id)}

    # Public scope: only public
    r = client.get(f"{base}?skip=0&limit=50", headers={**headers, "X-Active-Scope":"public"})
    assert r.status_code == 200
    data = r.json()
    ids = {item['suggestion_id'] for item in data['items']}
    assert ids == {str(s_public.suggestion_id)}

    # Organization B scope: user is not member; should see nothing
    r = client.get(f"{base}?skip=0&limit=50", headers={**headers, "X-Active-Scope":"organization", "X-Organization-Id": str(org_b.id)})
    assert r.status_code == 200
    data = r.json()
    assert data['items'] == []
    assert data['total_items'] == 0


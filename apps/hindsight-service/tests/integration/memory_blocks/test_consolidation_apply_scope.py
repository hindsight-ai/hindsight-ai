import uuid
from core.db import models, crud, schemas


def test_apply_consolidation_preserves_scope_and_keywords(db_session):
    db = db_session
    # Create user and org
    user = models.User(email='u@example.com', display_name='u')
    db.add(user); db.commit(); db.refresh(user)
    org = models.Organization(name='OrgX')
    db.add(org); db.commit(); db.refresh(org)
    db.add(models.OrganizationMembership(organization_id=org.id, user_id=user.id, role='owner', can_read=True, can_write=True)); db.commit()

    # Create agent and memory in org scope
    agent = models.Agent(agent_name='A', visibility_scope='organization', organization_id=org.id)
    db.add(agent); db.commit(); db.refresh(agent)
    mb1 = models.MemoryBlock(agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content='c1', visibility_scope='organization', organization_id=org.id)
    mb2 = models.MemoryBlock(agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content='c2', visibility_scope='organization', organization_id=org.id)
    db.add(mb1); db.add(mb2); db.commit(); db.refresh(mb1); db.refresh(mb2)

    # Create suggestion
    sugg = schemas.ConsolidationSuggestionCreate(
        group_id=uuid.uuid4(),
        suggested_content='merged',
        suggested_lessons_learned='lessons',
        suggested_keywords=['alpha','beta'],
        original_memory_ids=[str(mb1.id), str(mb2.id)],
        status='pending',
    )
    s = crud.create_consolidation_suggestion(db, sugg)

    # Apply consolidation
    new_mb = crud.apply_consolidation(db, s.suggestion_id)
    assert new_mb is not None
    assert new_mb.visibility_scope == 'organization'
    assert new_mb.organization_id == org.id
    # Keywords created with same scope
    kws = new_mb.keywords
    texts = sorted([k.keyword_text for k in kws])
    assert texts == ['alpha','beta']
    for k in kws:
        assert k.visibility_scope == 'organization'
        assert k.organization_id == org.id


def test_reject_consolidation_does_not_create_new_block(db_session):
    db = db_session
    # Ensure an agent exists so the memory block FK is satisfied
    agent = models.Agent(agent_name='TmpAgent', visibility_scope='public')
    db.add(agent); db.commit(); db.refresh(agent)
    mb = models.MemoryBlock(agent_id=agent.agent_id, conversation_id=uuid.uuid4(), content='x', visibility_scope='public')
    db.add(mb); db.commit(); db.refresh(mb)
    s = crud.create_consolidation_suggestion(db, schemas.ConsolidationSuggestionCreate(
        group_id=uuid.uuid4(),
        suggested_content='y',
        suggested_lessons_learned='z',
        suggested_keywords=['k'],
        original_memory_ids=[str(mb.id)],
        status='pending',
    ))
    # Directly update to rejected to simulate reject flow without hitting API
    u = crud.update_consolidation_suggestion(db, s.suggestion_id, schemas.ConsolidationSuggestionUpdate(status='rejected'))
    assert u.status == 'rejected'
    # apply should return None now
    assert crud.apply_consolidation(db, s.suggestion_id) is None


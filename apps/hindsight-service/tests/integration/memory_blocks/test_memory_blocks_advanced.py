import uuid
from datetime import datetime, timedelta, timezone
from core.db import models, crud, schemas


def _make_user_agent(db, scope="personal", org=None):
    user = models.User(email=f"mbadv_{uuid.uuid4().hex}@ex.com", display_name="MBA", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)
    agent = models.Agent(agent_name=f"MBAgent {uuid.uuid4().hex[:4]}", visibility_scope=scope, owner_user_id=user.id if scope=="personal" else None, organization_id=org.id if org else None)
    db.add(agent); db.commit(); db.refresh(agent)
    return user, agent


def test_memory_block_filters_and_archive(db_session):
    db = db_session
    # Personal
    user_p, agent_p = _make_user_agent(db)
    # Org
    org = models.Organization(name=f"MBAdvOrg_{uuid.uuid4().hex[:6]}", slug=f"mbadv-{uuid.uuid4().hex[:6]}", created_by=user_p.id)
    db.add(org); db.commit(); db.refresh(org)
    user_o, agent_o = _make_user_agent(db, scope="organization", org=org)

    # Create blocks
    mb1 = models.MemoryBlock(agent_id=agent_p.agent_id, conversation_id=uuid.uuid4(), content="Alpha content", lessons_learned="LL", visibility_scope="personal", owner_user_id=user_p.id)
    mb2 = models.MemoryBlock(agent_id=agent_o.agent_id, conversation_id=uuid.uuid4(), content="Beta content", lessons_learned="LL", visibility_scope="organization", organization_id=org.id)
    mb3 = models.MemoryBlock(agent_id=agent_p.agent_id, conversation_id=uuid.uuid4(), content="Gamma content", lessons_learned="LL", visibility_scope="public")
    db.add_all([mb1, mb2, mb3]); db.commit(); [db.refresh(x) for x in [mb1, mb2, mb3]]

    # Current user context (personal + org membership)
    ctx = {"id": user_p.id, "memberships": [{"organization_id": str(org.id)}]}
    # Filter by search term
    res = crud.get_all_memory_blocks(db, search_query="Alpha", current_user=ctx)
    assert len(res) == 1 and res[0].id == mb1.id

    # Archive one block and ensure filter respects archived flag
    crud.archive_memory_block(db, mb1.id)
    non_archived = crud.get_all_memory_blocks(db, current_user=ctx)
    assert all(not m.archived for m in non_archived)
    archived_only = crud.get_all_memory_blocks(db, current_user=ctx, is_archived=True)
    assert {m.id for m in archived_only} == {mb1.id}

    # Feedback scoring
    crud.report_memory_feedback(db, mb2.id, "positive")
    crud.report_memory_feedback(db, mb2.id, "negative")
    # Net 0 change
    updated = crud.get_memory_block(db, mb2.id)
    assert updated.feedback_score == 0

    # Keyword association via retrieval (create a block with keywords through create API for reliability)
    payload = schemas.MemoryBlockCreate(agent_id=agent_p.agent_id, conversation_id=uuid.uuid4(), content="Delta alpha beta", visibility_scope="personal", owner_user_id=user_p.id)
    mb_created = crud.create_memory_block(db, payload)
    kw_blocks = crud.get_keyword_memory_blocks(
        db,
        db.query(models.Keyword).first().keyword_id,
        current_user=ctx,
    )
    assert kw_blocks

    # Retrieval by keywords simple function
    retrieved = crud.retrieve_relevant_memories(db, ["alpha"], agent_id=agent_p.agent_id)
    assert any("alpha".lower() in (r.content.lower()) for r in retrieved)

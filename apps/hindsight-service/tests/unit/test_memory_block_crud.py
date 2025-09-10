import pytest
import uuid
from core.db.database import SessionLocal, engine
from core.db import models, schemas, crud


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


def _user(db, email: str):
    u = models.User(email=email, display_name=email.split('@')[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _agent(db, name: str, owner_id=None, scope="public", org_id=None):
    a = models.Agent(agent_name=name, visibility_scope=scope, owner_user_id=owner_id, organization_id=org_id)
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def test_memory_block_create_get_update_delete(db):
    user = _user(db, "mbuser@example.com")
    agent = _agent(db, "MemAgent", owner_id=user.id, scope="personal")
    mb_schema = schemas.MemoryBlockCreate(
        agent_id=agent.agent_id,
        conversation_id=uuid.uuid4(),
        content="This is a test memory about Python testing and coverage.",
        errors="",
        lessons_learned="Testing improves quality",
        metadata_col={"topic": "testing"},
        visibility_scope="personal",
        owner_user_id=user.id,
    )
    created = crud.create_memory_block(db, mb_schema)
    assert created.content.startswith("This is a test")

    fetched = crud.get_memory_block(db, created.id)
    assert fetched is not None

    crud.update_memory_block(db, created.id, schemas.MemoryBlockUpdate(feedback_score=5))
    assert crud.get_memory_block(db, created.id).feedback_score == 5

    # Archive then hard delete
    archived = crud.archive_memory_block(db, created.id)
    assert archived.archived is True
    assert crud.delete_memory_block(db, created.id) is True
    assert crud.get_memory_block(db, created.id) is None


def test_get_all_memory_blocks_scope_filters(db):
    # public memory
    public_agent = _agent(db, "PubAgent", scope="public")
    mb_public = crud.create_memory_block(db, schemas.MemoryBlockCreate(agent_id=public_agent.agent_id, conversation_id=uuid.uuid4(), content="Public content about AI", errors="", lessons_learned="", metadata_col={}, visibility_scope="public"))
    # personal
    user = _user(db, "owner2@example.com")
    personal_agent = _agent(db, "PersAgent", owner_id=user.id, scope="personal")
    mb_personal = crud.create_memory_block(db, schemas.MemoryBlockCreate(agent_id=personal_agent.agent_id, conversation_id=uuid.uuid4(), content="Personal note", errors="", lessons_learned="", metadata_col={}, visibility_scope="personal", owner_user_id=user.id))

    # organization
    org = models.Organization(name="MBOrg")
    db.add(org)
    db.commit()
    db.refresh(org)
    m = models.OrganizationMembership(user_id=user.id, organization_id=org.id, role="owner", can_read=True, can_write=True)
    db.add(m)
    db.commit()
    org_agent = _agent(db, "OrgMemAgent", scope="organization", org_id=org.id)
    mb_org = crud.create_memory_block(db, schemas.MemoryBlockCreate(agent_id=org_agent.agent_id, conversation_id=uuid.uuid4(), content="Org scoped", errors="", lessons_learned="", metadata_col={}, visibility_scope="organization", organization_id=org.id))

    # Unauth user sees only public
    unauth = crud.get_all_memory_blocks(db, current_user=None)
    assert {m.id for m in unauth} == {mb_public.id}

    current_user = {"id": user.id, "memberships": [{"organization_id": str(org.id)}]}
    visible = crud.get_all_memory_blocks(db, current_user=current_user)
    ids = {m.id for m in visible}
    assert {mb_public.id, mb_personal.id, mb_org.id}.issubset(ids)

    only_public = crud.get_all_memory_blocks(db, current_user=current_user, filter_scope="public")
    assert {m.id for m in only_public} == {mb_public.id}
    only_personal = crud.get_all_memory_blocks(db, current_user=current_user, filter_scope="personal")
    assert {m.id for m in only_personal} == {mb_personal.id}
    only_org = crud.get_all_memory_blocks(db, current_user=current_user, filter_scope="organization", filter_organization_id=org.id)
    assert {m.id for m in only_org} == {mb_org.id}

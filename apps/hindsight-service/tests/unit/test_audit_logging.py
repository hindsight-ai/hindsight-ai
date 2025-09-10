import uuid
from core.audit import log, AuditAction, AuditStatus, log_agent, log_keyword, log_memory, log_bulk_operation
from core.db.database import SessionLocal, engine
from core.db import models, schemas
import pytest

@pytest.fixture(scope="module")
def db():
    models.Base.metadata.create_all(bind=engine)
    try:
        yield SessionLocal()
    finally:
        models.Base.metadata.drop_all(bind=engine)

@pytest.fixture
def user(db):
    # Generate a unique email each test to avoid UNIQUE constraint collisions when
    # reusing the same module-scoped sqlite in-memory database.
    unique_email = f"tester_{uuid.uuid4().hex}@example.com"
    u = models.User(email=unique_email, display_name="tester")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

@pytest.fixture
def organization(db, user):
    unique_name = f"OrgA_{uuid.uuid4().hex[:8]}"
    org = models.Organization(name=unique_name, created_by=user.id)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

def test_log_basic(db, user, organization):
    entry = log(
        db,
        action=AuditAction.ORGANIZATION_CREATE,
        status=AuditStatus.SUCCESS,
        target_type="organization",
        target_id=organization.id,
        actor_user_id=user.id,
        organization_id=organization.id,
        metadata={"foo": "bar"},
    )
    assert entry.action_type == AuditAction.ORGANIZATION_CREATE.value
    assert entry.status == AuditStatus.SUCCESS.value
    assert entry.target_type == "organization"
    assert entry.target_id == organization.id
    assert entry.get_metadata().get("foo") == "bar"


def test_log_enums_vs_strings(db, user):
    # Using raw strings should also work
    entry = log(
        db,
        action="custom_action",
        status="custom_status",
        target_type="custom",
        target_id=None,
        actor_user_id=user.id,
        organization_id=None,
        metadata=None,
    )
    assert entry.action_type == "custom_action"
    assert entry.status == "custom_status"


def test_log_agent_wrapper(db, user, organization):
    agent_id = uuid.uuid4()
    entry = log_agent(
        db,
        actor_user_id=user.id,
        organization_id=organization.id,
        agent_id=agent_id,
        action=AuditAction.AGENT_CREATE,
        name="agent1",
    )
    assert entry.target_type == "agent"
    assert entry.target_id == agent_id
    assert entry.get_metadata()["name"] == "agent1"


def test_log_keyword_wrapper(db, user, organization):
    keyword_id = uuid.uuid4()
    entry = log_keyword(
        db,
        actor_user_id=user.id,
        organization_id=organization.id,
        keyword_id=keyword_id,
        action=AuditAction.KEYWORD_CREATE,
        text="kw1",
    )
    assert entry.target_type == "keyword"
    assert entry.target_id == keyword_id
    assert entry.get_metadata()["text"] == "kw1"


def test_log_memory_wrapper(db, user, organization):
    memory_id = uuid.uuid4()
    entry = log_memory(
        db,
        actor_user_id=user.id,
        organization_id=organization.id,
        memory_block_id=memory_id,
        action=AuditAction.MEMORY_CREATE,
        metadata={"size": 10},
    )
    assert entry.target_type == "memory_block"
    assert entry.target_id == memory_id
    assert entry.get_metadata()["size"] == 10


def test_log_bulk_operation_wrapper(db, user, organization):
    op_id = uuid.uuid4()
    entry = log_bulk_operation(
        db,
        actor_user_id=user.id,
        organization_id=organization.id,
        bulk_operation_id=op_id,
        action=AuditAction.BULK_OPERATION_START,
        metadata={"type": "bulk_move"},
    )
    assert entry.target_type == "bulk_operation"
    assert entry.target_id == op_id
    assert entry.get_metadata()["type"] == "bulk_move"

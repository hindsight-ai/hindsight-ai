import uuid
from datetime import datetime, timezone

from core.db.database import get_db_session_local
from core.db import models, schemas
from core.db.repositories import bulk_ops as repo_bulk
from core.db.repositories import audits as repo_audits


def _db():
    gen = get_db_session_local()
    db = next(gen)
    return db, gen


def test_bulk_operations_repository_smoke():
    db, gen = _db()
    try:
        # Create actor user
        user = models.User(email=f"actor_{uuid.uuid4().hex}@example.com")
        db.add(user)
        db.commit(); db.refresh(user)

        # Create bulk operation
        bo_schema = schemas.BulkOperationCreate(type="bulk_move", request_payload={"hello": "world"})
        bo = repo_bulk.create_bulk_operation(db, bo_schema, actor_user_id=user.id, organization_id=None)
        assert bo.type == "bulk_move"
        assert bo.actor_user_id == user.id
        assert bo.status == "pending"
        assert bo.progress == 0

        # Get by id
        fetched = repo_bulk.get_bulk_operation(db, bo.id)
        assert fetched is not None and fetched.id == bo.id

        # List
        lst = repo_bulk.get_bulk_operations(db, organization_id=None, user_id=user.id)
        assert any(x.id == bo.id for x in lst)

        # Update
        upd = schemas.BulkOperationUpdate(status="running", progress=50)
        bo2 = repo_bulk.update_bulk_operation(db, bo.id, upd)
        assert bo2.status == "running" and bo2.progress == 50
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


def test_audit_repository_smoke_filters():
    db, gen = _db()
    try:
        # Create actor user and org
        user = models.User(email=f"auditor_{uuid.uuid4().hex}@example.com")
        db.add(user); db.commit(); db.refresh(user)
        org = models.Organization(name=f"Org_{uuid.uuid4().hex[:6]}")
        db.add(org); db.commit(); db.refresh(org)

        # Create audit log via repository
        al_schema = schemas.AuditLogCreate(
            action_type="unit_test_event",
            status="success",
            target_type="unit",
            target_id=None,
            reason=None,
            metadata={"k": "v"},
        )
        al = repo_audits.create_audit_log(db, al_schema, actor_user_id=user.id, organization_id=org.id)
        assert al.action_type == "unit_test_event"
        assert al.actor_user_id == user.id
        assert al.organization_id == org.id

        # Filtered list
        rows = repo_audits.get_audit_logs(db, organization_id=org.id, user_id=user.id, action_type="unit_test_event", status="success")
        assert len(rows) >= 1
        assert rows[0].action_type == "unit_test_event"
    finally:
        try:
            next(gen)
        except StopIteration:
            pass


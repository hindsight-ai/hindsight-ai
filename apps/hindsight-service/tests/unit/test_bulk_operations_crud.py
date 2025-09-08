import uuid
from datetime import datetime, timezone

from core.db import models, crud, schemas


def test_create_and_update_bulk_operation(db_session):
    db = db_session
    user = models.User(email=f"bulk_{uuid.uuid4().hex}@example.com", display_name="BulkUser", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)

    # Randomize org name/slug to avoid uniqueness collisions across test runs
    suffix = uuid.uuid4().hex[:6]
    org = models.Organization(name=f"Bulk Org {suffix}", slug=f"bulk-org-{suffix}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)

    payload = schemas.BulkOperationCreate(type="move", request_payload={"example": True})
    op = crud.create_bulk_operation(db, payload, actor_user_id=user.id, organization_id=org.id)
    assert op.status == "pending"

    # Update progression
    from core.db import schemas as s
    upd = s.BulkOperationUpdate(status="running", progress=10, total=100)
    updated = crud.update_bulk_operation(db, op.id, upd)
    assert updated.status == "running"
    assert updated.progress == 10
    assert updated.total == 100

    # Listing by filters
    all_ops = crud.get_bulk_operations(db, organization_id=org.id)
    assert len(all_ops) == 1
    assert all_ops[0].id == op.id

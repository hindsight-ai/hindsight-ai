import uuid
from core.db import models, crud, schemas


def test_bulk_operation_progress_and_filters(db_session):
    db = db_session
    user = models.User(email=f"bof_{uuid.uuid4().hex}@ex.com", display_name="BOF", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)
    org = models.Organization(name=f"BOFOrg_{uuid.uuid4().hex[:6]}", slug=f"boforg-{uuid.uuid4().hex[:6]}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)

    # Create two operations different statuses
    op1 = crud.create_bulk_operation(db, schemas.BulkOperationCreate(type="move", request_payload={"a":1}), actor_user_id=user.id, organization_id=org.id)
    op2 = crud.create_bulk_operation(db, schemas.BulkOperationCreate(type="delete", request_payload={"b":2}), actor_user_id=user.id, organization_id=org.id)

    # Progress op1
    upd = schemas.BulkOperationUpdate(status="running", progress=5, total=10)
    crud.update_bulk_operation(db, op1.id, upd)
    upd2 = schemas.BulkOperationUpdate(status="completed", progress=10, total=10)
    crud.update_bulk_operation(db, op1.id, upd2)

    # Filter by organization and status
    all_ops = crud.get_bulk_operations(db, organization_id=org.id)
    assert {o.id for o in all_ops} == {op1.id, op2.id}
    completed = [o for o in all_ops if o.status == "completed"]
    assert len(completed) == 1 and completed[0].id == op1.id

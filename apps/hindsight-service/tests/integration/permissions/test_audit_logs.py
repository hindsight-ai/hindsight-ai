import uuid
from datetime import datetime, timezone

from core.db import models, crud, schemas


def test_create_and_filter_audit_logs(db_session):
    db = db_session
    user1 = models.User(email=f"actor1_{uuid.uuid4().hex}@example.com", display_name="Actor1", is_superadmin=False)
    user2 = models.User(email=f"actor2_{uuid.uuid4().hex}@example.com", display_name="Actor2", is_superadmin=False)
    db.add_all([user1, user2])
    db.commit()
    db.refresh(user1); db.refresh(user2)

    # Randomize org name/slug to avoid uniqueness collisions across test runs
    suffix = uuid.uuid4().hex[:6]
    org = models.Organization(name=f"Audited Org {suffix}", slug=f"audited-org-{suffix}", created_by=user1.id)
    db.add(org); db.commit(); db.refresh(org)

    # Create several audit entries
    for i in range(3):
        payload = schemas.AuditLogCreate(action_type="test_event", status="success", target_type="thing", target_id=None, metadata={"seq": i})
        crud.create_audit_log(db, payload, actor_user_id=user1.id, organization_id=org.id)

    payload2 = schemas.AuditLogCreate(action_type="other_event", status="failure", target_type="item", target_id=None, metadata=None)
    crud.create_audit_log(db, payload2, actor_user_id=user2.id, organization_id=None)

    # Filter by org
    org_logs = crud.get_audit_logs(db, organization_id=org.id)
    assert len(org_logs) == 3
    assert all(l.organization_id == org.id for l in org_logs)

    # Filter by user
    user2_logs = crud.get_audit_logs(db, user_id=user2.id)
    assert len(user2_logs) == 1
    assert user2_logs[0].actor_user_id == user2.id

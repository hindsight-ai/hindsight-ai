import uuid
from core.db import models, crud, schemas


def test_audit_log_compound_filters(db_session):
    db = db_session
    user = models.User(email=f"alog_{uuid.uuid4().hex}@ex.com", display_name="AL", is_superadmin=False)
    other = models.User(email=f"alog2_{uuid.uuid4().hex}@ex.com", display_name="AL2", is_superadmin=False)
    db.add_all([user, other]); db.commit(); db.refresh(user); db.refresh(other)

    org = models.Organization(name=f"ALOrg_{uuid.uuid4().hex[:6]}", slug=f"alorg-{uuid.uuid4().hex[:6]}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)

    # Create diverse logs
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="member_add", status="success", target_type="user", target_id=None), actor_user_id=user.id, organization_id=org.id)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="member_add", status="failure", target_type="user", target_id=None), actor_user_id=other.id, organization_id=org.id)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="invitation_create", status="success", target_type="invitation", target_id=None), actor_user_id=user.id, organization_id=org.id)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="member_add", status="success", target_type="user", target_id=None), actor_user_id=user.id, organization_id=None)

    # Filter by org + user + action_type
    logs = crud.get_audit_logs(db, organization_id=org.id, user_id=user.id, action_type="member_add")
    assert len(logs) == 1
    assert logs[0].actor_user_id == user.id and logs[0].organization_id == org.id and logs[0].action_type == "member_add"

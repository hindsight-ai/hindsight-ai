import uuid
from fastapi.testclient import TestClient
from unittest.mock import Mock
from core.api.main import app
from core.api.deps import get_current_user_context
from core.db import models, crud
from tests.conftest import _current_session

client = TestClient(app)

def auth():
    return {"x-auth-request-email": "auditor@example.com", "x-auth-request-user": "Auditor"}

def test_bulk_move_audit_start():
    # Prepare org & user using shared session
    db = _current_session.get()
    user = models.User(email="auditor@example.com", display_name="Auditor")
    db.add(user); db.commit(); db.refresh(user)
    org = models.Organization(name="AuditOrg", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)
    mem = models.OrganizationMembership(organization_id=org.id, user_id=user.id, role="owner", can_read=True, can_write=True)
    db.add(mem); db.commit()
    ag = models.Agent(agent_name="A1", visibility_scope="organization", organization_id=org.id)
    db.add(ag); db.commit(); db.refresh(ag)
    org_id = org.id
    user_id = user.id
    # Trigger dry_run False move to start operation
    dest_owner = uuid.uuid4()
    payload = {"dry_run": False, "destination_owner_user_id": str(dest_owner), "resource_types": ["agents"]}
    # Use dependency override to simplify: treat user as owner of org
    fake_user = Mock(); fake_user.id = user_id
    fake_user_context = {"id": user_id, "is_superadmin": True, "memberships_by_org": {str(org_id): {"role": "owner"}}}
    
    def mock_get_current_user_context(
        db=None,
        x_auth_request_user=None,
        x_auth_request_email=None,
        x_forwarded_user=None,
        x_forwarded_email=None,
    ):
        return fake_user, fake_user_context
    
    original_override = app.dependency_overrides.get(get_current_user_context)
    app.dependency_overrides[get_current_user_context] = mock_get_current_user_context
    
    try:
        r = client.post(f"/bulk-operations/organizations/{org_id}/bulk-move", json=payload, headers=auth())
        assert r.status_code == 200, r.text
    finally:
        # Clean up dependency override
        if original_override is not None:
            app.dependency_overrides[get_current_user_context] = original_override
        else:
            app.dependency_overrides.pop(get_current_user_context, None)
    op_id = r.json()["operation_id"]
    # Verify audit start log exists
    logs = crud.get_audit_logs(db, organization_id=org_id)
    assert any(l.action_type == "bulk_operation_start" and str(l.target_id) == op_id for l in logs)

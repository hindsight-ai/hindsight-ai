import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock
from core.api.main import app
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
    # Patch auth/permission to simplify: treat user as owner of org
    with patch('core.api.bulk_operations._require_current_user') as mock_req:
        fake_user = Mock(); fake_user.id = user_id
        fake_user_context = {"id": user_id, "is_superadmin": True, "memberships_by_org": {str(org_id): {"role": "owner"}}}
        mock_req.return_value = (fake_user, fake_user_context)
        r = client.post(f"/bulk-operations/organizations/{org_id}/bulk-move", json=payload, headers=auth())
    assert r.status_code == 200, r.text
    op_id = r.json()["operation_id"]
    # Verify audit start log exists
    logs = crud.get_audit_logs(db, organization_id=org_id)
    assert any(l.action_type == "bulk_operation_start" and str(l.target_id) == op_id for l in logs)

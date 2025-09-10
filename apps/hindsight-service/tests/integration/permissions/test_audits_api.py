import os
import sys
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from core.db import models, crud, schemas
from core.api.main import app as main_app


def test_audits_endpoint_requires_org_for_non_superadmin(db_session: Session):
    client = TestClient(main_app)
    # Create a normal user by hitting an endpoint that creates users implicitly (organizations create)
    headers = {"x-auth-request-user": "norm", "x-auth-request-email": "norm@example.com"}
    # Attempt to list audits without org -> should 403
    r = client.get("/audits/", headers=headers)
    assert r.status_code == 403


def test_audits_endpoint_superadmin_can_list_all(db_session: Session, monkeypatch):
    # Mark an admin email so created user becomes superadmin via ADMIN_EMAILS logic
    os.environ["ADMIN_EMAILS"] = "root@example.com"
    client = TestClient(main_app)
    headers_admin = {"x-auth-request-user": "root", "x-auth-request-email": "root@example.com"}
    # First request creates the superadmin user implicitly
    r = client.get("/audits/", headers=headers_admin)
    assert r.status_code == 200  # empty list ok

    # Seed some audit logs directly
    db: Session = db_session
    user = db.query(models.User).filter_by(email="root@example.com").first()
    org = models.Organization(name="OrgAud", slug=f"orgaud-{uuid.uuid4().hex[:6]}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="org_create", status="success", target_type="organization", target_id=org.id), actor_user_id=user.id, organization_id=org.id)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="member_add", status="failure", target_type="user", target_id=None), actor_user_id=user.id, organization_id=org.id)
    crud.create_audit_log(db, schemas.AuditLogCreate(action_type="member_add", status="success", target_type="user", target_id=None), actor_user_id=user.id, organization_id=None)

    # Superadmin list all
    r = client.get("/audits/", headers=headers_admin)
    assert r.status_code == 200
    all_logs = r.json()
    assert len(all_logs) >= 3

    # Filter by organization_id
    r = client.get(f"/audits/?organization_id={org.id}", headers=headers_admin)
    assert r.status_code == 200
    org_logs = r.json()
    assert all(l["organization_id"] == str(org.id) for l in org_logs)
    assert any(l["action_type"] == "org_create" for l in org_logs)

    # Filter by user_id (actor)
    r = client.get(f"/audits/?user_id={user.id}", headers=headers_admin)
    assert r.status_code == 200
    user_logs = r.json()
    assert len(user_logs) >= 3

    # Combined filter org + user narrows subset
    r = client.get(f"/audits/?organization_id={org.id}&user_id={user.id}", headers=headers_admin)
    assert r.status_code == 200
    combined = r.json()
    assert len(combined) <= len(user_logs)
    assert all(l["organization_id"] == str(org.id) for l in combined)
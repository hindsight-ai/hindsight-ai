import uuid
from datetime import datetime, timezone

from core.db import models, crud, schemas

# Session provided via db_session fixture (see conftest)


def test_create_and_list_invitations(db_session):
    db = db_session
    # Create org + user
    user = models.User(email=f"owner_{uuid.uuid4().hex}@example.com", display_name="Owner", is_superadmin=False)
    db.add(user)
    db.commit(); db.refresh(user)

    org = models.Organization(name=f"OrgOne_{uuid.uuid4().hex}", slug=f"org-one-{uuid.uuid4().hex[:8]}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)

    invite_email = f"invitee_{uuid.uuid4().hex}@example.com"
    inv_schema = schemas.OrganizationInvitationCreate(email=invite_email, role="viewer")
    invitation = crud.create_organization_invitation(db, org.id, inv_schema, invited_by_user_id=user.id)
    assert invitation.email == invite_email
    assert invitation.role == "viewer"
    assert invitation.status == "pending"
    assert invitation.expires_at > datetime.now(timezone.utc)

    invitations = crud.get_organization_invitations(db, org.id)
    assert len(invitations) == 1
    assert invitations[0].id == invitation.id


def test_update_and_delete_invitation(db_session):
    db = db_session
    user = models.User(email=f"owner2_{uuid.uuid4().hex}@example.com", display_name="Owner2", is_superadmin=False)
    db.add(user); db.commit(); db.refresh(user)

    org = models.Organization(name=f"OrgTwo_{uuid.uuid4().hex}", slug=f"org-two-{uuid.uuid4().hex[:8]}", created_by=user.id)
    db.add(org); db.commit(); db.refresh(org)

    inv_schema = schemas.OrganizationInvitationCreate(email=f"person_{uuid.uuid4().hex}@example.com", role="editor")
    invitation = crud.create_organization_invitation(db, org.id, inv_schema, invited_by_user_id=user.id)

    upd = schemas.OrganizationInvitationUpdate(status="revoked", role="viewer")
    updated = crud.update_organization_invitation(db, invitation.id, upd)
    assert updated.status == "revoked"
    assert updated.role == "viewer"

    deleted = crud.delete_organization_invitation(db, invitation.id)
    assert deleted is True
    # Second delete should be False
    assert crud.delete_organization_invitation(db, invitation.id) is False

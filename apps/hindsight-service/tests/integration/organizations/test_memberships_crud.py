import uuid
from core.db import models, crud, schemas


def _seed_org_and_users(db):
    owner = models.User(email=f"owner_{uuid.uuid4().hex}@ex.com", display_name="Owner", is_superadmin=False)
    member = models.User(email=f"member_{uuid.uuid4().hex}@ex.com", display_name="Member", is_superadmin=False)
    db.add_all([owner, member]); db.commit(); db.refresh(owner); db.refresh(member)
    org = models.Organization(name=f"OrgM_{uuid.uuid4().hex[:6]}", slug=f"orgm-{uuid.uuid4().hex[:6]}", created_by=owner.id)
    db.add(org); db.commit(); db.refresh(org)
    m_rec = models.OrganizationMembership(organization_id=org.id, user_id=owner.id, role="owner", can_read=True, can_write=True)
    db.add(m_rec); db.commit()
    return org, owner, member


def test_update_and_delete_membership(db_session):
    db = db_session
    org, owner, member = _seed_org_and_users(db)
    # Add second membership
    m2 = models.OrganizationMembership(organization_id=org.id, user_id=member.id, role="viewer", can_read=True, can_write=False)
    db.add(m2); db.commit()

    # Update membership
    upd = schemas.OrganizationMemberUpdate(role="editor", can_write=True)
    updated = crud.update_organization_member(db, org.id, member.id, upd)
    assert updated.role == "editor"
    assert updated.can_write is True

    # Delete membership
    assert crud.delete_organization_member(db, org.id, member.id) is True
    # Second delete returns False
    assert crud.delete_organization_member(db, org.id, member.id) is False

    # Update non-existent membership returns None
    assert crud.update_organization_member(db, org.id, member.id, upd) is None

import uuid
from core.db import crud


def test_invitation_update_delete_not_found(db_session):
    db = db_session
    fake_id = uuid.uuid4()
    # Update non-existent
    from core.db import schemas
    upd = schemas.OrganizationInvitationUpdate(status="revoked")
    updated = crud.update_organization_invitation(db, fake_id, upd)
    assert updated is None
    # Delete non-existent
    deleted = crud.delete_organization_invitation(db, fake_id)
    assert deleted is False

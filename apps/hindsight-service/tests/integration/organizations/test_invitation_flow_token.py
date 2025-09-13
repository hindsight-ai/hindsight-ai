import uuid
from datetime import datetime, UTC, timedelta

from core.db import models


def test_accept_invitation_via_token(db_session, client):
    # Seed inviter
    inviter = models.User(email="inviter@example.com", display_name="Inviter")
    db_session.add(inviter); db_session.commit(); db_session.refresh(inviter)

    # Seed org
    org = models.Organization(name="TokenOrg", slug="token-org", created_by=inviter.id)
    db_session.add(org); db_session.commit(); db_session.refresh(org)

    # Create invitation directly (pending)
    inv = models.OrganizationInvitation(
        organization_id=org.id,
        email="invitee@example.com",
        invited_by_user_id=inviter.id,
        role="viewer",
        status="pending",
        token=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(inv); db_session.commit(); db_session.refresh(inv)

    # Call accept endpoint with token and mismatched authenticated email; token should override
    headers = {"x-auth-request-email": "someoneelse@example.com"}
    resp = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp.status_code == 200

    # Invitation should be marked accepted and membership created for invitee@example.com
    inv_db = db_session.query(models.OrganizationInvitation).get(inv.id)
    assert inv_db.status == 'accepted'
    mems = db_session.query(models.OrganizationMembership).filter_by(organization_id=org.id).all()
    # There should be at least one member with the invitee's email
    invitee_user = db_session.query(models.User).filter_by(email="invitee@example.com").first()
    assert invitee_user is not None
    assert any(m.user_id == invitee_user.id for m in mems)


def test_decline_invitation_via_token(db_session, client):
    # Seed inviter
    inviter = models.User(email="inv2@example.com", display_name="Inviter2")
    db_session.add(inviter); db_session.commit(); db_session.refresh(inviter)

    # Seed org
    org = models.Organization(name="DeclineOrg", slug="decline-org", created_by=inviter.id)
    db_session.add(org); db_session.commit(); db_session.refresh(org)

    inv = models.OrganizationInvitation(
        organization_id=org.id,
        email="invitee2@example.com",
        invited_by_user_id=inviter.id,
        role="viewer",
        status="pending",
        token=uuid.uuid4().hex,
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db_session.add(inv); db_session.commit(); db_session.refresh(inv)

    headers = {"x-auth-request-email": "anyone@example.com"}
    resp = client.post(f"/organizations/{org.id}/invitations/{inv.id}/decline?token={inv.token}", headers=headers)
    assert resp.status_code == 200
    inv_db = db_session.query(models.OrganizationInvitation).get(inv.id)
    assert inv_db.status == 'revoked'

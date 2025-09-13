import uuid
from datetime import datetime, UTC, timedelta

from core.db import models


def _seed_org_and_user(db):
    inviter = models.User(email=f"owner-{uuid.uuid4().hex[:8]}@example.com", display_name="Owner")
    db.add(inviter); db.commit(); db.refresh(inviter)
    org = models.Organization(name=f"Org-{uuid.uuid4().hex[:6]}", slug=None, created_by=inviter.id)
    db.add(org); db.commit(); db.refresh(org)
    # Make inviter owner
    db.add(models.OrganizationMembership(organization_id=org.id, user_id=inviter.id, role='owner'))
    db.commit()
    return inviter, org


def test_cannot_invite_existing_member(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    # Create a member user
    member = models.User(email="member@example.com", display_name="Member")
    db_session.add(member); db_session.commit(); db_session.refresh(member)
    db_session.add(models.OrganizationMembership(organization_id=org.id, user_id=member.id, role='viewer'))
    db_session.commit()

    headers = {"x-auth-request-email": inviter.email}
    payload = {"email": member.email, "role": "viewer"}
    resp = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    assert resp.status_code == 409


def test_duplicate_pending_invitation_returns_409(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    payload = {"email": "dup@example.com", "role": "viewer"}
    r1 = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    assert r1.status_code == 201
    r2 = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    assert r2.status_code == 409


def test_accept_invitation_twice_second_400(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    payload = {"email": "twice@example.com", "role": "viewer"}
    r = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    assert r.status_code == 201
    inv = db_session.query(models.OrganizationInvitation).filter_by(organization_id=org.id, email=payload['email']).first()
    # Accept via token
    resp1 = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp1.status_code == 200
    # Second accept
    resp2 = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp2.status_code == 400


def test_accept_after_revoked_returns_400(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    payload = {"email": "revoke@example.com", "role": "viewer"}
    r = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    inv = db_session.query(models.OrganizationInvitation).filter_by(organization_id=org.id, email=payload['email']).first()
    # Revoke
    client.delete(f"/organizations/{org.id}/invitations/{inv.id}", headers=headers)
    # Accept attempt
    resp = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp.status_code == 400


def test_decline_after_accepted_returns_400(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    payload = {"email": "acceptfirst@example.com", "role": "viewer"}
    r = client.post(f"/organizations/{org.id}/invitations", json=payload, headers=headers)
    inv = db_session.query(models.OrganizationInvitation).filter_by(organization_id=org.id, email=payload['email']).first()
    # Accept via token
    resp1 = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp1.status_code == 200
    # Now decline attempt should fail with 400
    resp2 = client.post(f"/organizations/{org.id}/invitations/{inv.id}/decline?token={inv.token}", headers=headers)
    assert resp2.status_code == 400


def test_accept_expired_invitation_returns_400(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    inv = models.OrganizationInvitation(
        organization_id=org.id,
        email="expired@example.com",
        invited_by_user_id=inviter.id,
        role="viewer",
        status="pending",
        token=uuid.uuid4().hex,
        created_at=datetime.now(UTC) - timedelta(days=10),
        expires_at=datetime.now(UTC) - timedelta(days=3),
    )
    db_session.add(inv); db_session.commit(); db_session.refresh(inv)
    headers = {"x-auth-request-email": inviter.email}
    resp = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token={inv.token}", headers=headers)
    assert resp.status_code == 400


def test_list_invitations_pending_only_default(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    # Create pending and accepted invites
    p1 = models.OrganizationInvitation(organization_id=org.id, email="p1@example.com", invited_by_user_id=inviter.id, role="viewer", status="pending", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    a1 = models.OrganizationInvitation(organization_id=org.id, email="a1@example.com", invited_by_user_id=inviter.id, role="viewer", status="accepted", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    db_session.add_all([p1, a1]); db_session.commit()
    resp = client.get(f"/organizations/{org.id}/invitations", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert all(item['status'] == 'pending' for item in data)


def test_list_invitations_all_returns_all_statuses(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": inviter.email}
    # Create invites with different statuses
    p1 = models.OrganizationInvitation(organization_id=org.id, email="p2@example.com", invited_by_user_id=inviter.id, role="viewer", status="pending", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    a1 = models.OrganizationInvitation(organization_id=org.id, email="a2@example.com", invited_by_user_id=inviter.id, role="viewer", status="accepted", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    r1 = models.OrganizationInvitation(organization_id=org.id, email="r2@example.com", invited_by_user_id=inviter.id, role="viewer", status="revoked", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    db_session.add_all([p1, a1, r1]); db_session.commit()
    resp = client.get(f"/organizations/{org.id}/invitations?status=all", headers=headers)
    assert resp.status_code == 200
    statuses = {item['status'] for item in resp.json()}
    assert 'pending' in statuses and 'accepted' in statuses and 'revoked' in statuses


def test_wrong_token_and_email_mismatch_returns_403(db_session, client):
    inviter, org = _seed_org_and_user(db_session)
    headers = {"x-auth-request-email": "different@example.com"}
    inv = models.OrganizationInvitation(organization_id=org.id, email="invitee3@example.com", invited_by_user_id=inviter.id, role="viewer", status="pending", token=uuid.uuid4().hex, created_at=datetime.now(UTC), expires_at=datetime.now(UTC)+timedelta(days=7))
    db_session.add(inv); db_session.commit(); db_session.refresh(inv)
    resp = client.post(f"/organizations/{org.id}/invitations/{inv.id}/accept?token=wrongtok", headers=headers)
    assert resp.status_code == 403

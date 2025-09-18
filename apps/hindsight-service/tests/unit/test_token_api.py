import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.api.main import app
from core.db import models


def test_token_management_crud_flow(client: TestClient, db_session: Session):
    headers = {"x-auth-request-email": "tok@example.com", "x-auth-request-user": "Tok"}

    # Create a token
    payload = {
        "name": "CLI Token",
        "scopes": ["read", "write"],
    }
    r = client.post("/users/me/tokens", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    token_resp = r.json()
    assert token_resp["token"].startswith("hs_pat_")
    # Normalize token UUID string
    token_id = str(uuid.UUID(str(token_resp["id"])))

    # List tokens
    r = client.get("/users/me/tokens", headers=headers)
    assert r.status_code == 200
    toks = r.json()
    assert any(t["id"] == token_id for t in toks)

    # Rotate token
    r = client.post(f"/users/me/tokens/{token_id}/rotate", headers=headers)
    assert r.status_code == 200
    rotated = r.json()
    assert rotated["token"].startswith("hs_pat_")

    # Update token
    new_name = "Updated Token"
    exp = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r = client.patch(f"/users/me/tokens/{token_id}", json={"name": new_name, "expires_at": exp}, headers=headers)
    assert r.status_code == 200
    updated = r.json()
    assert updated["name"] == new_name

    # Revoke token
    r = client.delete(f"/users/me/tokens/{token_id}", headers=headers)
    # Endpoint uses 204; content may be empty
    assert r.status_code == 204


def test_agents_list_with_pat_allows_personal_read(client: TestClient, db_session: Session):
    # Create a user and a personal agent for them
    user = models.User(email="reader2@example.com", display_name="Reader2")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    agent = models.Agent(agent_name="PAgent", visibility_scope="personal", owner_user_id=user.id)
    db_session.add(agent)
    db_session.commit()

    # Create PAT via API for this user by simulating OAuth headers
    headers = {"x-auth-request-email": user.email, "x-auth-request-user": user.display_name}
    r = client.post("/users/me/tokens", json={"name": "t", "scopes": ["read"]}, headers=headers)
    assert r.status_code == 201
    token = r.json()["token"]

    # Use PAT to list agents; should include personal agent
    r = client.get("/agents/?limit=50", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    agents = r.json()
    assert any(a["agent_name"] == "PAgent" for a in agents)

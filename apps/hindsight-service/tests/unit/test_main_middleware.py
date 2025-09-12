from fastapi.testclient import TestClient
from core.api.main import app


def test_guest_post_rejected_by_readonly_middleware():
    client = TestClient(app)
    # Attempt to create agent without auth headers
    r = client.post("/agents/", json={"agent_name": "X"})
    assert r.status_code == 401
    assert "Guest mode is read-only" in r.text


def test_post_allowed_with_auth_headers():
    client = TestClient(app)
    headers = {"x-auth-request-email": "poster@example.com", "x-auth-request-user": "Poster"}
    r = client.post("/agents/", json={"agent_name": "PosterAgent", "visibility_scope": "personal"}, headers=headers)
    # It may pass or validate elsewhere, but should not be blocked by middleware
    assert r.status_code in (200, 201, 422)


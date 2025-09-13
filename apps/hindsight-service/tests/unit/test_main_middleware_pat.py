from fastapi.testclient import TestClient
from core.api.main import app


def test_post_not_blocked_by_middleware_when_pat_header_present():
    client = TestClient(app)
    # Invalid PAT should pass middleware and be rejected by dependency (401), not guest read-only message
    r = client.post(
        "/agents/",
        json={"agent_name": "X", "visibility_scope": "personal"},
        headers={"Authorization": "Bearer hs_pat_invalid"},
    )
    assert r.status_code == 401
    assert "Guest mode is read-only" not in (r.text or "")


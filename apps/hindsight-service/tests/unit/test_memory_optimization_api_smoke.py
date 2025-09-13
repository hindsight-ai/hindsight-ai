import uuid
from fastapi.testclient import TestClient
from core.api.main import app


client = TestClient(app)


def test_memory_optimization_suggestions_and_execute_noop():
    # Should return a suggestions payload even with empty DB
    r = client.get("/memory-optimization/suggestions")
    assert r.status_code == 200
    body = r.json()
    assert "suggestions" in body and isinstance(body["suggestions"], list)

    # Executing a non-existent suggestion id should return a graceful error status
    sid = str(uuid.uuid4())
    r2 = client.post(
        f"/memory-optimization/suggestions/{sid}/execute",
        headers={"x-auth-request-user": "tester", "x-auth-request-email": "tester@example.com"},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2.get("suggestion_id") == sid
    assert body2.get("status") in ("error", "completed")

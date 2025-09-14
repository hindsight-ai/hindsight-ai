from fastapi.testclient import TestClient
from core.api.main import app


def test_support_build_info():
    client = TestClient(app)
    r = client.get("/build-info")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service_name") == "hindsight-service"
    assert "version" in data


import uuid
from fastapi.testclient import TestClient
from core.api.main import app as main_app


def _headers(user: str):
    return {"x-auth-request-user": user, "x-auth-request-email": f"{user}@example.com"}


def test_create_org_duplicate_slug_and_name():
    client = TestClient(main_app)
    h = _headers("orguser")
    r = client.post("/organizations/", json={"name": "DupOrg", "slug": "dupslug"}, headers=h)
    assert r.status_code == 201
    # Duplicate name
    r2 = client.post("/organizations/", json={"name": "DupOrg", "slug": "dupslug2"}, headers=h)
    assert r2.status_code == 409
    # Duplicate slug
    r3 = client.post("/organizations/", json={"name": "DupOrg2", "slug": "dupslug"}, headers=h)
    assert r3.status_code == 409

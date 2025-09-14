import uuid
import pytest
from fastapi.testclient import TestClient

from core.api.main import app


def _h(email):
    return {"x-auth-request-user": email.split("@")[0], "x-auth-request-email": email}


@pytest.mark.usefixtures("db_session")
def test_keywords_crud_organization_scope(db_session):
    client = TestClient(app)

    owner_email = f"kw_{uuid.uuid4().hex[:8]}@example.com"
    # Create org
    r_org = client.post("/organizations/", json={"name": f"KwOrg_{uuid.uuid4().hex[:6]}"}, headers=_h(owner_email))
    assert r_org.status_code == 201, r_org.text
    org_id = r_org.json()["id"]

    # Create keyword in organization scope
    payload = {
        "keyword_text": "alpha-key",
        "visibility_scope": "organization",
        "organization_id": org_id,
    }
    r_create = client.post("/keywords/", json=payload, headers=_h(owner_email))
    assert r_create.status_code == 201, r_create.text
    kw = r_create.json()
    kw_id = kw["keyword_id"]

    # List keywords
    r_list = client.get(f"/keywords/?scope=organization&organization_id={org_id}", headers=_h(owner_email))
    assert r_list.status_code == 200
    assert any(k.get("keyword_id") == kw_id for k in r_list.json())

    # Get keyword by id
    r_get = client.get(f"/keywords/{kw_id}", headers=_h(owner_email))
    assert r_get.status_code == 200
    assert r_get.json()["keyword_text"] == "alpha-key"

    # Update keyword
    r_update = client.put(
        f"/keywords/{kw_id}",
        json={"keyword_text": "beta-key"},
        headers=_h(owner_email),
    )
    assert r_update.status_code == 200
    assert r_update.json()["keyword_text"] == "beta-key"

    # Count associated memory blocks (should be 0)
    r_cnt = client.get(f"/keywords/{kw_id}/memory-blocks/count", headers=_h(owner_email))
    assert r_cnt.status_code == 200
    assert r_cnt.json().get("count") in (0, None)

    # Delete keyword
    r_del = client.delete(f"/keywords/{kw_id}", headers=_h(owner_email))
    assert r_del.status_code in (200, 204)

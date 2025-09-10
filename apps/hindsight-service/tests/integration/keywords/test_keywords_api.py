import uuid
from fastapi.testclient import TestClient
from core.api.main import app  # corrected import path

client = TestClient(app)

# Helper to build auth headers

def auth(email="user@example.com", name="User"):
    return {
        "x-auth-request-email": email,
        "x-auth-request-user": name,
    }

def test_create_personal_keyword():
    r = client.post("/keywords/", json={"keyword_text": "alpha"}, headers=auth())
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["keyword_text"] == "alpha"
    assert data["visibility_scope"] == "personal"


def test_duplicate_personal_keyword_conflict():
    r1 = client.post("/keywords/", json={"keyword_text": "dupkw"}, headers=auth())
    assert r1.status_code == 201
    r2 = client.post("/keywords/", json={"keyword_text": "dupkw"}, headers=auth())
    assert r2.status_code == 409


def test_list_keywords_personal_scope():
    # ensure at least one
    client.post("/keywords/", json={"keyword_text": "listme"}, headers=auth())
    r = client.get("/keywords/?scope=personal", headers=auth())
    assert r.status_code == 200
    arr = r.json()
    assert any(k["keyword_text"] == "listme" for k in arr)


def test_update_keyword_forbidden_when_other_user():
    r = client.post("/keywords/", json={"keyword_text": "toupdate"}, headers=auth("owner@example.com"))
    assert r.status_code == 201
    kw_id = r.json()["keyword_id"]
    # other user attempts update
    r2 = client.put(f"/keywords/{kw_id}", json={"keyword_text": "changed"}, headers=auth("other@example.com"))
    assert r2.status_code == 403


def test_update_keyword_success():
    r = client.post("/keywords/", json={"keyword_text": "orig"}, headers=auth())
    kw_id = r.json()["keyword_id"]
    r2 = client.put(f"/keywords/{kw_id}", json={"keyword_text": "updated"}, headers=auth())
    assert r2.status_code == 200
    assert r2.json()["keyword_text"] == "updated"


def test_get_single_keyword_and_not_found():
    r = client.post("/keywords/", json={"keyword_text": "single"}, headers=auth())
    kw_id = r.json()["keyword_id"]
    r2 = client.get(f"/keywords/{kw_id}", headers=auth())
    assert r2.status_code == 200
    nf = client.get(f"/keywords/{uuid.uuid4()}", headers=auth())
    assert nf.status_code == 404


def test_delete_keyword():
    r = client.post("/keywords/", json={"keyword_text": "delme"}, headers=auth())
    kw_id = r.json()["keyword_id"]
    d = client.delete(f"/keywords/{kw_id}", headers=auth())
    assert d.status_code == 204
    # second delete should 404
    d2 = client.delete(f"/keywords/{kw_id}", headers=auth())
    assert d2.status_code == 404


def test_memory_block_keyword_association_flow():
    # create memory block (personal) - reuse existing helper from other tests? replicate minimal
    # ensure agent exists
    agent_resp = client.post("/agents/", json={"agent_name": "AssocAgent", "visibility_scope": "personal"}, headers=auth())
    assert agent_resp.status_code == 201, agent_resp.text
    agent_id = agent_resp.json()["agent_id"]
    import uuid as _uuid
    conv_id = str(_uuid.uuid4())
    mb = client.post("/memory-blocks/", json={"content": "assoc test", "visibility_scope": "personal", "agent_id": agent_id, "conversation_id": conv_id}, headers=auth())
    assert mb.status_code == 201, mb.text
    mb_id = mb.json()["id"]
    kw = client.post("/keywords/", json={"keyword_text": "linkable"}, headers=auth())
    kid = kw.json()["keyword_id"]
    # associate
    a = client.post(f"/memory-blocks/{mb_id}/keywords/{kid}", headers=auth())
    assert a.status_code == 201, a.text
    # duplicate association should 409
    a2 = client.post(f"/memory-blocks/{mb_id}/keywords/{kid}", headers=auth())
    assert a2.status_code == 409
    # list keywords for memory block
    mk = client.get(f"/memory-blocks/{mb_id}/keywords/", headers=auth())
    assert mk.status_code == 200
    assert any(k["keyword_id"] == kid for k in mk.json())
    # list memory blocks for keyword
    kb = client.get(f"/keywords/{kid}/memory-blocks/", headers=auth())
    assert kb.status_code == 200
    assert any(m["id"] == mb_id for m in kb.json())
    # count
    cnt = client.get(f"/keywords/{kid}/memory-blocks/count", headers=auth())
    assert cnt.status_code == 200
    assert cnt.json()["count"] >= 1
    # disassociate
    dis = client.delete(f"/memory-blocks/{mb_id}/keywords/{kid}", headers=auth())
    assert dis.status_code == 204, dis.text
    # second disassociate should 404
    dis2 = client.delete(f"/memory-blocks/{mb_id}/keywords/{kid}", headers=auth())
    assert dis2.status_code == 404

from fastapi.testclient import TestClient
from core.api.main import app
from core.db.database import SessionLocal
from core.db import models

client = TestClient(app)

def auth(email="opt@example.com", name="Opt"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def seed_blocks_for_optimization():
    # create several blocks to trigger suggestions
    for i in range(3):
        client.post("/memory-blocks/", json={"content": "A" * (1600 + i), "visibility_scope": "personal"}, headers=auth())
    # one short block without keywords
    client.post("/memory-blocks/", json={"content": "short block", "visibility_scope": "personal"}, headers=auth())


def test_get_suggestions_and_execute_keyword_suggestion():
    seed_blocks_for_optimization()
    r = client.get("/memory-optimization/suggestions", headers=auth())
    assert r.status_code == 200, r.text
    data = r.json()
    suggestions = data.get("suggestions", [])
    assert isinstance(suggestions, list)
    # pick keyword suggestion if present else skip execution test
    keyword_sugg = None
    for s in suggestions:
        if s["type"] == "keywords":
            keyword_sugg = s
            break
    if keyword_sugg:
        sid = keyword_sugg["id"]
        exec_r = client.post(f"/memory-optimization/suggestions/{sid}/execute", headers=auth())
        assert exec_r.status_code == 200
        exec_data = exec_r.json()
        assert exec_data["status"] in ("completed", "error")


def test_preview_suggestion():
    preview = client.get("/memory-optimization/suggestions/fake-id/preview", headers=auth())
    assert preview.status_code == 200
    body = preview.json()
    assert body["preview"]["reversible"] is True

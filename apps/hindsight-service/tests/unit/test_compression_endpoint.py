from fastapi.testclient import TestClient
from core.api.main import app

client = TestClient(app)

def auth(email="comp@example.com", name="Comp"):
    return {"x-auth-request-email": email, "x-auth-request-user": name}


def test_compress_memory_block_missing_llm_key(monkeypatch):
    # create agent first
    agent_resp = client.post("/agents/", json={"agent_name": "CompAgent", "visibility_scope": "personal"}, headers=auth())
    assert agent_resp.status_code == 201, agent_resp.text
    agent_id = agent_resp.json()["agent_id"]
    import uuid as _uuid
    conv_id = str(_uuid.uuid4())
    mb = client.post("/memory-blocks/", json={"content": "Some long content to compress", "visibility_scope": "personal", "agent_id": agent_id, "conversation_id": conv_id}, headers=auth())
    assert mb.status_code == 201, mb.text
    mb_id = mb.json()["id"]
    # ensure env var not set
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    r = client.post(f"/memory-blocks/{mb_id}/compress", headers=auth())
    # Expect 500 due to missing key
    assert r.status_code == 500


def test_compress_memory_block_not_found(monkeypatch):
    # set fake api key to reach code path then stub service
    monkeypatch.setenv("LLM_API_KEY", "fake")
    class DummySvc:
        def compress_memory_block(self, *a, **kw):
            return {"error": True, "message": "Memory block not found"}
    from core import pruning
    monkeypatch.setattr(pruning.compression_service, "get_compression_service", lambda key: DummySvc())
    r = client.post(f"/memory-blocks/00000000-0000-0000-0000-000000000000/compress", headers=auth())
    assert r.status_code in (400, 500)


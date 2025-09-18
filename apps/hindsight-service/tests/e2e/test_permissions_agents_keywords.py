import os
import sys
import uuid

import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config

from .utils_pg import postgres_container


def _service_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, "..", ".."))


def _alembic_config(db_url: str) -> Config:
    service_dir = _service_root()
    ini_path = os.path.join(service_dir, "alembic.ini")
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    cfg = Config(ini_path)
    os.environ["TEST_DATABASE_URL"] = db_url
    os.environ["DATABASE_URL"] = db_url
    return cfg


@pytest.mark.e2e
def test_agents_keywords_scoping_and_guest_and_associations():
    with postgres_container() as (db_url, _):
        cfg = _alembic_config(db_url)
        command.upgrade(cfg, "head")

        # Configure environment
        os.environ["DEV_MODE"] = "false"
        os.environ["ADMIN_EMAILS"] = "alice@example.com"  # Alice is superadmin

        # Fresh import bound to this DB
        import sys as _sys
        for m in [k for k in list(_sys.modules.keys()) if k.startswith('core.api') or k.startswith('core.db')]:
            _sys.modules.pop(m, None)
        from core.api.main import app
        client = TestClient(app)

        alice = {"x-auth-request-user": "alice", "x-auth-request-email": "alice@example.com"}
        bob = {"x-auth-request-user": "bob", "x-auth-request-email": "bob@example.com"}
        guest = {}

        # 1) /user-info unauthenticated -> 401, {authenticated:false}
        r = client.get("/user-info", headers=guest)
        assert r.status_code == 401
        body = r.json()
        assert body.get("authenticated") is False

        # Create org and add Bob viewer
        org = client.post("/organizations/", json={"name": "Org K"}, headers=alice).json()
        org_id = org["id"]
        r = client.post(f"/organizations/{org_id}/members", json={"email": "bob@example.com", "role": "viewer"}, headers=alice)
        assert r.status_code == 201

        # 2) Create agents: one public (allowed for superadmin), one personal
        pub_agent = client.post("/agents/", json={"agent_name": "PublicAgent", "visibility_scope": "public"}, headers=alice).json()
        personal_agent = client.post("/agents/", json={"agent_name": "AlicePersonal", "visibility_scope": "personal"}, headers=alice).json()

        # Guest should only see public
        agents_guest = client.get("/agents/", headers=guest).json()
        names_guest = {a["agent_name"] for a in agents_guest}
        assert "PublicAgent" in names_guest
        assert "AlicePersonal" not in names_guest

        # 3) Keywords list scoping: create public + personal + org keywords
        r = client.post("/keywords/", json={"keyword_text": "public-key", "visibility_scope": "public"}, headers=alice)
        assert r.status_code == 201
        r = client.post("/keywords/", json={"keyword_text": "personal-key", "visibility_scope": "personal"}, headers=alice)
        assert r.status_code == 201
        r = client.post("/keywords/", json={"keyword_text": "org-key", "visibility_scope": "organization", "organization_id": org_id}, headers=alice)
        assert r.status_code == 201

        kws_guest = client.get("/keywords/", headers=guest).json()
        kw_texts = {k["keyword_text"] for k in kws_guest}
        assert "public-key" in kw_texts
        assert "personal-key" not in kw_texts
        assert "org-key" not in kw_texts

        # 4) Create org-scoped memory block and attempt associations
        agent_id = personal_agent["agent_id"]
        mb = client.post(
            "/memory-blocks/",
            json={
                "agent_id": agent_id,
                "conversation_id": str(uuid.uuid4()),
                "content": "some note",
                "visibility_scope": "organization",
                "organization_id": org_id,
            },
            headers=alice,
        ).json()

        # Get IDs of keywords
        # Find org-key and personal-key by listing with Alice
        kws_alice = client.get("/keywords/", headers=alice).json()
        org_kw = next(k for k in kws_alice if k["keyword_text"] == "org-key")
        personal_kw = next(k for k in kws_alice if k["keyword_text"] == "personal-key")

        # Bob (viewer) tries to associate org keyword to org memory -> 403 (no write)
        r = client.post(f"/memory-blocks/{mb['id']}/keywords/{org_kw['keyword_id']}", headers=bob)
        assert r.status_code == 403

        # Alice associates personal keyword to org memory -> 409 scope mismatch
        r = client.post(f"/memory-blocks/{mb['id']}/keywords/{personal_kw['keyword_id']}", headers=alice)
        assert r.status_code == 409


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
def test_scope_filters_and_permissions_endpoints():
    with postgres_container() as (db_url, _):
        cfg = _alembic_config(db_url)
        command.upgrade(cfg, "head")

        # Configure environment for app
        os.environ["DEV_MODE"] = "false"
        os.environ["ADMIN_EMAILS"] = "alice@example.com"

        # Import app after env is set
        # Ensure a fresh import bound to this test DB
        import sys as _sys
        for m in [k for k in list(_sys.modules.keys()) if k.startswith('core.api') or k.startswith('core.db')]:
            _sys.modules.pop(m, None)
        from core.api.main import app
        client = TestClient(app)

        alice_headers = {
            "x-auth-request-user": "alice",
            "x-auth-request-email": "alice@example.com",
        }
        bob_headers = {
            "x-auth-request-user": "bob",
            "x-auth-request-email": "bob@example.com",
        }

        # Create organization as Alice (owner)
        r = client.post("/organizations/", json={"name": "Org One", "slug": "org1"}, headers=alice_headers)
        assert r.status_code == 201, r.text
        org = r.json()
        org_id = org["id"]

        # Add Bob as viewer
        r = client.post(f"/organizations/{org_id}/members", json={"email": "bob@example.com", "role": "viewer"}, headers=alice_headers)
        assert r.status_code == 201, r.text

        # Create an agent as Alice (personal)
        r = client.post("/agents/", json={"agent_name": "TestAgent", "visibility_scope": "personal"}, headers=alice_headers)
        assert r.status_code == 201, r.text
        agent_id = r.json()["agent_id"]

        # Alice creates org-scoped memory block
        mb_payload = {
            "agent_id": agent_id,
            "conversation_id": str(uuid.uuid4()),
            "content": "Org note",
            "visibility_scope": "organization",
            "organization_id": org_id,
        }
        r = client.post("/memory-blocks/", json=mb_payload, headers=alice_headers)
        assert r.status_code == 201, r.text

        # Bob (viewer) attempts to create in org -> forbidden
        r = client.post("/memory-blocks/", json=mb_payload | {"content": "Bob try"}, headers=bob_headers)
        assert r.status_code == 403

        # Guest lists memory blocks -> should only see public; ensure empty OK (no error)
        r = client.get("/memory-blocks/")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data

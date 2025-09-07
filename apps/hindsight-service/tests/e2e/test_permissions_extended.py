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
def test_read_filters_and_scope_moves_and_permissions():
    with postgres_container() as (db_url, _):
        cfg = _alembic_config(db_url)
        command.upgrade(cfg, "head")

        os.environ["DEV_MODE"] = "false"
        # Make Alice superadmin to allow creating public data
        os.environ["ADMIN_EMAILS"] = "alice@example.com"

        # Ensure a fresh import bound to this test DB
        import sys as _sys
        for m in [k for k in list(_sys.modules.keys()) if k.startswith('core.api') or k.startswith('core.db')]:
            _sys.modules.pop(m, None)
        from core.api.main import app
        client = TestClient(app)

        alice = {"x-auth-request-user": "alice", "x-auth-request-email": "alice@example.com"}
        bob = {"x-auth-request-user": "bob", "x-auth-request-email": "bob@example.com"}
        guest = {}

        # Create org and add Bob as admin
        org = client.post("/organizations/", json={"name": "Org X"}, headers=alice).json()
        org_id = org["id"]
        r = client.post(f"/organizations/{org_id}/members", json={"email": "bob@example.com", "role": "admin", "can_write": True}, headers=alice)
        assert r.status_code == 201, r.text

        # Create agent (personal)
        agent = client.post("/agents/", json={"agent_name": "A1", "visibility_scope": "personal"}, headers=alice).json()
        agent_id = agent["agent_id"]

        # Alice creates personal memory
        mb_personal = client.post(
            "/memory-blocks/",
            json={
                "agent_id": agent_id,
                "conversation_id": str(uuid.uuid4()),
                "content": "Personal note with apple term",
                "visibility_scope": "personal",
            },
            headers=alice,
        ).json()

        # Alice creates public memory (as superadmin)
        r = client.post(
            "/memory-blocks/",
            json={
                "agent_id": agent_id,
                "conversation_id": str(uuid.uuid4()),
                "content": "Public note",
                "visibility_scope": "public",
            },
            headers=alice,
        )
        assert r.status_code == 201, r.text

        # Guest should see only public data
        data_guest = client.get("/memory-blocks/", headers=guest).json()
        assert isinstance(data_guest["items"], list)
        # Explicit scope narrowing by guest: personal should be empty, public should have items
        data_guest_personal = client.get("/memory-blocks/?scope=personal", headers=guest).json()
        assert len(data_guest_personal["items"]) == 0
        data_guest_public = client.get("/memory-blocks/?scope=public", headers=guest).json()
        assert len(data_guest_public["items"]) >= 1

        # Bob cannot delete Alice's personal memory
        r = client.delete(f"/memory-blocks/{mb_personal['id']}/hard-delete", headers=bob)
        assert r.status_code == 403

        # Bob tries to move Alice's personal memory to org -> consent required
        r = client.post(
            f"/memory-blocks/{mb_personal['id']}/change-scope",
            json={"visibility_scope": "organization", "organization_id": org_id},
            headers=bob,
        )
        assert r.status_code in (403, 409)  # 409 for consent, or 403 if policy denies without consent

        # Alice moves her personal memory to the org (allowed)
        r = client.post(
            f"/memory-blocks/{mb_personal['id']}/change-scope",
            json={"visibility_scope": "organization", "organization_id": org_id},
            headers=alice,
        )
        assert r.status_code == 200, r.text
        moved = r.json()
        assert moved["visibility_scope"] == "organization"
        assert moved["organization_id"] == org_id

        # Narrow listing by scope and org
        data_org_only = client.get(f"/memory-blocks/?scope=organization&organization_id={org_id}", headers=alice).json()
        assert all(item["visibility_scope"] == "organization" and item["organization_id"] == org_id for item in data_org_only["items"]) or len(data_org_only["items"]) == 0

        # Bob (admin) can now hard-delete the org memory
        r = client.delete(f"/memory-blocks/{mb_personal['id']}/hard-delete", headers=bob)
        assert r.status_code == 204

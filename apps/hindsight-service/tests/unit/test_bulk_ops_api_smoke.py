import uuid
from fastapi.testclient import TestClient

from core.api.main import app


client = TestClient(app)


def _h(user, email):
    return {"x-auth-request-user": user, "x-auth-request-email": email}


def test_bulk_ops_inventory_and_dry_runs():
    owner_email = f"bulk_{uuid.uuid4().hex[:8]}@example.com"
    # Create a source organization
    r_org = client.post("/organizations/", json={"name": f"BulkOrg_{uuid.uuid4().hex[:6]}"}, headers=_h("owner", owner_email))
    assert r_org.status_code == 201
    org_id = r_org.json()["id"]

    # Inventory should be present and numeric
    r_inv = client.get(f"/bulk-operations/organizations/{org_id}/inventory", headers=_h("owner", owner_email))
    assert r_inv.status_code == 200
    inv = r_inv.json()
    assert set(inv.keys()) == {"agent_count", "memory_block_count", "keyword_count"}

    # Dry-run bulk move with destination_owner_user_id only (allowed membership path)
    payload_move = {
        "dry_run": True,
        "destination_owner_user_id": str(uuid.uuid4()),
        "resource_types": ["agents", "memory_blocks", "keywords"],
    }
    r_move = client.post(f"/bulk-operations/organizations/{org_id}/bulk-move", json=payload_move, headers=_h("owner", owner_email))
    assert r_move.status_code == 200
    plan = r_move.json()
    assert "resources_to_move" in plan and "conflicts" in plan

    # Dry-run bulk delete
    payload_del = {"dry_run": True, "resource_types": ["agents", "memory_blocks", "keywords"]}
    r_del = client.post(f"/bulk-operations/organizations/{org_id}/bulk-delete", json=payload_del, headers=_h("owner", owner_email))
    assert r_del.status_code == 200
    plan_del = r_del.json()
    assert "resources_to_delete" in plan_del


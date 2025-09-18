import uuid
from fastapi.testclient import TestClient


def test_token_rotate_invalid_and_unknown_id(client: TestClient):
    headers = {"x-auth-request-email": "tokerr@example.com", "x-auth-request-user": "TokErr"}

    # Invalid UUID
    r = client.post("/users/me/tokens/not-a-uuid/rotate", headers=headers)
    assert r.status_code == 422

    # Unknown UUID: create a legitimate UUID not in DB
    unknown = uuid.uuid4()
    r = client.post(f"/users/me/tokens/{unknown}/rotate", headers=headers)
    # Not found or not active
    assert r.status_code in (404, 422)


def test_token_update_invalid_and_delete_unknown(client: TestClient):
    headers = {"x-auth-request-email": "tokerr2@example.com", "x-auth-request-user": "TokErr2"}

    # Update invalid id
    r = client.patch("/users/me/tokens/not-a-uuid", json={"name": "X"}, headers=headers)
    assert r.status_code == 422

    # Delete unknown id
    r = client.delete(f"/users/me/tokens/{uuid.uuid4()}", headers=headers)
    assert r.status_code in (404, 422)


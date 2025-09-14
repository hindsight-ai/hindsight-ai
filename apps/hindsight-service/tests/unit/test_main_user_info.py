import os
import pytest
from fastapi.testclient import TestClient

from core.api.main import app


def _h(email):
    return {"x-auth-request-user": email.split("@")[0], "x-auth-request-email": email}


@pytest.mark.usefixtures("db_session")
def test_user_info_dev_mode(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("DEV_MODE", "true")
    r = client.get("/user-info")
    assert r.status_code == 200
    data = r.json()
    assert data["authenticated"] is True
    assert data["email"] == "dev@localhost"


@pytest.mark.usefixtures("db_session")
def test_user_info_oauth_headers(monkeypatch):
    client = TestClient(app)
    monkeypatch.setenv("DEV_MODE", "false")
    r = client.get("/user-info", headers=_h("tester@example.com"))
    assert r.status_code == 200
    data = r.json()
    assert data["authenticated"] is True
    assert data["email"] == "tester@example.com"


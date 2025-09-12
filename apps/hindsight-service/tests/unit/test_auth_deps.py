import os
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.api.deps import get_current_user_context


def test_get_current_user_context_unauthorized(monkeypatch):
    # Ensure dev mode is off
    monkeypatch.setenv("DEV_MODE", "false")

    app = FastAPI()

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/me")
    assert r.status_code == 401


def test_get_current_user_context_dev_mode(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")

    app = FastAPI()

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx
        return {"email": user.email, "is_superadmin": bool(getattr(user, "is_superadmin", False))}

    client = TestClient(app)
    r = client.get("/me")
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "dev@localhost"


def test_admin_emails_elevation(monkeypatch):
    # Turn off dev mode to go through header identity
    monkeypatch.setenv("DEV_MODE", "false")
    admin_email = "auth_admin@example.com"
    monkeypatch.setenv("ADMIN_EMAILS", admin_email)

    app = FastAPI()

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx
        return {"email": user.email, "is_superadmin": bool(getattr(user, "is_superadmin", False))}

    client = TestClient(app)
    r = client.get("/me", headers={
        "x-auth-request-email": admin_email,
        "x-auth-request-user": "Admin"
    })
    assert r.status_code == 200
    assert r.json()["is_superadmin"] is True


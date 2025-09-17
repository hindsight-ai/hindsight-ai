import os
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.api.deps import get_current_user_context


def test_get_current_user_context_unauthorized(monkeypatch):
    # Ensure dev mode is off
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")

    app = FastAPI()

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/me")
    assert r.status_code == 401


def test_get_current_user_context_dev_mode(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")

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
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")
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


def test_admin_emails_do_not_elevate_others(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("ADMIN_EMAILS", "privileged@example.com")

    app = FastAPI()

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx
        return {"email": user.email, "is_superadmin": bool(getattr(user, "is_superadmin", False))}

    client = TestClient(app)
    r = client.get("/me", headers={
        "x-auth-request-email": "regular@example.com",
        "x-auth-request-user": "Regular"
    })
    assert r.status_code == 200
    assert r.json()["is_superadmin"] is False

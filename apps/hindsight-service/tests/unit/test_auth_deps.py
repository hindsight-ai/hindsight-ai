import os
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from core.api.deps import get_current_user_context
from core.db.database import get_db


def _wire_local_app_to_test_session(app: FastAPI) -> None:
    """Make a test-only FastAPI app share the conftest's transactional session.

    Without this, `get_db` falls back to its production implementation, which
    opens fresh sessions on the engine pool. Those sessions commit straight
    through to the testcontainer Postgres and the writes persist across tests
    — which leaks state and (post-F2) causes IdentityMismatchError 401s in
    later tests that send a different X-Auth-Request-User for the same email.
    """
    # Imported lazily so this module can be imported even outside pytest.
    from tests.conftest import _override_get_db  # type: ignore

    app.dependency_overrides[get_db] = _override_get_db


def test_get_current_user_context_unauthorized(monkeypatch):
    # Ensure dev mode is off
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setenv("APP_BASE_URL", "http://localhost:3000")

    app = FastAPI()
    _wire_local_app_to_test_session(app)

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
    _wire_local_app_to_test_session(app)

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx.user, user_ctx.current
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
    _wire_local_app_to_test_session(app)

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx.user, user_ctx.current
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
    _wire_local_app_to_test_session(app)

    @app.get("/me")
    def me(user_ctx = Depends(get_current_user_context)):
        user, current = user_ctx.user, user_ctx.current
        return {"email": user.email, "is_superadmin": bool(getattr(user, "is_superadmin", False))}

    client = TestClient(app)
    r = client.get("/me", headers={
        "x-auth-request-email": "regular@example.com",
        "x-auth-request-user": "Regular"
    })
    assert r.status_code == 200
    assert r.json()["is_superadmin"] is False

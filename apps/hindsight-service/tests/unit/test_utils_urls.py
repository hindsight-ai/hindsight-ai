import os
import pytest

from core.utils.urls import (
    _add_scheme_if_missing,
    _strip_trailing_slash,
    get_app_base_url,
    build_login_invite_link,
)


def test_add_scheme_if_missing_variants():
    assert _add_scheme_if_missing("https://example.com") == "https://example.com"
    assert _add_scheme_if_missing("http://example.com") == "http://example.com"
    assert _add_scheme_if_missing("localhost:3000") == "http://localhost:3000"
    assert _add_scheme_if_missing("127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert _add_scheme_if_missing("example.com") == "https://example.com"
    assert _add_scheme_if_missing("") == "http://localhost:3000"


def test_strip_trailing_slash():
    assert _strip_trailing_slash("https://x/") == "https://x"
    assert _strip_trailing_slash("https://x") == "https://x"


def test_get_app_base_url_env_precedence(monkeypatch):
    # APP_BASE_URL takes precedence and strips trailing slash
    monkeypatch.setenv("APP_BASE_URL", "https://x/")
    monkeypatch.delenv("APP_HOST", raising=False)
    assert get_app_base_url() == "https://x"

    # Fallback to APP_HOST and add scheme if missing
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.setenv("APP_HOST", "example.com/")
    assert get_app_base_url() == "https://example.com"

    # Default
    monkeypatch.delenv("APP_BASE_URL", raising=False)
    monkeypatch.delenv("APP_HOST", raising=False)
    assert get_app_base_url() == "http://localhost:3000"


def test_build_login_invite_link_accept_decline_with_token(monkeypatch):
    monkeypatch.setenv("APP_BASE_URL", "https://app.example.com")
    url = build_login_invite_link(
        invitation_id="inv1", org_id="org1", email="e@example.com", action="accept", token="t123"
    )
    assert url.startswith("https://app.example.com/login?")
    assert "accept_invite=inv1" in url and "org=org1" in url and "email=e%40example.com" in url and "token=t123" in url

    url2 = build_login_invite_link(
        invitation_id="inv2", org_id="org2", email="e2@example.com", action="decline"
    )
    assert "decline_invite=inv2" in url2 and "token=" not in url2


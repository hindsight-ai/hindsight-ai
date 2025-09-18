import os
from contextlib import contextmanager

from core.utils.urls import (
    _add_scheme_if_missing,
    _strip_trailing_slash,
    get_app_base_url,
    build_login_invite_link,
)


@contextmanager
def _env(**env):
    old = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_add_scheme_if_missing_variants():
    assert _add_scheme_if_missing("") == "http://localhost:3000"
    assert _add_scheme_if_missing("localhost:3000") == "http://localhost:3000"
    assert _add_scheme_if_missing("127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert _add_scheme_if_missing("example.com") == "https://example.com"
    assert _add_scheme_if_missing("https://already") == "https://already"
    assert _add_scheme_if_missing("http://already") == "http://already"


def test_strip_trailing_slash():
    assert _strip_trailing_slash("https://x/") == "https://x"
    assert _strip_trailing_slash("https://x") == "https://x"


def test_get_app_base_url_precedence():
    with _env(APP_BASE_URL="https://app.example.com/", APP_HOST=None):
        assert get_app_base_url() == "https://app.example.com"
    with _env(APP_BASE_URL="   ", APP_HOST="example.com/"):
        assert get_app_base_url() == "https://example.com"
    with _env(APP_BASE_URL=None, APP_HOST=None):
        assert get_app_base_url() == "http://localhost:3000"


def test_build_login_invite_link_accept_and_decline():
    with _env(APP_BASE_URL="https://app.example.com"):
        url = build_login_invite_link(
            invitation_id="inv1", org_id="org1", email="user@example.com"
        )
        assert url.startswith("https://app.example.com/login?")
        assert "accept_invite=inv1" in url and "org=org1" in url and "email=user%40example.com" in url

        d = build_login_invite_link(
            invitation_id="inv1", org_id="org1", email="user@example.com", action="decline", token="tok123"
        )
        assert "decline_invite=inv1" in d and "token=tok123" in d


"""
URL utilities for building absolute links in emails and notifications.

Primary source: APP_BASE_URL (e.g., https://app.hindsight-ai.com)
Fallback: APP_HOST for compatibility (adds scheme heuristically if missing).
"""
from __future__ import annotations

import os
from urllib.parse import urlencode


def _add_scheme_if_missing(host: str) -> str:
    h = host.strip()
    if not h:
        return "http://localhost:3000"
    if h.startswith("http://") or h.startswith("https://"):
        return h
    # Simple heuristic: use http for localhost, otherwise https
    lower = h.lower()
    if lower.startswith("localhost") or lower.startswith("127.0.0.1"):
        return f"http://{h}"
    return f"https://{h}"


def _strip_trailing_slash(url: str) -> str:
    return url[:-1] if url.endswith("/") else url


def get_app_base_url() -> str:
    """Return normalized base URL for the frontend application.

    Precedence:
    1. APP_BASE_URL (recommended)
    2. APP_HOST (legacy) — add scheme if missing
    Defaults to http://localhost:3000 if neither is set.
    """
    base = os.getenv("APP_BASE_URL")
    if base and base.strip():
        return _strip_trailing_slash(base.strip())
    host = os.getenv("APP_HOST")
    if host and host.strip():
        full = _add_scheme_if_missing(host.strip())
        return _strip_trailing_slash(full)
    return "http://localhost:3000"


def build_login_invite_link(*, invitation_id: str, org_id: str, email: str, action: str = "accept", token: str | None = None) -> str:
    """Build a login URL with invite context query params.

    action: "accept" or "decline"
    """
    base = get_app_base_url()
    key = "accept_invite" if action == "accept" else "decline_invite"
    params = {key: invitation_id, "org": org_id, "email": email}
    if token:
        params["token"] = token
    qs = urlencode(params)
    return f"{base}/login?{qs}"

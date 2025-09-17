"""Runtime environment helpers for guarding development-only flags."""

import os
from urllib.parse import urlparse
from typing import Optional, Set

_LOCAL_HOSTS: Set[str] = {"localhost", "127.0.0.1", "::1"}


def _extract_hostname(url_value: str) -> Optional[str]:
    """Return hostname from a URL or bare host string."""
    if not url_value:
        return None
    url_value = url_value.strip()
    if not url_value:
        return None
    candidate = url_value if "://" in url_value else f"http://{url_value}"
    parsed = urlparse(candidate)
    return parsed.hostname


def _allowed_dev_hosts() -> Set[str]:
    """Hosts that are allowed to run with DEV_MODE enabled."""
    extra = os.getenv("DEV_MODE_ALLOWED_HOSTS", "")
    allowed = set(_LOCAL_HOSTS)
    if extra:
        allowed.update({host.strip().lower() for host in extra.split(",") if host.strip()})
    return allowed


def dev_mode_requested() -> bool:
    """Return True when DEV_MODE env var is set to a truthy value."""
    return os.getenv("DEV_MODE", "false").lower() == "true"


def dev_mode_active() -> bool:
    """Return True if dev mode is enabled and allowed; raise if misconfigured.

    DEV_MODE can only be used when APP_BASE_URL points at localhost/127.0.0.1 (or
    an explicitly whitelisted host via DEV_MODE_ALLOWED_HOSTS). This prevents
    staging/production deployments from silently impersonating the dev user.
    """
    if not dev_mode_requested():
        return False

    hostname = _extract_hostname(os.getenv("APP_BASE_URL", ""))
    allowed_hosts = _allowed_dev_hosts()

    if hostname:
        if hostname.lower() not in allowed_hosts:
            raise RuntimeError(
                "DEV_MODE=true is not permitted when APP_BASE_URL points to "
                f"'{hostname}'. Allowed hosts: {sorted(allowed_hosts)}"
            )
    else:
        # No hostname available—require explicit opt-in for safety.
        if os.getenv("ALLOW_DEV_MODE", "false").lower() != "true" and not os.getenv("PYTEST_CURRENT_TEST"):
            raise RuntimeError(
                "DEV_MODE=true requires APP_BASE_URL to be set to a localhost URL "
                "or ALLOW_DEV_MODE=true for non-local execution."
            )

    return True

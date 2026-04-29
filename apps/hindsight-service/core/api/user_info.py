"""
User-info endpoint.

GET /user-info — returns authenticated user info and memberships.
Kept separate from core/api/users.py (prefix=/users) so the URL stays at /user-info.
"""
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import Request

from core.db.database import get_db
from core.api.auth import (
    resolve_identity_from_headers,
    get_or_create_user,
    get_user_memberships,
    is_beta_access_admin,
)
from core.api.deps import (
    get_current_user_context_or_pat,
    get_or_create_user_for_request,
    _ensure_dev_mode_defaults,
)
from core.utils.runtime import dev_mode_active
from core.utils.feature_flags import get_feature_flags

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/user-info")
def get_user_info(
    request: Request,
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
    authorization: Optional[str] = Header(default=None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    db: Session = Depends(get_db),
):
    """
    Return authenticated user info and memberships.
    - Dev mode (DEV_MODE=true): returns a stable dev user and ensures it exists.
    - Normal mode: reads headers set by oauth2-proxy, upserts user, and returns memberships.
    """
    try:
        is_dev_mode = dev_mode_active()
    except RuntimeError as exc:
        logger.error("DEV_MODE misconfiguration detected: %s", exc)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="DEV_MODE misconfigured")

    flags = get_feature_flags()

    if is_dev_mode:
        email = "dev@localhost"
        user = get_or_create_user(db, email=email, display_name="Development User")
        dev_pat_token = _ensure_dev_mode_defaults(db, user)
        memberships = get_user_memberships(db, user.id)
        beta_admin = True
        return {
            "authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_superadmin": True,
            "beta_access_status": "accepted",
            "memberships": memberships,
            "beta_access_admin": beta_admin,
            "llm_features_enabled": flags["llm_features_enabled"],
            "dev_mode_pat": dev_pat_token,
        }

    # If a PAT is provided, authenticate via PAT first
    if authorization or x_api_key:
        try:
            user, current_user = get_current_user_context_or_pat(
                db=db,
                authorization=authorization,
                x_api_key=x_api_key,
                x_auth_request_user=x_auth_request_user,
                x_auth_request_email=x_auth_request_email,
                x_forwarded_user=x_forwarded_user,
                x_forwarded_email=x_forwarded_email,
            )
            memberships = current_user.memberships
            return {
                "authenticated": True,
                "user_id": str(user.id),
                "email": user.email,
                "display_name": user.display_name,
                "is_superadmin": bool(getattr(user, "is_superadmin", False)),
                "beta_access_status": user.beta_access_status,
                "memberships": memberships,
                "pat": current_user.pat,
                "llm_features_enabled": flags["llm_features_enabled"],
            }
        except HTTPException as e:
            return JSONResponse({"authenticated": False, "detail": e.detail}, status_code=e.status_code)

    # Local dev fallback (no oauth, no PAT). Defaults to OFF; the previous
    # default-on + Host: localhost* check was spoofable via the Host header
    # whenever the backend was reachable without Traefik in front of it.
    # Now we require: explicit opt-in via ALLOW_LOCAL_DEV_AUTH=true AND a
    # loopback client_ip. The Host header is no longer consulted.
    try:
        allow_local = os.getenv("ALLOW_LOCAL_DEV_AUTH", "false").lower() == "true"
    except Exception:
        allow_local = False
    client_ip = None
    try:
        client_ip = request.client.host if request.client else None
    except Exception:
        client_ip = None
    is_local = allow_local and client_ip in ("127.0.0.1", "::1")
    if is_local and not any([x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email]):
        email = os.getenv('DEV_LOCAL_EMAIL', 'dev@localhost')
        name = os.getenv('DEV_LOCAL_NAME', 'Development User')
        user = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, user.id)
        return {
            "authenticated": True,
            "user_id": str(user.id),
            "email": user.email,
            "display_name": user.display_name,
            "is_superadmin": bool(user.is_superadmin),
            "beta_access_status": user.beta_access_status,
            "memberships": memberships,
            "llm_features_enabled": flags["llm_features_enabled"],
        }

    # Otherwise, fallback to oauth2-proxy headers
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not name and not email:
        return JSONResponse({"authenticated": False}, status_code=status.HTTP_401_UNAUTHORIZED)

    if not email:
        return {"authenticated": True, "user": name or None, "email": None}

    # IdentityMismatchError is translated to 401 by the global exception
    # handler at the top of main.py.
    user = get_or_create_user_for_request(db, email=email, name=name)
    memberships = get_user_memberships(db, user.id)
    beta_admin = is_beta_access_admin(user.email) or bool(user.is_superadmin)
    return {
        "authenticated": True,
        "user_id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(user.is_superadmin),
        "beta_access_status": user.beta_access_status,
        "memberships": memberships,
        "beta_access_admin": beta_admin,
        "llm_features_enabled": flags["llm_features_enabled"],
    }

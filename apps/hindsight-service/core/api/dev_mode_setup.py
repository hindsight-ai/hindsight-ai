"""Dev-mode user provisioning.

Extracted from ``core.api.deps`` (#92). Provisions superadmin rights,
beta-access acceptance, and a default PAT for ``dev@localhost`` users
on every dev-mode request. Cached PAT token is reused across requests
in the same process to avoid issuing a new token on every login.

Imported and called by ``get_current_user_context()`` in ``deps.py``
when ``dev_mode_active()`` is true. Does nothing in normal/production
mode.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from core.db import models
from core.db.repositories import tokens as token_repo
from core.db.schemas.tokens import TokenCreateRequest
from core.utils.token_crypto import parse_token

logger = logging.getLogger(__name__)

# Process-local cache so dev sessions don't issue a new PAT on every request.
# Reset by a process restart or by token rotation in the DB.
_DEV_MODE_PAT_CACHE: Optional[str] = None


def ensure_dev_mode_defaults(db: Session, user: models.User) -> Optional[str]:
    """Ensure dev@localhost has superadmin rights, beta access, and a PAT.

    Returns the active dev-mode PAT (cached in-process or freshly minted).
    """
    global _DEV_MODE_PAT_CACHE

    changed = False
    if not getattr(user, "is_superadmin", False):
        user.is_superadmin = True
        changed = True
    if getattr(user, "beta_access_status", "") != "accepted":
        user.beta_access_status = "accepted"
        changed = True

    if changed:
        try:
            db.commit()
        except Exception:
            db.rollback()
        else:
            db.refresh(user)

    # Reuse cached PAT token when still valid for this user
    token_value: Optional[str] = None
    if _DEV_MODE_PAT_CACHE:
        parsed = parse_token(_DEV_MODE_PAT_CACHE)
        if parsed:
            pat = token_repo.get_by_token_id(db, token_id=parsed.token_id)
            if pat and pat.status == "active" and pat.user_id == user.id:
                token_value = _DEV_MODE_PAT_CACHE

    if token_value is not None:
        return token_value

    active_tokens = [pat for pat in token_repo.list_tokens(db, user_id=user.id) if pat.status == "active"]
    full_token: Optional[str] = None
    if active_tokens:
        rotated = token_repo.rotate_token(db, token_db_id=active_tokens[0].id, user_id=user.id)
        if rotated:
            _pat, full_token = rotated
    if not full_token:
        payload = TokenCreateRequest(name="Dev Mode Default PAT", scopes=["read", "write"])
        _pat, full_token = token_repo.create_token(db, user_id=user.id, payload=payload)

    _DEV_MODE_PAT_CACHE = full_token
    logger.info("DEV_MODE PAT token issued for %s: %s", user.email, full_token)
    return full_token

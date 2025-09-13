"""
Repositories for Personal Access Tokens (PATs).

Implements create/list/get/revoke/rotate/update and last-used updates.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional

from sqlalchemy.orm import Session

from core.db import models, schemas
from core.utils import token_crypto


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(
    db: Session,
    *,
    user_id: uuid.UUID,
    payload: schemas.TokenCreateRequest,
) -> Tuple[models.PersonalAccessToken, str]:
    token_id, secret, full_token = token_crypto.generate_token()
    token_hash = token_crypto.hash_secret(secret)
    prefix, last_four = token_crypto.derive_display_parts(full_token)

    pat = models.PersonalAccessToken(
        user_id=user_id,
        token_id=token_id,
        token_hash=token_hash,
        name=payload.name,
        prefix=prefix,
        last_four=last_four,
        scopes=list(payload.scopes or []),
        organization_id=payload.organization_id,
        status="active",
        created_at=_now(),
        expires_at=payload.expires_at,
    )
    db.add(pat)
    db.commit()
    db.refresh(pat)
    return pat, full_token


def list_tokens(db: Session, *, user_id: uuid.UUID) -> List[models.PersonalAccessToken]:
    return (
        db.query(models.PersonalAccessToken)
        .filter(models.PersonalAccessToken.user_id == user_id)
        .order_by(models.PersonalAccessToken.created_at.desc())
        .all()
    )


def get_token_owned(db: Session, *, token_db_id: uuid.UUID, user_id: uuid.UUID) -> Optional[models.PersonalAccessToken]:
    return (
        db.query(models.PersonalAccessToken)
        .filter(
            models.PersonalAccessToken.id == token_db_id,
            models.PersonalAccessToken.user_id == user_id,
        )
        .first()
    )


def get_by_token_id(db: Session, *, token_id: str) -> Optional[models.PersonalAccessToken]:
    return (
        db.query(models.PersonalAccessToken)
        .filter(models.PersonalAccessToken.token_id == token_id)
        .first()
    )


def revoke_token(db: Session, *, token_db_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    pat = get_token_owned(db, token_db_id=token_db_id, user_id=user_id)
    if not pat:
        return False
    if pat.status != "revoked":
        pat.status = "revoked"
        pat.revoked_at = _now()
        db.commit()
        db.refresh(pat)
    return True


def rotate_token(db: Session, *, token_db_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Tuple[models.PersonalAccessToken, str]]:
    pat = get_token_owned(db, token_db_id=token_db_id, user_id=user_id)
    if not pat:
        return None
    # Only allow rotate on active tokens
    if pat.status != "active":
        return None
    _tid, secret, full_token = token_crypto.generate_token()
    # keep token_id stable for traceability
    token_hash = token_crypto.hash_secret(secret)
    prefix, last_four = token_crypto.derive_display_parts(full_token)
    pat.token_hash = token_hash
    pat.prefix = prefix
    pat.last_four = last_four
    # Optionally we could bump created_at; keep as is to preserve audit trail
    db.commit()
    db.refresh(pat)
    return pat, full_token


def update_token(db: Session, *, token_db_id: uuid.UUID, user_id: uuid.UUID, payload: schemas.TokenUpdateRequest) -> Optional[models.PersonalAccessToken]:
    pat = get_token_owned(db, token_db_id=token_db_id, user_id=user_id)
    if not pat:
        return None
    changed = False
    if payload.name is not None and payload.name.strip() and payload.name != pat.name:
        pat.name = payload.name.strip()
        changed = True
    if payload.expires_at != pat.expires_at:
        pat.expires_at = payload.expires_at
        changed = True
    if changed:
        db.commit()
        db.refresh(pat)
    return pat


def mark_used_now(db: Session, *, pat: models.PersonalAccessToken) -> None:
    pat.last_used_at = _now()
    try:
        db.commit()
    except Exception:
        db.rollback()


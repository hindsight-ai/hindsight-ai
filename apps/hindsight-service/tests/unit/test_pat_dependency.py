import uuid
from datetime import datetime, timedelta, timezone

import pytest

from sqlalchemy.orm import Session

from core.api import deps
from core.db import models, schemas
from core.db.repositories import tokens as token_repo


def _mk_user(db: Session, email: str = "patuser@example.com") -> models.User:
    u = models.User(email=email, display_name=email.split("@")[0])
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _mk_pat(db: Session, user: models.User, **kwargs):
    payload = schemas.TokenCreateRequest(
        name=kwargs.get("name", "test"),
        scopes=kwargs.get("scopes", ["read"]),
        organization_id=kwargs.get("organization_id"),
        expires_at=kwargs.get("expires_at"),
    )
    pat, token = token_repo.create_token(db, user_id=user.id, payload=payload)
    return pat, token


def test_dep_accepts_valid_pat(db_session: Session):
    user = _mk_user(db_session)
    _pat, token = _mk_pat(db_session, user)

    u, ctx = deps.get_current_user_context_or_pat(db=db_session, authorization=f"Bearer {token}")
    assert str(u.id) == str(ctx["id"])  # shape aligns
    assert ctx.get("pat") is not None
    assert "read" in set(ctx["pat"].get("scopes") or [])


def test_dep_rejects_bad_secret(db_session: Session):
    user = _mk_user(db_session, email="badsecret@example.com")
    pat, token = _mk_pat(db_session, user)
    # Replace secret with wrong one keeping token_id intact
    wrong = f"hs_pat_{pat.token_id}_WRONGSECRET"
    with pytest.raises(Exception):
        deps.get_current_user_context_or_pat(db=db_session, authorization=f"Bearer {wrong}")


def test_dep_rejects_invalid_format(db_session: Session):
    with pytest.raises(Exception):
        deps.get_current_user_context_or_pat(db=db_session, authorization="Bearer not_a_pat")


def test_dep_rejects_unknown_token_id(db_session: Session):
    tid = uuid.uuid4().hex[:16]
    fake = f"hs_pat_{tid}_whatever"
    with pytest.raises(Exception):
        deps.get_current_user_context_or_pat(db=db_session, authorization=f"Bearer {fake}")


def test_dep_rejects_revoked_and_expired(db_session: Session):
    user = _mk_user(db_session, email="expired@example.com")
    pat, token = _mk_pat(db_session, user)
    # Expired
    pat.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()
    with pytest.raises(Exception):
        deps.get_current_user_context_or_pat(db=db_session, authorization=f"Bearer {token}")
    # Revoked
    pat.expires_at = None
    pat.status = "revoked"
    db_session.commit()
    with pytest.raises(Exception):
        deps.get_current_user_context_or_pat(db=db_session, authorization=f"Bearer {token}")


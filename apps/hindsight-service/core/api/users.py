"""
Users API endpoints.

Currently exposes self-profile update for display name.
"""
from typing import Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.api.deps import get_current_user_context
from core.db import models, schemas
from core.db.repositories import tokens as token_repo
from core.audit import AuditAction, AuditStatus, log

router = APIRouter(prefix="/users", tags=["users"])  # normalized prefix


@router.patch("/me")
def update_me(
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    display_name = (payload.get("display_name") or None)

    if display_name is not None:
        # Basic validation
        s = str(display_name).strip()
        if len(s) == 0 or len(s) > 80:
            raise HTTPException(status_code=422, detail="display_name must be 1..80 characters")
        user.display_name = s
        db.commit()
        db.refresh(user)

    return {"id": str(user.id), "email": user.email, "display_name": user.display_name}


# Personal Access Tokens (PAT) management for the current user

@router.get("/me/tokens", response_model=list[schemas.TokenResponse])
def list_tokens(
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    pats = token_repo.list_tokens(db, user_id=user.id)
    return pats


@router.post("/me/tokens", response_model=schemas.TokenCreateResponse, status_code=status.HTTP_201_CREATED)
def create_token(
    payload: schemas.TokenCreateRequest,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    pat, full_token = token_repo.create_token(db, user_id=user.id, payload=payload)
    # Audit (no secrets)
    try:
        log(
            db,
            action=AuditAction.TOKEN_CREATE,
            status=AuditStatus.SUCCESS,
            target_type="personal_access_token",
            target_id=pat.id,
            actor_user_id=user.id,
            organization_id=payload.organization_id,
            metadata={
                "name": payload.name,
                "scopes": list(payload.scopes or []),
                "expires_at": payload.expires_at.isoformat() if payload.expires_at else None,
            },
        )
    except Exception:
        pass
    # Compose response
    return schemas.TokenCreateResponse(
        **schemas.TokenResponse.model_validate(pat, from_attributes=True).model_dump(),
        token=full_token,
    )


@router.delete("/me/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(
    token_id: str,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    try:
        uuid_token = uuid.UUID(str(token_id))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid token id")
    ok = token_repo.revoke_token(db, token_db_id=uuid_token, user_id=user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found")
    try:
        log(
            db,
            action=AuditAction.TOKEN_REVOKE,
            status=AuditStatus.SUCCESS,
            target_type="personal_access_token",
            target_id=uuid_token,
            actor_user_id=user.id,
            organization_id=None,
        )
    except Exception:
        pass
    return {"message": "revoked"}


@router.post("/me/tokens/{token_id}/rotate", response_model=schemas.TokenCreateResponse)
def rotate_token(
    token_id: str,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    try:
        uuid_token = uuid.UUID(str(token_id))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid token id")
    result = token_repo.rotate_token(db, token_db_id=uuid_token, user_id=user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Token not found or not active")
    pat, new_token = result
    try:
        log(
            db,
            action=AuditAction.TOKEN_ROTATE,
            status=AuditStatus.SUCCESS,
            target_type="personal_access_token",
            target_id=uuid_token,
            actor_user_id=user.id,
            organization_id=None,
        )
    except Exception:
        pass
    return schemas.TokenCreateResponse(
        **schemas.TokenResponse.model_validate(pat, from_attributes=True).model_dump(),
        token=new_token,
    )


@router.patch("/me/tokens/{token_id}", response_model=schemas.TokenResponse)
def update_token(
    token_id: str,
    payload: schemas.TokenUpdateRequest,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    user, _ctx = user_context
    try:
        uuid_token = uuid.UUID(str(token_id))
    except Exception:
        raise HTTPException(status_code=422, detail="Invalid token id")
    pat = token_repo.update_token(db, token_db_id=uuid_token, user_id=user.id, payload=payload)
    if not pat:
        raise HTTPException(status_code=404, detail="Token not found")
    return pat

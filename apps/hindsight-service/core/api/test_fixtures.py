"""Test-fixtures endpoints — gated behind E2E_TEST_HOOKS=true.

These endpoints exist solely to seed DB state for the Playwright E2E
suite (umbrella #96). They bypass production code paths that require
LLM (e.g. consolidation suggestion generation), letting tests exercise
the UI flows that operate on the resulting rows.

## Security model — three layers of defense

1. **Module not imported when flag is off.** ``core/api/main.py``
   conditionally imports + mounts this router only when
   ``E2E_TEST_HOOKS=true``. In production deploys, the env var is unset
   and the routes literally do not exist (404).
2. **In-handler re-check.** Every handler starts with
   ``_assert_hooks_enabled()``. Defense-in-depth — even if someone
   accidentally mounts the router unconditionally.
3. **CI-only env var.** ``E2E_TEST_HOOKS=true`` lives in
   ``.github/workflows/e2e.yml`` only; production compose files,
   helm values, etc. never set it.

## Authorization

Endpoints still require oauth2-proxy headers (e.g.
``x-auth-request-email``). The header identity is the OWNER of the
seeded data — protects against a leaked endpoint being used to read
other users' data via the response serializer.
"""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.api.deps import UserContext, get_current_user_context
from core.db import models, schemas
from core.db.database import get_db
from core.db.repositories import consolidation_suggestions as cs_repo

router = APIRouter(prefix="/test-fixtures", tags=["test-fixtures"])


def _hooks_enabled() -> bool:
    return os.getenv("E2E_TEST_HOOKS", "false").lower() == "true"


def _assert_hooks_enabled() -> None:
    """Raise 404 (not 403) when the flag is off — the route should
    appear not to exist at all to outside callers."""
    if not _hooks_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)


class SeedConsolidationSuggestionRequest(BaseModel):
    """Payload for seeding a ConsolidationSuggestion row.

    All fields below are persisted directly. ``original_memory_ids`` is
    enforced to be a list of memory blocks owned by the requesting user
    (defense against the leaked-endpoint scenario).
    """

    suggested_content: str
    suggested_lessons_learned: str = ""
    suggested_keywords: List[str] = []
    original_memory_ids: List[str]
    group_id: Optional[uuid.UUID] = None
    status: str = "pending"


@router.post("/consolidation-suggestion", status_code=status.HTTP_201_CREATED)
def seed_consolidation_suggestion(
    payload: SeedConsolidationSuggestionRequest,
    db: Session = Depends(get_db),
    user_context: UserContext = Depends(get_current_user_context),
):
    """Seed a ConsolidationSuggestion row owned by the requesting user.

    Used by E2E journey #106 to test the validate / reject UI without
    needing the LLM-driven consolidation worker (which is gated by
    ``LLM_FEATURES_ENABLED``).

    Validates ownership of all referenced memory blocks before insert.
    """
    _assert_hooks_enabled()
    user = user_context.user

    # Validate ownership of all referenced memory blocks
    for mid in payload.original_memory_ids:
        try:
            mid_uuid = uuid.UUID(mid)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail=f"Invalid memory_id: {mid}")
        block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == mid_uuid).first()
        if not block:
            raise HTTPException(status_code=404, detail=f"Memory block not found: {mid}")
        if block.owner_user_id != user.id:
            raise HTTPException(
                status_code=403,
                detail=f"Memory block {mid} not owned by requesting user",
            )

    suggestion_in = schemas.ConsolidationSuggestionCreate(
        group_id=payload.group_id or uuid.uuid4(),
        suggested_content=payload.suggested_content,
        suggested_lessons_learned=payload.suggested_lessons_learned,
        suggested_keywords=payload.suggested_keywords,
        original_memory_ids=payload.original_memory_ids,
        status=payload.status,
    )
    suggestion = cs_repo.create_consolidation_suggestion(db, suggestion=suggestion_in)
    return {
        "suggestion_id": str(suggestion.suggestion_id),
        "group_id": str(suggestion.group_id),
        "status": suggestion.status,
    }

"""
Consolidation endpoints.

Trigger consolidation analysis and manage consolidation suggestions.
"""
from __future__ import annotations

import logging
import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import crud, schemas, models
from core.api.permissions import can_read, can_write
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_read, ensure_pat_allows_write
from core.audit import log as audit_log, AuditAction, AuditStatus
from core.db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["consolidation"])  # keep paths stable for now


@router.post("/consolidation/trigger/", status_code=status.HTTP_202_ACCEPTED)
def trigger_consolidation_endpoint(db: Session = Depends(get_db)):
    """Trigger the memory block consolidation process manually."""
    import os
    from core.workers.consolidation_worker import run_consolidation_analysis

    logger.info("Manual trigger of consolidation process received")

    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. LLM-based consolidation will not occur.")

    try:
        run_consolidation_analysis(llm_api_key)
        return {"message": "Consolidation process triggered successfully"}
    except Exception as e:
        logger.error(f"Error triggering consolidation process: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error triggering consolidation process: {str(e)}")


def _user_can_view_suggestion(db: Session, suggestion, current_user) -> bool:
    try:
        # Check at least one original memory is readable
        for mid in suggestion.original_memory_ids or []:
            try:
                mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            except Exception:
                mem = None
            if mem and can_read(mem, current_user):
                return True
    except Exception:
        pass
    return False

def _user_can_write_suggestion(db: Session, suggestion, current_user) -> bool:
    try:
        # Require write on all originals to proceed with mutation
        for mid in suggestion.original_memory_ids or []:
            try:
                mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            except Exception:
                mem = None
            if not (mem and can_write(mem, current_user)):
                return False
        return True
    except Exception:
        return False


@router.get("/consolidation-suggestions/", response_model=schemas.PaginatedConsolidationSuggestions)
def get_consolidation_suggestions_endpoint(
    status: Optional[str] = None,
    group_id: Optional[uuid.UUID] = None,
    sort_by: Optional[str] = "timestamp",
    sort_order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Retrieve all consolidation suggestions with filtering/sorting/pagination."""
    logger.info(
        f"Fetching consolidation suggestions with filters: status={status}, group_id={group_id}"
    )

    user, current_user, scope_ctx = scoped
    # Enforce PAT read permissions based on requested scope
    ensure_pat_allows_read(current_user, getattr(scope_ctx, 'organization_id', None))

    # Fetch suggestions narrowed by SQL to the current scope to reduce cross-scope noise
    raw_suggestions, _total_items = crud.get_consolidation_suggestions_scoped(
        db=db,
        status=status,
        group_id=group_id,
        skip=skip,
        limit=limit,
        scope_ctx=scope_ctx,
        current_user=current_user,
    )
    def _in_scope(mem) -> bool:
        try:
            sc = getattr(scope_ctx, 'scope', None)
            if sc == 'organization':
                return getattr(mem, 'organization_id', None) == getattr(scope_ctx, 'organization_id', None)
            if sc == 'personal':
                return getattr(mem, 'owner_user_id', None) == (current_user or {}).get('id')
            if sc == 'public':
                return getattr(mem, 'visibility_scope', None) == 'public'
            # Default: treat as personal unless specified
            return getattr(mem, 'owner_user_id', None) == (current_user or {}).get('id')
        except Exception:
            return False

    scoped_suggestions = []
    for s in raw_suggestions:
        ok = False
        for mid in (s.original_memory_ids or []):
            try:
                mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            except Exception:
                mem = None
            if not mem:
                continue
            if can_read(mem, current_user) and _in_scope(mem):
                ok = True
                break
        if ok:
            scoped_suggestions.append(s)

    total_items = len(scoped_suggestions)
    total_pages = math.ceil(total_items / limit) if limit > 0 else 0

    return {"items": scoped_suggestions, "total_items": total_items, "total_pages": total_pages}


@router.get(
    "/consolidation-suggestions/{suggestion_id}",
    response_model=schemas.ConsolidationSuggestion,
)
def get_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Retrieve a specific consolidation suggestion by ID."""
    user, current_user, scope_ctx = scoped
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    # Enforce visibility based on original memories
    if not _user_can_view_suggestion(db, suggestion, current_user):
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return suggestion


@router.post(
    "/consolidation-suggestions/{suggestion_id}/validate/",
    response_model=schemas.ConsolidationSuggestion,
)
def validate_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Validate a consolidation suggestion and apply the consolidation."""
    logger.info(f"Validating consolidation suggestion {suggestion_id}")
    user, current_user, scope_ctx = scoped
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")
    if not _user_can_view_suggestion(db, suggestion, current_user):
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    # PAT enforcement for write in org context (derive org if applicable)
    try:
        org_id = None
        for mid in (suggestion.original_memory_ids or []):
            mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            if mem and getattr(mem, 'organization_id', None):
                org_id = mem.organization_id
                break
        ensure_pat_allows_write(current_user, org_id)
    except Exception:
        pass

    try:
        crud.apply_consolidation(db, suggestion_id=suggestion_id)
        updated = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
        if not updated:
            raise HTTPException(status_code=404, detail="Updated consolidation suggestion not found")
        if updated.status == "pending":
            update_schema = schemas.ConsolidationSuggestionUpdate(status="validated")
            updated = crud.update_consolidation_suggestion(
                db, suggestion_id=suggestion_id, suggestion=update_schema
            )
        # Audit: consolidation validated
        try:
            # Try to derive an org from first original memory
            org_id = None
            for mid in (updated.original_memory_ids or []):
                try:
                    mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
                except Exception:
                    mem = None
                if mem and getattr(mem, 'organization_id', None):
                    org_id = mem.organization_id
                    break
            audit_log(
                db,
                action=AuditAction.CONSOLIDATION_VALIDATE,
                status=AuditStatus.SUCCESS,
                target_type="consolidation_suggestion",
                target_id=updated.suggestion_id,
                actor_user_id=current_user.get('id'),
                organization_id=org_id,
                metadata={
                    "group_id": str(updated.group_id) if getattr(updated, 'group_id', None) else None,
                    "original_count": len(updated.original_memory_ids or []),
                },
            )
        except Exception:
            pass
        return updated
    except Exception as e:
        logger.error(f"Error validating suggestion {suggestion_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating suggestion: {str(e)}")


@router.post(
    "/consolidation-suggestions/{suggestion_id}/reject/",
    response_model=schemas.ConsolidationSuggestion,
)
def reject_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """Reject a consolidation suggestion, marking it as rejected."""
    logger.info(f"Rejecting consolidation suggestion {suggestion_id}")
    user, current_user, scope_ctx = scoped
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")
    if not _user_can_view_suggestion(db, suggestion, current_user):
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    # Mutating action: require write permission on all originals
    if not _user_can_write_suggestion(db, suggestion, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    # PAT enforcement for write on org context
    try:
        org_id = None
        for mid in (suggestion.original_memory_ids or []):
            mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            if mem and getattr(mem, 'organization_id', None):
                org_id = mem.organization_id
                break
        ensure_pat_allows_write(current_user, org_id)
    except Exception:
        pass
    if not _user_can_view_suggestion(db, suggestion, current_user):
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")

    update_schema = schemas.ConsolidationSuggestionUpdate(status="rejected")
    updated = crud.update_consolidation_suggestion(
        db, suggestion_id=suggestion_id, suggestion=update_schema
    )
    # Audit: consolidation rejected
    try:
        org_id = None
        for mid in (updated.original_memory_ids or []):
            try:
                mem = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == uuid.UUID(str(mid))).first()
            except Exception:
                mem = None
            if mem and getattr(mem, 'organization_id', None):
                org_id = mem.organization_id
                break
        audit_log(
            db,
            action=AuditAction.CONSOLIDATION_REJECT,
            status=AuditStatus.SUCCESS,
            target_type="consolidation_suggestion",
            target_id=updated.suggestion_id,
            actor_user_id=current_user.get('id'),
            organization_id=org_id,
            metadata={
                "group_id": str(updated.group_id) if getattr(updated, 'group_id', None) else None,
                "original_count": len(updated.original_memory_ids or []),
            },
        )
    except Exception:
        pass
    return updated


@router.delete(
    "/consolidation-suggestions/{suggestion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Delete a consolidation suggestion from the database."""
    success = crud.delete_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not success:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return {"message": "Consolidation suggestion deleted successfully"}

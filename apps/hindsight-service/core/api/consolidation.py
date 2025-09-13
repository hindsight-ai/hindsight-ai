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

from core.db import crud, schemas
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


@router.get("/consolidation-suggestions/", response_model=schemas.PaginatedConsolidationSuggestions)
def get_consolidation_suggestions_endpoint(
    status: Optional[str] = None,
    group_id: Optional[uuid.UUID] = None,
    sort_by: Optional[str] = "timestamp",
    sort_order: Optional[str] = "desc",
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Retrieve all consolidation suggestions with filtering/sorting/pagination."""
    logger.info(
        f"Fetching consolidation suggestions with filters: status={status}, group_id={group_id}"
    )

    suggestions, total_items = crud.get_consolidation_suggestions(
        db=db,
        status=status,
        group_id=group_id,
        skip=skip,
        limit=limit,
    )

    total_pages = math.ceil(total_items / limit) if limit > 0 else 0

    return {"items": suggestions, "total_items": total_items, "total_pages": total_pages}


@router.get(
    "/consolidation-suggestions/{suggestion_id}",
    response_model=schemas.ConsolidationSuggestion,
)
def get_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Retrieve a specific consolidation suggestion by ID."""
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    return suggestion


@router.post(
    "/consolidation-suggestions/{suggestion_id}/validate/",
    response_model=schemas.ConsolidationSuggestion,
)
def validate_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Validate a consolidation suggestion and apply the consolidation."""
    logger.info(f"Validating consolidation suggestion {suggestion_id}")
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")

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
        return updated
    except Exception as e:
        logger.error(f"Error validating suggestion {suggestion_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error validating suggestion: {str(e)}")


@router.post(
    "/consolidation-suggestions/{suggestion_id}/reject/",
    response_model=schemas.ConsolidationSuggestion,
)
def reject_consolidation_suggestion_endpoint(
    suggestion_id: uuid.UUID, db: Session = Depends(get_db)
):
    """Reject a consolidation suggestion, marking it as rejected."""
    logger.info(f"Rejecting consolidation suggestion {suggestion_id}")
    suggestion = crud.get_consolidation_suggestion(db, suggestion_id=suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Consolidation suggestion not found")
    if suggestion.status != "pending":
        raise HTTPException(status_code=400, detail="Suggestion is not in pending status")

    update_schema = schemas.ConsolidationSuggestionUpdate(status="rejected")
    return crud.update_consolidation_suggestion(
        db, suggestion_id=suggestion_id, suggestion=update_schema
    )


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

"""
Pruning API endpoints.

POST /memory/prune/suggest — generate pruning suggestions
POST /memory/prune/confirm — confirm and archive selected blocks
"""
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import crud
from core.db.database import get_db
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_write
from core.pruning.pruning_service import get_pruning_service
from core.utils.feature_flags import llm_features_enabled

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/memory/prune/suggest", response_model=dict)
def generate_pruning_suggestions_endpoint(
    request: dict = None,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Generate memory block pruning suggestions using LLM evaluation.
    Returns a batch of memory blocks with pruning scores for human review.
    """
    if request is None:
        request = {}

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    # Bypass the LLM gate when E2E_TEST_HOOKS=true — the pruning service
    # already has a deterministic `_fallback_scoring` path (sklearn-based)
    # that runs when LLM_API_KEY is unset, producing repeatable scores
    # suitable for E2E. The gate is preserved for production where
    # LLM-quality scoring is the product expectation.
    if not llm_features_enabled() and os.getenv("E2E_TEST_HOOKS", "false").lower() != "true":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")

    batch_size = request.get("batch_size", 50)
    target_count = request.get("target_count")
    max_iterations = request.get("max_iterations", 10)

    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Fallback scoring will be used.")

    try:
        # Get pruning service instance
        pruning_service = get_pruning_service(llm_api_key)

        # Generate pruning suggestions
        suggestions = pruning_service.generate_pruning_suggestions(
            db=db,
            batch_size=batch_size,
            target_count=target_count,
            max_iterations=max_iterations
        )

        return suggestions
    except Exception as e:
        logger.error(f"Error generating pruning suggestions: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating pruning suggestions: {str(e)}")


@router.post("/memory/prune/confirm", response_model=dict)
def confirm_pruning_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Confirm and archive selected memory blocks for pruning.
    This endpoint archives the memory blocks that were approved for pruning.
    """
    memory_block_ids = request.get("memory_block_ids", [])

    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided for pruning")

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    archived_count = 0
    failed_count = 0
    failed_blocks = []

    try:
        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                success = crud.archive_memory_block(db, memory_id=memory_id)
                if success:
                    archived_count += 1
                    logger.info(f"Successfully archived memory block {memory_id_str} for pruning")
                else:
                    failed_count += 1
                    failed_blocks.append(memory_id_str)
                    logger.warning(f"Failed to archive memory block {memory_id_str}")
            except ValueError:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Invalid UUID format for memory block ID: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                failed_blocks.append(memory_id_str)
                logger.error(f"Error archiving memory block {memory_id_str}: {str(e)}")

        db.commit()

        return {
            "message": f"Pruning confirmation processed successfully",
            "archived_count": archived_count,
            "failed_count": failed_count,
            "failed_blocks": failed_blocks if failed_blocks else None
        }
    except Exception as e:
        logger.error(f"Error confirming pruning: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error confirming pruning: {str(e)}")

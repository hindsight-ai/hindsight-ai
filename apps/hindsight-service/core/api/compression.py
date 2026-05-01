"""
Compression API endpoints.

POST /memory-blocks/{memory_id}/compress        — suggest compressed version
POST /memory-blocks/{memory_id}/compress/apply  — apply compressed content
"""
import logging
import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import crud, schemas
from core.db.database import get_db
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_write
from core.pruning.compression_service import get_compression_service
from core.utils.feature_flags import llm_features_enabled

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/memory-blocks/{memory_id}/compress", response_model=dict)
def compress_memory_block_endpoint(
    memory_id: uuid.UUID,
    request: dict = None,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Compress a memory block using LLM to create a more condensed version.
    Returns the compression suggestion for user review and approval.
    """
    if request is None:
        request = {}

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    if not llm_features_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")

    user_instructions = request.get("user_instructions", "")

    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform compression.")
        raise HTTPException(status_code=500, detail="LLM service not available for compression")

    try:
        # Get compression service instance
        compression_service = get_compression_service(llm_api_key)

        # Compress the memory block
        compression_result = compression_service.compress_memory_block(
            db=db,
            memory_id=memory_id,
            user_instructions=user_instructions
        )

        # Check if compression was successful
        if "error" in compression_result:
            raise HTTPException(
                status_code=400 if "not found" in compression_result["message"].lower() else 500,
                detail=compression_result["message"]
            )

        return compression_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error compressing memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compressing memory block: {str(e)}")


@router.post("/memory-blocks/{memory_id}/compress/apply", response_model=schemas.MemoryBlock)
def apply_memory_compression_endpoint(
    memory_id: uuid.UUID,
    request: dict,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Apply the compressed version to replace the original memory block content.
    """
    compressed_content = request.get("compressed_content")
    compressed_lessons = request.get("compressed_lessons_learned")

    if not compressed_content:
        raise HTTPException(status_code=400, detail="Compressed content is required")

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    try:
        # Update the memory block with compressed content
        update_data = schemas.MemoryBlockUpdate(
            content=compressed_content,
            lessons_learned=compressed_lessons
        )

        updated_memory = crud.update_memory_block(
            db=db,
            memory_id=memory_id,
            memory_block=update_data
        )

        if not updated_memory:
            raise HTTPException(status_code=404, detail="Memory block not found")

        logger.info(f"Successfully applied compression to memory block {memory_id}")
        return updated_memory

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error applying compression to memory block {memory_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying compression: {str(e)}")

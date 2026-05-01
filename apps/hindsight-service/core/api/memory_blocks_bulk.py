"""
Memory-blocks bulk operation endpoints.

POST /memory-blocks/bulk-generate-keywords — generate keyword suggestions
POST /memory-blocks/bulk-apply-keywords    — apply selected keywords
POST /memory-blocks/bulk-compact           — bulk AI compression

These routes use the /memory-blocks/bulk-* URL pattern (not /bulk-operations/*),
so they live here rather than in bulk_operations.py which carries the
/bulk-operations prefix for admin-level operations.
"""
import asyncio
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.db import crud, models, schemas
from core.db.database import get_db
from core.api.deps import get_scoped_user_and_context, ensure_pat_allows_write
from core.pruning.compression_service import get_compression_service
from core.services.keyword_extraction_service import extract_keywords_enhanced
from core.utils.feature_flags import llm_features_enabled

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/memory-blocks/bulk-generate-keywords", response_model=dict)
def bulk_generate_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Generate keywords for multiple memory blocks using basic keyword extraction.
    Returns suggested keywords for each memory block for user review and approval.
    """
    memory_block_ids = request.get("memory_block_ids", [])

    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    try:
        suggestions = []
        successful_count = 0
        failed_count = 0

        for memory_id_str in memory_block_ids:
            try:
                memory_id = uuid.UUID(memory_id_str)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)

                if not memory_block:
                    logger.warning(f"Memory block not found: {memory_id_str}")
                    continue

                # Extract keywords from content and lessons_learned
                content_text = (memory_block.content or '') + ' ' + (memory_block.lessons_learned or '')

                # Simple keyword extraction (enhanced version of the disabled function)
                suggested_keywords = extract_keywords_enhanced(content_text)

                if suggested_keywords:
                    suggestions.append({
                        "memory_block_id": str(memory_id),
                        "memory_block_content_preview": (memory_block.content or '')[:100] + "..." if len(memory_block.content or '') > 100 else (memory_block.content or ''),
                        "suggested_keywords": suggested_keywords,
                        "current_keywords": [kw.keyword_text for kw in memory_block.keywords] if memory_block.keywords else []
                    })
                    successful_count += 1
                else:
                    logger.info(f"No keywords could be extracted for memory block {memory_id_str}")
                    failed_count += 1

            except ValueError:
                failed_count += 1
                logger.error(f"Invalid UUID format: {memory_id_str}")
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing memory block {memory_id_str}: {str(e)}")

        return {
            "suggestions": suggestions,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Generated keyword suggestions for {successful_count} memory blocks"
        }

    except Exception as e:
        logger.error(f"Error in bulk keyword generation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating keywords: {str(e)}")


@router.post("/memory-blocks/bulk-apply-keywords", response_model=dict)
def bulk_apply_keywords_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Apply selected keywords to memory blocks.
    Expects a list of memory block IDs with their selected keywords.
    """
    applications = request.get("applications", [])

    if not applications:
        raise HTTPException(status_code=400, detail="No keyword applications provided")

    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    try:
        successful_count = 0
        failed_count = 0
        results = []

        for application in applications:
            memory_block_id = application.get("memory_block_id")
            selected_keywords = application.get("selected_keywords", [])

            if not memory_block_id or not selected_keywords:
                failed_count += 1
                continue

            try:
                memory_id = uuid.UUID(memory_block_id)
                memory_block = crud.get_memory_block(db, memory_id=memory_id)

                if not memory_block:
                    failed_count += 1
                    continue

                added_keywords = []
                skipped_keywords = []

                for keyword_text in selected_keywords:
                    # Get or create keyword
                    keyword = crud.get_keyword_by_text(db, keyword_text=keyword_text)
                    if not keyword:
                        keyword_create = schemas.KeywordCreate(keyword_text=keyword_text)
                        keyword = crud.create_keyword(db=db, keyword=keyword_create)

                    # Check if association already exists
                    existing_association = db.query(models.MemoryBlockKeyword).filter(
                        models.MemoryBlockKeyword.memory_id == memory_id,
                        models.MemoryBlockKeyword.keyword_id == keyword.keyword_id
                    ).first()

                    if not existing_association:
                        crud.create_memory_block_keyword(db, memory_id=memory_id, keyword_id=keyword.keyword_id)
                        added_keywords.append(keyword_text)
                    else:
                        skipped_keywords.append(keyword_text)

                results.append({
                    "memory_block_id": memory_block_id,
                    "added_keywords": added_keywords,
                    "skipped_keywords": skipped_keywords,
                    "success": True
                })
                successful_count += 1

            except Exception as e:
                logger.error(f"Error applying keywords to memory block {memory_block_id}: {str(e)}")
                results.append({
                    "memory_block_id": memory_block_id,
                    "error": str(e),
                    "success": False
                })
                failed_count += 1

        return {
            "results": results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "message": f"Applied keywords to {successful_count} memory blocks"
        }

    except Exception as e:
        logger.error(f"Error in bulk keyword application: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error applying keywords: {str(e)}")


@router.post("/memory-blocks/bulk-compact", response_model=dict)
async def bulk_compact_memory_blocks_endpoint(
    request: dict,
    db: Session = Depends(get_db),
    scoped = Depends(get_scoped_user_and_context),
):
    """
    Bulk compact multiple memory blocks using AI compression.
    This endpoint processes multiple memory blocks for compaction with optional concurrency.
    """
    user = scoped.user
    current_user = scoped.current
    _scope_ctx = scoped.scope
    if user is None or current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    ensure_pat_allows_write(current_user)

    if not llm_features_enabled():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM features are currently disabled")

    logger.info(f"Bulk compaction request received with {len(request.get('memory_block_ids', []))} blocks")

    memory_block_ids = request.get("memory_block_ids", [])
    user_instructions = request.get("user_instructions", "")
    max_concurrent = request.get("max_concurrent", 1)  # Default to 1 for safety

    # Validate max_concurrent parameter
    if not isinstance(max_concurrent, int) or max_concurrent < 1:
        max_concurrent = 1
    if max_concurrent > 10:  # Reasonable upper limit to prevent abuse
        max_concurrent = 10

    logger.info(f"Using max_concurrent: {max_concurrent}")

    if not memory_block_ids:
        raise HTTPException(status_code=400, detail="No memory block IDs provided")

    # Retrieve LLM_API_KEY from environment variables
    llm_api_key = os.getenv("LLM_API_KEY")
    if not llm_api_key:
        logger.warning("LLM_API_KEY is not set. Cannot perform bulk compaction.")
        raise HTTPException(status_code=500, detail="LLM service not available for compaction")

    logger.info(f"Starting bulk compaction for {len(memory_block_ids)} blocks with {max_concurrent} concurrent processes")

    def process_single_block(memory_id_str: str):
        """Process a single memory block in a separate thread."""
        try:
            memory_id = uuid.UUID(memory_id_str)
            logger.info(f"Starting compression for block {memory_id_str}")

            # Get compression service instance (in the thread)
            compression_service = get_compression_service(llm_api_key)

            # Create a new DB session for this thread
            db_gen = get_db()
            thread_db = next(db_gen)

            try:
                # Compress the memory block
                compression_result = compression_service.compress_memory_block(
                    db=thread_db,
                    memory_id=memory_id,
                    user_instructions=user_instructions
                )
                logger.info(f"Compression completed for block {memory_id_str}")

                # Check if compression was successful
                if "error" not in compression_result:
                    # Auto-apply the compression if successful
                    compressed_content = compression_result.get("compressed_content")
                    compressed_lessons = compression_result.get("compressed_lessons_learned")

                    if compressed_content:
                        # Update the memory block with compressed content
                        update_data = schemas.MemoryBlockUpdate(
                            content=compressed_content,
                            lessons_learned=compressed_lessons
                        )

                        updated_memory = crud.update_memory_block(
                            db=thread_db,
                            memory_id=memory_id,
                            memory_block=update_data
                        )

                        if updated_memory:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": True,
                                "original_length": len(compression_result.get("original_content", "")),
                                "compressed_length": len(compressed_content),
                                "compression_ratio": compression_result.get("compression_ratio", 0),
                                "message": "Successfully compacted"
                            }
                        else:
                            return {
                                "memory_block_id": memory_id_str,
                                "success": False,
                                "error": "Failed to update memory block"
                            }
                    else:
                        return {
                            "memory_block_id": memory_id_str,
                            "success": False,
                            "error": "No compressed content returned"
                        }
                else:
                    return {
                        "memory_block_id": memory_id_str,
                        "success": False,
                        "error": compression_result.get("message", "Compression failed")
                    }
            finally:
                thread_db.close()

        except ValueError:
            logger.error(f"Invalid UUID format: {memory_id_str}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": "Invalid UUID format"
            }
        except Exception as e:
            logger.error(f"Error compacting memory block {memory_id_str}: {str(e)}")
            return {
                "memory_block_id": memory_id_str,
                "success": False,
                "error": str(e)
            }

    try:
        # Use ThreadPoolExecutor for concurrent processing
        # Use a fresh event loop retrieval that is future-safe; if no loop set, create one
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop; create a temporary one (mainly for sync test contexts)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            # Create tasks for all memory blocks
            tasks = [
                loop.run_in_executor(executor, process_single_block, memory_id)
                for memory_id in memory_block_ids
            ]

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results and handle exceptions
        processed_results = []
        successful_count = 0
        failed_count = 0

        for result in results:
            if isinstance(result, Exception):
                failed_count += 1
                processed_results.append({
                    "memory_block_id": "unknown",
                    "success": False,
                    "error": str(result)
                })
            else:
                processed_results.append(result)
                if result.get("success", False):
                    successful_count += 1
                else:
                    failed_count += 1

        return {
            "results": processed_results,
            "successful_count": successful_count,
            "failed_count": failed_count,
            "total_processed": len(memory_block_ids),
            "message": f"Successfully compacted {successful_count} out of {len(memory_block_ids)} memory blocks"
        }

    except Exception as e:
        logger.error(f"Error in bulk memory block compaction: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error compacting memory blocks: {str(e)}")

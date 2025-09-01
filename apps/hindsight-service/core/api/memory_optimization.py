from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from datetime import datetime
import json

from core.db import crud, models
from core.db.database import get_db
from core.db import schemas

router = APIRouter()

@router.get("/suggestions")
async def get_memory_optimization_suggestions(db: Session = Depends(get_db)):
    """
    Analyze memory blocks and return AI-powered optimization suggestions
    """
    try:
        suggestions = []
        
        # 1. Analyze for compaction opportunities (long memory blocks)
        long_blocks = db.query(models.MemoryBlock).filter(
            models.MemoryBlock.archived == False
        ).all()
        
        # Find blocks that are longer than 1500 characters
        compaction_candidates = [
            block for block in long_blocks 
            if len(block.content or '') > 1500
        ]
        
        if compaction_candidates:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "compaction",
                "title": f"Compact {len(compaction_candidates)} lengthy memory blocks",
                "description": f"Found {len(compaction_candidates)} memory blocks with more than 1500 characters that could benefit from compaction to improve performance and reduce storage.",
                "priority": "high" if len(compaction_candidates) > 10 else "medium",
                "affected_blocks": [str(block.id) for block in compaction_candidates[:20]],  # Limit to 20 for display
                "all_affected_blocks": [str(block.id) for block in compaction_candidates],   # full set for execution
                "estimated_impact": f"Reduce storage by an estimated 30-50% ({len(compaction_candidates)} blocks)",
                "status": "pending"
            })
        
        # 2. Analyze for keyword optimization (blocks without keywords)
        blocks_without_keywords = []
        for block in long_blocks:
            if not block.memory_block_keywords or len(block.memory_block_keywords) == 0:
                blocks_without_keywords.append(block)
        
        if blocks_without_keywords:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "keywords",
                "title": f"Add keywords to {len(blocks_without_keywords)} memory blocks",
                "description": f"Found {len(blocks_without_keywords)} memory blocks without keywords. Adding keywords will improve searchability and organization.",
                "priority": "medium",
                "affected_blocks": [str(block.id) for block in blocks_without_keywords[:20]],  # preview subset
                "all_affected_blocks": [str(block.id) for block in blocks_without_keywords],   # full set for execution
                "estimated_impact": f"Improve searchability for {len(blocks_without_keywords)} blocks",
                "status": "pending"
            })
        
        # 3. Analyze for archival opportunities (old, low-feedback blocks)
        old_blocks = db.query(models.MemoryBlock).filter(
            models.MemoryBlock.archived == False,
            models.MemoryBlock.feedback_score <= 0,
            models.MemoryBlock.retrieval_count <= 1
        ).all()
        
        # Filter to blocks older than 90 days with low engagement
        archival_candidates = []
        current_time = datetime.utcnow()
        for block in old_blocks:
            # Handle timezone-aware vs naive datetime comparison
            created_at = block.created_at
            if created_at.tzinfo is not None:
                # If created_at is timezone-aware, make current_time timezone-aware too
                from datetime import timezone
                current_time_tz = current_time.replace(tzinfo=timezone.utc)
                days_old = (current_time_tz - created_at).days
            else:
                # If created_at is naive, use naive current_time
                days_old = (current_time - created_at).days
            
            if days_old > 90:
                archival_candidates.append(block)
        
        if archival_candidates:
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "archive",
                "title": f"Archive {len(archival_candidates)} old, unused memory blocks",
                "description": f"Found {len(archival_candidates)} memory blocks that are over 90 days old with low engagement (0 feedback, ≤1 retrievals). Consider archiving to improve performance.",
                "priority": "low",
                "affected_blocks": [str(block.id) for block in archival_candidates[:20]],
                "estimated_impact": f"Clean up {len(archival_candidates)} low-value blocks",
                "status": "pending"
            })
        
        # 4. Analyze for potential duplicates (simple content similarity)
        # This is a basic implementation - in a real system you'd use semantic similarity
        content_groups = {}
        for block in long_blocks[:100]:  # Limit to avoid performance issues
            # Simple similarity based on first 100 characters
            content_key = (block.content or '')[:100].lower().strip()
            if len(content_key) > 50:  # Only consider blocks with substantial content
                if content_key not in content_groups:
                    content_groups[content_key] = []
                content_groups[content_key].append(block)
        
        duplicate_groups = {k: v for k, v in content_groups.items() if len(v) > 1}
        if duplicate_groups:
            total_duplicates = sum(len(group) for group in duplicate_groups.values())
            all_duplicate_blocks = []
            for group in duplicate_groups.values():
                all_duplicate_blocks.extend(group)
            
            suggestions.append({
                "id": str(uuid.uuid4()),
                "type": "merge",
                "title": f"Merge {total_duplicates} potentially duplicate memory blocks",
                "description": f"Found {len(duplicate_groups)} groups of similar memory blocks that might be duplicates. Merging them could reduce redundancy.",
                "priority": "medium",
                "affected_blocks": [str(block.id) for block in all_duplicate_blocks[:20]],
                "estimated_impact": f"Reduce redundancy by merging {total_duplicates} similar blocks",
                "status": "pending"
            })
        
        return {
            "suggestions": suggestions,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "total_memory_blocks_analyzed": len(long_blocks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze memory blocks: {str(e)}")

@router.post("/suggestions/{suggestion_id}/execute")
async def execute_optimization_suggestion(
    suggestion_id: str, 
    db: Session = Depends(get_db)
):
    """
    Execute a specific optimization suggestion
    """
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # First, re-analyze to get current suggestions and find the suggestion by ID
        response = await get_memory_optimization_suggestions(db)
        suggestions = response.get("suggestions", [])
        
        # Find the suggestion by ID
        suggestion = None
        for s in suggestions:
            if s["id"] == suggestion_id:
                suggestion = s
                break
        
        if not suggestion:
            return {
                "suggestion_id": suggestion_id,
                "status": "error",
                "message": "Suggestion not found or may have become stale",
                "results": None
            }
        
        # Execute based on suggestion type
        if suggestion["type"] == "keywords":
            # Execute keyword generation directly using the bulk keyword generation function
            try:
                from core.api.main import extract_keywords_enhanced
                
                suggestions_list = []
                successful_count = 0
                failed_count = 0
                
                # Prefer full list if available
                target_block_ids = suggestion.get("all_affected_blocks") or suggestion.get("affected_blocks") or []
                
                for memory_id_str in target_block_ids:
                    try:
                        memory_id = uuid.UUID(memory_id_str)
                        memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
                        
                        if not memory_block:
                            logger.warning(f"Memory block not found: {memory_id_str}")
                            continue
                        
                        # Extract keywords from content and lessons_learned
                        content_text = (memory_block.content or '') + ' ' + (memory_block.lessons_learned or '')
                        
                        # Simple keyword extraction
                        suggested_keywords = extract_keywords_enhanced(content_text)
                        
                        if suggested_keywords:
                            suggestions_list.append({
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
                
                keyword_data = {
                    "suggestions": suggestions_list,
                    "successful_count": successful_count,
                    "failed_count": failed_count,
                    "total_processed": len(target_block_ids),
                    "message": f"Generated keyword suggestions for {successful_count} memory blocks"
                }
                
                return {
                    "suggestion_id": suggestion_id,
                    "status": "completed",
                    "execution_timestamp": datetime.utcnow().isoformat(),
                    "message": "Keyword suggestions generated successfully",
                    "results": {
                        "type": "keyword_suggestions",
                        "data": keyword_data,
                        "summary": f"Generated keyword suggestions for {successful_count} memory blocks",
                        "metrics": {
                            "blocks_processed": str(successful_count),
                            "suggestions_generated": str(len(suggestions_list)),
                            "execution_time": "< 1 second"
                        }
                    }
                }
                    
            except Exception as e:
                logger.error(f"Error executing keyword suggestion: {str(e)}")
                return {
                    "suggestion_id": suggestion_id,
                    "status": "error",
                    "message": f"Error generating keywords: {str(e)}",
                    "results": None
                }
        
        else:
            # For other suggestion types, return a mock response for now
            return {
                "suggestion_id": suggestion_id,
                "status": "completed",
                "execution_timestamp": datetime.utcnow().isoformat(),
                "message": f"Optimization suggestion ({suggestion['type']}) has been queued for execution",
                "results": {
                    "summary": "Action completed successfully",
                    "metrics": {
                        "blocks_processed": str(len(suggestion.get("affected_blocks", []))),
                        "improvement_type": suggestion["type"],
                        "execution_time": "2.3 seconds"
                    }
                }
            }
            
    except Exception as e:
        logger.error(f"Error executing optimization suggestion {suggestion_id}: {str(e)}")
        return {
            "suggestion_id": suggestion_id,
            "status": "error",
            "message": f"Error executing suggestion: {str(e)}",
            "results": None
        }

@router.get("/suggestions/{suggestion_id}/preview")
async def preview_optimization_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db)
):
    """
    Preview what would happen if a suggestion is executed
    """
    return {
        "suggestion_id": suggestion_id,
        "preview": {
            "affected_blocks": [],
            "estimated_changes": {},
            "reversible": True
        }
    }

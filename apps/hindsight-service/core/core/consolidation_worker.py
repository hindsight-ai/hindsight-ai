"""
Shim for backward compatibility with tests and legacy imports.

The consolidation worker implementation lives in `core.workers.consolidation_worker`.
This module provides thin wrappers around selected functions so that test patches
targeting this module (e.g., get_all_memory_blocks, create_consolidation_suggestion,
get_db) continue to work without modifying tests.
"""

import logging
from typing import Dict, Any, List
import uuid

from core.workers.consolidation_worker import (  # type: ignore
    analyze_duplicates_with_fallback,
)
import os, json
from core.db.crud import get_all_memory_blocks, create_consolidation_suggestion  # for test patch compatibility
from core.db.database import get_db  # for test patch compatibility

__all__ = [
    "fetch_memory_blocks",
    "analyze_duplicates_with_fallback",
    "analyze_duplicates_with_llm",
    "store_consolidation_suggestions",
    "run_consolidation_analysis",
    "get_all_memory_blocks",
    "create_consolidation_suggestion",
    "get_db",
]

logger = logging.getLogger(__name__)


def fetch_memory_blocks(db, offset: int, limit: int) -> List[Dict[str, Any]]:
    """Wrapper using shim-level get_all_memory_blocks to preserve patching semantics."""
    try:
        memory_blocks = get_all_memory_blocks(db, skip=offset, limit=limit)
        logger.info(f"Fetched batch of {len(memory_blocks)} memory blocks (offset: {offset})")
        if memory_blocks:
            return [mb.__dict__ for mb in memory_blocks]
        return []
    except Exception as e:
        logger.error(f"Error fetching memory blocks: {str(e)}")
        return []


def store_consolidation_suggestions(db, groups: List[Dict[str, Any]]) -> int:
    """Wrapper that uses shim-level create_consolidation_suggestion symbol for patching."""
    from core.db.models import ConsolidationSuggestion

    created_count = 0
    for group in groups:
        if not group.get("suggested_content") or not group.get("suggested_lessons_learned"):
            logger.info(
                f"Skipping group {group.get('group_id', 'unknown')} as it lacks LLM-generated content/lessons learned."
            )
            continue
        try:
            memory_ids = sorted(group.get("memory_ids", []))
            existing_suggestions = db.query(ConsolidationSuggestion).filter(
                ConsolidationSuggestion.status == "pending"
            ).all()

            has_overlap = False
            for suggestion in existing_suggestions:
                existing_ids = set(suggestion.original_memory_ids or [])
                current_ids = set(memory_ids)
                if existing_ids & current_ids:
                    has_overlap = True
                    break
            if has_overlap:
                group_id = group.get('group_id', 'unknown')
                logger.info(
                    f"Skipping group {group_id} due to existing pending suggestion(s) with overlapping memory IDs"
                )
                continue

            try:
                group_id_str = group.get("group_id", str(uuid.uuid4()))
                try:
                    group_id_uuid = uuid.UUID(group_id_str) if isinstance(group_id_str, str) else group_id_str
                except ValueError:
                    logger.warning(
                        f"Invalid UUID format for group_id {group_id_str}, generating a new UUID"
                    )
                    group_id_uuid = uuid.uuid4()
                original_memory_ids_str = [str(mid) for mid in memory_ids]
                suggested_keywords_str = [str(kw) for kw in group.get("suggested_keywords", [])]

                suggestion_data = {
                    "group_id": group_id_uuid,
                    "suggested_content": group.get("suggested_content", ""),
                    "suggested_lessons_learned": group.get("suggested_lessons_learned", ""),
                    "suggested_keywords": suggested_keywords_str,
                    "original_memory_ids": original_memory_ids_str,
                    "status": "pending",
                }
                try:
                    from core.db.schemas import ConsolidationSuggestionCreate

                    suggestion_schema = ConsolidationSuggestionCreate(**suggestion_data)
                    create_consolidation_suggestion(db, suggestion_schema)
                    created_count += 1
                except Exception as inner_e:
                    logger.error(
                        f"Inner error during suggestion creation for group {group_id_uuid}: {str(inner_e)}"
                    )
            except ValueError as ve:
                logger.error(
                    f"UUID conversion error for group {group.get('group_id', 'unknown')}: {str(ve)}"
                )
        except Exception as e:
            logger.error(
                f"Error storing suggestion for group {group.get('group_id', 'unknown')}: {str(e)}"
            )
    db.commit()
    return created_count


def run_consolidation_analysis(llm_api_key: str):
    """Wrapper that uses shim-level get_db and functions so test patches apply."""
    logger.info("Starting memory block consolidation analysis")
    total_blocks_processed = 0
    total_suggestions_created = 0
    offset = 0

    db = next(get_db())
    try:
        while True:
            memory_blocks = fetch_memory_blocks(db, offset, 100)
            if not memory_blocks:
                break
            total_blocks_processed += len(memory_blocks)
            duplicate_groups = analyze_duplicates_with_llm(memory_blocks, llm_api_key)
            suggestions_created = store_consolidation_suggestions(db, duplicate_groups)
            total_suggestions_created += suggestions_created
            offset += 100
            if len(memory_blocks) < 100:
                break
    except Exception as e:
        logger.error(f"Consolidation analysis failed: {str(e)}")
    finally:
        db.close()
        logger.info(
            f"Completed consolidation analysis. Total blocks processed: {total_blocks_processed}, "
            f"Total suggestions created: {total_suggestions_created}"
        )


def analyze_duplicates_with_llm(memory_blocks: List[Dict[str, Any]], llm_api_key: str) -> List[Dict[str, Any]]:
    """Wrapper that uses shim-level fallback for patch compatibility and mirrors worker behavior."""
    if not memory_blocks:
        logger.warning("No memory blocks to analyze")
        return []
    logger.info("Identifying potential duplicate groups using scikit-learn based similarity analysis")
    duplicate_groups = analyze_duplicates_with_fallback(memory_blocks)
    logger.info(
        f"Scikit-learn similarity analysis identified {len(duplicate_groups)} potential duplicate groups"
    )
    if not duplicate_groups:
        logger.info("No potential duplicate groups identified, skipping LLM consolidation")
        return []
    try:
        from google import genai
        client = genai.Client(api_key=llm_api_key)
        model_name = os.getenv("LLM_MODEL_NAME")
        if not model_name:
            error_msg = (
                "LLM_MODEL_NAME environment variable not provided. A valid model name is required for Gemini API requests."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)
        enriched_groups: List[Dict[str, Any]] = []
        for group in duplicate_groups:
            group_id = group.get("group_id", str(uuid.uuid4()))
            memory_ids = group.get("memory_ids", [])
            group_blocks = [block for block in memory_blocks if str(block["id"]) in memory_ids]
            blocks_data = [
                {
                    "id": str(block["id"]),
                    "content": block.get("content", ""),
                    "lessons_learned": block.get("lessons_learned", ""),
                    "keywords": [
                        kw.get("keyword_text") if isinstance(kw, dict) else getattr(kw, "keyword_text", None)
                        for kw in (block.get("keywords") or [])
                    ],
                }
                for block in group_blocks
            ]
            prompt = (
                "Generate consolidated content, lessons learned, and keywords for the following group of memory blocks.\n"
                "Return only a JSON object with the following structure:\n\n"
                "{\n"
                "  \"suggested_content\": \"...\",\n"
                "  \"suggested_lessons_learned\": \"...\",\n"
                "  \"suggested_keywords\": [\"kw1\", \"kw2\"]\n"
                "}\n\n"
                "Analyze the following memory blocks to generate consolidated suggestions:\n"
            ) + json.dumps(blocks_data, indent=2)
            logger.info(
                f"Prompt length for Gemini API request for group {group_id}: {len(prompt)} characters"
            )
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json", "temperature": 0.3},
                )
                result_text = response.text if response.text else "{}"
                try:
                    suggestion_data = json.loads(result_text)
                    suggested_content = suggestion_data.get("suggested_content", "")
                    suggested_lessons = suggestion_data.get("suggested_lessons_learned", "")
                    max_content_length = max(len(block.get("content", "")) for block in group_blocks) if group_blocks else 0
                    max_lessons_length = max(len(block.get("lessons_learned", "")) for block in group_blocks) if group_blocks else 0
                    if max_content_length and len(suggested_content) > max_content_length:
                        suggested_content = suggested_content[:max_content_length]
                    if max_lessons_length and len(suggested_lessons) > max_lessons_length:
                        suggested_lessons = suggested_lessons[:max_lessons_length]
                    enriched_groups.append(
                        {
                            "group_id": group_id,
                            "memory_ids": memory_ids,
                            "suggested_content": suggested_content,
                            "suggested_lessons_learned": suggested_lessons,
                            "suggested_keywords": suggestion_data.get("suggested_keywords", []),
                        }
                    )
                except json.JSONDecodeError:
                    logger.error(
                        f"Failed to parse Gemini response as JSON for group {group_id}, keeping original group data"
                    )
                    enriched_groups.append(group)
            except Exception as model_error:
                error_msg = (
                    f"Failed to use model {model_name} for group {group_id}. Error: {str(model_error)}"
                )
                logger.error(error_msg)
                enriched_groups.append(group)
                raise ValueError(error_msg) from model_error
        logger.info(f"Completed LLM consolidation for {len(enriched_groups)} groups")
        return enriched_groups
    except Exception as e:
        logger.error(
            f"Gemini API request failed: {str(e)}. Returning groups without LLM suggestions."
        )
        return duplicate_groups
    
if __name__ == "__main__":
    import os
    import logging
    logger = logging.getLogger(__name__)
    llm_api_key_from_env = os.getenv("LLM_API_KEY", "")
    if not llm_api_key_from_env:
        logger.warning(
            "LLM_API_KEY not set in environment for direct worker execution. LLM-based consolidation will not occur."
        )
    run_consolidation_analysis(llm_api_key_from_env)

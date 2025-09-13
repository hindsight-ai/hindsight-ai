"""
Consolidation Worker for Hindsight AI

This script runs as a background process to analyze memory blocks for duplicates
and generate consolidation suggestions using an LLM-based approach. It retrieves
memory blocks from the database in batches, processes them to identify duplicate
groups, and stores suggestions for consolidation in the database.

Usage:
    python -m core.workers.consolidation_worker

Configuration:
    - BATCH_SIZE: Number of memory blocks to process in each batch (default: 100)
    - FREQUENCY: How often the worker runs (configured via cron or environment variable)
    - LLM_API_KEY: API key for accessing the LLM service (set via environment variable)
"""

import os
import json
import logging
import uuid
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import requests
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from core.db.database import get_db
from core.db.crud import get_all_memory_blocks, create_consolidation_suggestion

# Configure logging
log_dir = "logs"
log_file = os.path.join(log_dir, "hindsight_consolidation.log")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration settings
BATCH_SIZE = int(os.getenv("CONSOLIDATION_BATCH_SIZE", 100))
FALLBACK_SIMILARITY_THRESHOLD = float(os.getenv("FALLBACK_SIMILARITY_THRESHOLD", 0.4)) # Lowered further for testing

def fetch_memory_blocks(db: Session, offset: int, limit: int) -> List[Dict[str, Any]]:
    """
    Retrieve a batch of memory blocks from the database with pagination.
    This function ensures efficient data retrieval for large datasets.
    
    Args:
        db: Database session
        offset: Starting index for the batch
        limit: Number of records to retrieve
        
    Returns:
        List of memory block dictionaries
    """
    try:
        # Retrieve memory blocks with pagination
        memory_blocks = get_all_memory_blocks(db, skip=offset, limit=limit)
        logger.info(f"Fetched batch of {len(memory_blocks)} memory blocks (offset: {offset})")
        if memory_blocks:
            return [mb.__dict__ for mb in memory_blocks]
        else:
            logger.info("No memory blocks retrieved in this batch")
            return []
    except Exception as e:
        logger.error(f"Error fetching memory blocks: {str(e)}")
        return []

def analyze_duplicates_with_llm(memory_blocks: List[Dict[str, Any]], llm_api_key: str) -> List[Dict[str, Any]]:
    """
    Use an LLM (Gemini model) to generate consolidation suggestions for pre-identified duplicate groups.
    First, identify duplicate groups using a fallback method (scikit-learn), then use the LLM to suggest
    consolidated content for those groups.
    
    Args:
        memory_blocks: List of memory block dictionaries to analyze
        llm_api_key: The API key for the LLM service.
        
    Returns:
        List of duplicate group dictionaries with suggested consolidations
    """
    if not memory_blocks:
        logger.warning("No memory blocks to analyze")
        return []
    
    # Step 1: Identify potential duplicate groups using scikit-learn
    logger.info("Identifying potential duplicate groups using scikit-learn based similarity analysis")
    duplicate_groups = analyze_duplicates_with_fallback(memory_blocks)
    logger.info(f"Scikit-learn similarity analysis identified {len(duplicate_groups)} potential duplicate groups")
    
    if not duplicate_groups:
        logger.info("No potential duplicate groups identified, skipping LLM consolidation")
        return []
    
    # The LLM API key is expected to be valid here. If not, the genai.Client initialization will raise an error.
    try:
        from google import genai
        
        # Initialize the Gemini client with API key
        client = genai.Client(api_key=llm_api_key)
        
        # Step 2: Use LLM to generate consolidation suggestions for each identified group
        model_name = os.getenv("LLM_MODEL_NAME")
        if not model_name:
            error_msg = "LLM_MODEL_NAME environment variable not provided. A valid model name is required for Gemini API requests."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Using LLM to generate consolidation suggestions for {len(duplicate_groups)} groups with model: {model_name}")
        enriched_groups = []
        
        for group in duplicate_groups:
            group_id = group.get("group_id", str(uuid.uuid4()))
            memory_ids = group.get("memory_ids", [])
            
            # Prepare data for LLM analysis for this specific group
            group_blocks = [block for block in memory_blocks if str(block["id"]) in memory_ids]
            blocks_data = [
                {
                    "id": str(block["id"]),
                    "content": block.get("content", ""),
                    "lessons_learned": block.get("lessons_learned", ""),
                    "keywords": [kw.get("keyword_text") if isinstance(kw, dict) else getattr(kw, "keyword_text", None) for kw in (block.get("keywords") or [])]
                }
                for block in group_blocks
            ]
            
            # Create a prompt for the LLM with a proper JSON structure
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
            
            logger.info(f"Prompt length for Gemini API request for group {group_id}: {len(prompt)} characters")
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "response_mime_type": "application/json",
                        "temperature": 0.3
                    }
                )
                
                # Extract the response content
                result_text = response.text if response.text else "{}"
                try:
                    suggestion_data = json.loads(result_text)
                    suggested_content = suggestion_data.get("suggested_content", "")
                    suggested_lessons = suggestion_data.get("suggested_lessons_learned", "")
                    
                    # Calculate max length of content and lessons learned in the group
                    max_content_length = max(len(block.get("content", "")) for block in group_blocks)
                    max_lessons_length = max(len(block.get("lessons_learned", "")) for block in group_blocks)
                    
                    # Assert that suggestions do not exceed max lengths
                    if len(suggested_content) > max_content_length:
                        logger.warning(f"Suggested content for group {group_id} exceeds max content length ({len(suggested_content)} > {max_content_length}), trimming")
                        suggested_content = suggested_content[:max_content_length]
                    if len(suggested_lessons) > max_lessons_length:
                        logger.warning(f"Suggested lessons for group {group_id} exceeds max lessons length ({len(suggested_lessons)} > {max_lessons_length}), trimming")
                        suggested_lessons = suggested_lessons[:max_lessons_length]
                    
                    enriched_group = {
                        "group_id": group_id,
                        "memory_ids": memory_ids,
                        "suggested_content": suggested_content,
                        "suggested_lessons_learned": suggested_lessons,
                        "suggested_keywords": suggestion_data.get("suggested_keywords", [])
                    }
                    enriched_groups.append(enriched_group)
                    logger.info(f"Generated consolidation suggestions for group {group_id}")
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse Gemini response as JSON for group {group_id}, keeping original group data")
                    enriched_groups.append(group)
            except Exception as model_error:
                error_msg = f"Failed to use model {model_name} for group {group_id}. Error: {str(model_error)}"
                logger.error(error_msg)
                enriched_groups.append(group)
                raise ValueError(error_msg) from model_error
        
        logger.info(f"Completed LLM consolidation for {len(enriched_groups)} groups")
        return enriched_groups
    except Exception as e:
        logger.error(f"Gemini API request failed: {str(e)}. Returning groups without LLM suggestions.")
        return duplicate_groups

def analyze_duplicates_with_fallback(memory_blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Fallback method to identify duplicates using basic text similarity (TF-IDF + cosine similarity).
    
    Args:
        memory_blocks: List of memory block dictionaries to analyze
        
    Returns:
        List of duplicate group dictionaries with suggested consolidations
    """
    if len(memory_blocks) < 2:
        return []
    
    # Combine content and lessons learned for similarity analysis
    texts = [f"{block.get('content', '')} {block.get('lessons_learned', '')}" for block in memory_blocks]
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    similarity_matrix = cosine_similarity(tfidf_matrix)
    
    # Group similar blocks based on threshold
    groups = []
    used = set()
    for i in range(len(memory_blocks)):
        if i in used:
            continue
        current_group = {"group_id": str(uuid.uuid4()), "memory_ids": [str(memory_blocks[i]["id"]) ]}
        for j in range(i + 1, len(memory_blocks)):
            if j not in used and similarity_matrix[i][j] >= FALLBACK_SIMILARITY_THRESHOLD:
                current_group["memory_ids"].append(str(memory_blocks[j]["id"]))
                used.add(j)
        if len(current_group["memory_ids"]) > 1:  # Only consider groups with duplicates
            # Fallback method only identifies groups, it does not generate consolidated content.
            # The LLM is mandatory for generating suggestions.
            groups.append(current_group)
        used.add(i)
    
    logger.info(f"Scikit-learn similarity analysis identified {len(groups)} potential duplicate groups")
    return groups

def store_consolidation_suggestions(db: Session, groups: List[Dict[str, Any]]) -> int:
    """
    Store consolidation suggestions in the database for identified duplicate groups.
    This function checks for existing pending suggestions with overlapping memory IDs
    to avoid creating duplicate suggestions.
    
    Args:
        db: Database session
        groups: List of duplicate group dictionaries with consolidation suggestions
        
    Returns:
        Number of new suggestions created
    """
    from sqlalchemy import and_
    from core.db.models import ConsolidationSuggestion
    
    created_count = 0
    for group in groups:
        # Only process groups that have LLM-generated suggestions
        if not group.get("suggested_content") or not group.get("suggested_lessons_learned"):
            logger.info(f"Skipping group {group.get('group_id', 'unknown')} as it lacks LLM-generated content/lessons learned.")
            continue
        try:
            logger.info(f"Processing group: {group}")
            # Convert memory IDs to a sorted list of strings for comparison
            memory_ids = sorted(group.get("memory_ids", []))
            logger.info(f"Extracted memory_ids: {memory_ids}")
            
            # Query for existing pending suggestions with overlapping memory IDs
            existing_suggestions = db.query(ConsolidationSuggestion).filter(
                ConsolidationSuggestion.status == "pending"
            ).all()
            
            # Check for overlap manually since overlap method might not be available
            has_overlap = False
            for suggestion in existing_suggestions:
                existing_ids = set(suggestion.original_memory_ids or [])
                current_ids = set(memory_ids)
                if existing_ids & current_ids:  # Check for intersection
                    has_overlap = True
                    break
            
            if has_overlap:
                group_id = group.get('group_id', 'unknown')
                logger.info(f"Skipping group {group_id} due to existing pending suggestion(s) with overlapping memory IDs")
                continue
            
            # If no overlapping suggestions found, create a new one
            try:
                group_id_str = group.get("group_id", str(uuid.uuid4()))
                try:
                    group_id_uuid = uuid.UUID(group_id_str) if isinstance(group_id_str, str) else group_id_str
                except ValueError:
                    logger.warning(f"Invalid UUID format for group_id {group_id_str}, generating a new UUID")
                    group_id_uuid = uuid.uuid4()
                # Ensure original_memory_ids are strings for JSONB serialization
                original_memory_ids_str = [str(mid) for mid in memory_ids]
                # Ensure suggested_keywords are strings
                suggested_keywords_str = [str(kw) for kw in group.get("suggested_keywords", [])]

                suggestion_data = {
                    "group_id": group_id_uuid,
                    "suggested_content": group.get("suggested_content", ""),
                    "suggested_lessons_learned": group.get("suggested_lessons_learned", ""),
                    "suggested_keywords": suggested_keywords_str,
                    "original_memory_ids": original_memory_ids_str,
                    "status": "pending"
                }
                logger.info(f"Attempting to create suggestion with data: {suggestion_data}")
                try:
                    from core.db.schemas import ConsolidationSuggestionCreate
                    suggestion_schema = ConsolidationSuggestionCreate(**suggestion_data)
                    create_consolidation_suggestion(db, suggestion_schema)
                    created_count += 1
                    logger.info(f"Created consolidation suggestion for group {group_id_uuid} with {len(memory_ids)} memory blocks")
                except Exception as inner_e:
                    logger.error(f"Inner error during suggestion creation for group {group_id_uuid}: {str(inner_e)}")
                    logger.error(f"Full suggestion data: {suggestion_data}")
            except ValueError as ve:
                logger.error(f"UUID conversion error for group {group.get('group_id', 'unknown')}: {str(ve)}")
                logger.error(f"Full group structure: {group}")
        except Exception as e:
            logger.error(f"Error storing suggestion for group {group.get('group_id', 'unknown')}: {str(e)}")
            logger.error(f"Full group structure: {group}")
    
    db.commit()
    logger.info(f"Stored {created_count} new consolidation suggestions")
    return created_count

def run_consolidation_analysis(llm_api_key: str):
    """
    Main function to run the consolidation analysis process.
    Retrieves memory blocks in batches, analyzes for duplicates, and stores suggestions.
    
    Args:
        llm_api_key: The API key for the LLM service.
    """
    logger.info("Starting memory block consolidation analysis")
    total_blocks_processed = 0
    total_suggestions_created = 0
    offset = 0
    
    db = next(get_db())
    try:
        while True:
            memory_blocks = fetch_memory_blocks(db, offset, BATCH_SIZE)
            if not memory_blocks:
                break
                
            total_blocks_processed += len(memory_blocks)
            duplicate_groups = analyze_duplicates_with_llm(memory_blocks, llm_api_key)
            suggestions_created = store_consolidation_suggestions(db, duplicate_groups)
            total_suggestions_created += suggestions_created
            
            offset += BATCH_SIZE
            logger.info(f"Processed {total_blocks_processed} memory blocks, created {total_suggestions_created} suggestions so far")
            
            # Break if we received less than BATCH_SIZE, indicating end of data
            if len(memory_blocks) < BATCH_SIZE:
                break
                
    except Exception as e:
        logger.error(f"Consolidation analysis failed: {str(e)}")
    finally:
        db.close()
        logger.info(f"Completed consolidation analysis. Total blocks processed: {total_blocks_processed}, Total suggestions created: {total_suggestions_created}")

if __name__ == "__main__":
    # This block is for direct execution of the worker, e.g., via a cron job.
    # In this case, LLM_API_KEY must be set in the environment where the script is run.
    # For FastAPI integration, the LLM_API_KEY is passed from main.py.
    llm_api_key_from_env = os.getenv("LLM_API_KEY", "")
    if not llm_api_key_from_env:
        logger.warning("LLM_API_KEY not set in environment for direct worker execution. LLM-based consolidation will not occur.")
    run_consolidation_analysis(llm_api_key_from_env)

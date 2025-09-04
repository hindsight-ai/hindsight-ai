from sqlalchemy.orm import Session, joinedload # Import joinedload
from . import models, schemas
import uuid
from datetime import datetime, timezone
from sqlalchemy import or_, func # Import func
from typing import List, Optional

# CRUD for Agent
def create_agent(db: Session, agent: schemas.AgentCreate):
    db_agent = models.Agent(agent_name=agent.agent_name)
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def get_agent(db: Session, agent_id: uuid.UUID):
    return db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()

def get_agent_by_name(db: Session, agent_name: str):
    return db.query(models.Agent).filter(models.Agent.agent_name == agent_name).first()

def get_agents(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Agent).offset(skip).limit(limit).all()

def search_agents(db: Session, query: str, skip: int = 0, limit: int = 100):
    # Use pg_trgm's similarity for fuzzy matching
    # A similarity threshold of 0.3 is a common starting point, adjust as needed
    SIMILARITY_THRESHOLD = 0.3
    return db.query(models.Agent).filter(
        func.similarity(models.Agent.agent_name, query) >= SIMILARITY_THRESHOLD
    ).order_by(
        func.similarity(models.Agent.agent_name, query).desc() # Order by similarity score
    ).offset(skip).limit(limit).all()

def update_agent(db: Session, agent_id: uuid.UUID, agent: schemas.AgentUpdate):
    db_agent = db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()
    if db_agent:
        for key, value in agent.dict(exclude_unset=True).items():
            setattr(db_agent, key, value)
        db.commit()
        db.refresh(db_agent)
    return db_agent

def delete_agent(db: Session, agent_id: uuid.UUID):
    db_agent = db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()
    if db_agent:
        # Delete associated AgentTranscript records
        db.query(models.AgentTranscript).filter(models.AgentTranscript.agent_id == agent_id).delete(synchronize_session=False)
        
        # Delete associated MemoryBlock records
        db.query(models.MemoryBlock).filter(models.MemoryBlock.agent_id == agent_id).delete(synchronize_session=False)
        
        # Now delete the agent
        db.delete(db_agent)
        db.commit()
        return True # Indicate successful deletion
    return False # Indicate agent not found or deletion failed

# CRUD for AgentTranscript
def create_agent_transcript(db: Session, transcript: schemas.AgentTranscriptCreate):
    db_transcript = models.AgentTranscript(
        agent_id=transcript.agent_id,
        conversation_id=transcript.conversation_id,
        transcript_content=transcript.transcript_content
    )
    db.add(db_transcript)
    db.commit()
    db.refresh(db_transcript)
    return db_transcript

def get_agent_transcript(db: Session, transcript_id: uuid.UUID):
    return db.query(models.AgentTranscript).filter(models.AgentTranscript.transcript_id == transcript_id).first()

def get_agent_transcripts_by_agent(db: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.AgentTranscript).filter(models.AgentTranscript.agent_id == agent_id).offset(skip).limit(limit).all()

def get_agent_transcripts_by_conversation(db: Session, conversation_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.AgentTranscript).filter(models.AgentTranscript.conversation_id == conversation_id).offset(skip).limit(limit).all()

def update_agent_transcript(db: Session, transcript_id: uuid.UUID, transcript: schemas.AgentTranscriptUpdate):
    db_transcript = db.query(models.AgentTranscript).filter(models.AgentTranscript.transcript_id == transcript_id).first()
    if db_transcript:
        for key, value in transcript.dict(exclude_unset=True).items():
            setattr(db_transcript, key, value)
        db.commit()
        db.refresh(db_transcript)
    return db_transcript

def delete_agent_transcript(db: Session, transcript_id: uuid.UUID):
    db_transcript = db.query(models.AgentTranscript).filter(models.AgentTranscript.transcript_id == transcript_id).first()
    if db_transcript:
        db.delete(db_transcript)
        db.commit()
    return db_transcript

# CRUD for Keyword
def create_keyword(db: Session, keyword: schemas.KeywordCreate):
    db_keyword = models.Keyword(keyword_text=keyword.keyword_text)
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

def get_keyword(db: Session, keyword_id: uuid.UUID):
    return db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()

def get_keyword_by_text(db: Session, keyword_text: str):
    return db.query(models.Keyword).filter(models.Keyword.keyword_text == keyword_text).first()

def get_keywords(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Keyword).offset(skip).limit(limit).all()

def update_keyword(db: Session, keyword_id: uuid.UUID, keyword: schemas.KeywordUpdate):
    db_keyword = db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()
    if db_keyword:
        for key, value in keyword.dict(exclude_unset=True).items():
            setattr(db_keyword, key, value)
        db.commit()
        db.refresh(db_keyword)
    return db_keyword

def delete_keyword(db: Session, keyword_id: uuid.UUID):
    db_keyword = db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()
    if db_keyword:
        db.delete(db_keyword)
        db.commit()
    return db_keyword

# CRUD for MemoryBlock
def create_memory_block(db: Session, memory_block: schemas.MemoryBlockCreate):
    db_memory_block = models.MemoryBlock(
        agent_id=memory_block.agent_id,
        conversation_id=memory_block.conversation_id,
        content=memory_block.content,
        errors=memory_block.errors,
        lessons_learned=memory_block.lessons_learned,
        metadata_col=memory_block.metadata_col,
        feedback_score=memory_block.feedback_score or 0  # Default to 0 if not provided
    )
    db.add(db_memory_block)
    db.flush()  # Flush to get memory_id before commit

    # Use NLP-based keyword extraction from core module
    from core.core.keyword_extraction import extract_keywords
    extracted_keywords = set(extract_keywords(memory_block.content))

    # Create associations with keywords
    for keyword_text in extracted_keywords:
        keyword = _get_or_create_keyword(db, keyword_text)
        db_mbk = models.MemoryBlockKeyword(memory_id=db_memory_block.id, keyword_id=keyword.keyword_id)
        db.add(db_mbk)

    # Create initial feedback log entry
    db_feedback_log = models.FeedbackLog(
        memory_id=db_memory_block.id,
        feedback_type='neutral',
        feedback_details='Initial memory creation'
    )
    db.add(db_feedback_log)

    db.commit()
    db.refresh(db_memory_block)
    # Explicitly convert to schema model to ensure proper serialization
    return schemas.MemoryBlock.from_orm(db_memory_block)

def get_memory_block(db: Session, memory_id: uuid.UUID):
    return db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()

def get_memory_blocks_by_agent(db: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.MemoryBlock).filter(models.MemoryBlock.agent_id == agent_id).offset(skip).limit(limit).all()

def get_memory_blocks_by_conversation(db: Session, conversation_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.MemoryBlock).filter(models.MemoryBlock.conversation_id == conversation_id).offset(skip).limit(limit).all()

# CRUD for MemoryBlock
def get_all_memory_blocks(
    db: Session,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    search_query: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_feedback_score: Optional[int] = None,
    max_feedback_score: Optional[int] = None,
    min_retrieval_count: Optional[int] = None,
    max_retrieval_count: Optional[int] = None,
    keyword_ids: Optional[List[uuid.UUID]] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc", # "asc" or "desc"
    skip: int = 0,
    limit: int = 100,
    get_total: bool = False, # New parameter to indicate if total count is needed
    include_archived: bool = False, # New parameter to include archived blocks
    is_archived: Optional[bool] = None # New parameter to explicitly filter by archived status
):
    query = db.query(models.MemoryBlock).options(joinedload(models.MemoryBlock.memory_block_keywords).joinedload(models.MemoryBlockKeyword.keyword)) # Eager load keywords

    if is_archived is not None:
        query = query.filter(models.MemoryBlock.archived == is_archived)
    elif not include_archived: # Only apply this filter if is_archived is not explicitly set
        query = query.filter(models.MemoryBlock.archived == False)

    if agent_id:
        query = query.filter(models.MemoryBlock.agent_id == agent_id)
    if conversation_id:
        query = query.filter(models.MemoryBlock.conversation_id == conversation_id)
    
    if search_query:
        search_pattern = f"%{search_query}%"
        query = query.filter(
            or_(
                models.MemoryBlock.id.cast(str).ilike(search_pattern), # Search UUID as string
                models.MemoryBlock.content.ilike(search_pattern),
                models.MemoryBlock.errors.ilike(search_pattern),
                models.MemoryBlock.lessons_learned.ilike(search_pattern),
                # models.MemoryBlock.external_history_link.ilike(search_pattern),  # Removed: column does not exist
                # Searching JSON metadata requires casting to text
                models.MemoryBlock.metadata_col.cast(str).ilike(search_pattern),
                models.MemoryBlock.agent_id.cast(str).ilike(search_pattern), # Search agent_id as string
                models.MemoryBlock.conversation_id.cast(str).ilike(search_pattern) # Search conversation_id as string
            )
        )

    if start_date:
        query = query.filter(models.MemoryBlock.created_at >= start_date)
    if end_date:
        query = query.filter(models.MemoryBlock.created_at <= end_date)

    if min_feedback_score is not None:
        query = query.filter(models.MemoryBlock.feedback_score >= min_feedback_score)
    if max_feedback_score is not None:
        query = query.filter(models.MemoryBlock.feedback_score <= max_feedback_score)

    if min_retrieval_count is not None:
        query = query.filter(models.MemoryBlock.retrieval_count >= min_retrieval_count)
    if max_retrieval_count is not None:
        query = query.filter(models.MemoryBlock.retrieval_count <= max_retrieval_count)

    if keyword_ids:
        query = query.join(models.MemoryBlockKeyword).filter(models.MemoryBlockKeyword.keyword_id.in_(keyword_ids))

    # Get total count before applying limit and offset
    total_count = query.count()

    if sort_by:
        if sort_by == "creation_date":
            order_column = models.MemoryBlock.created_at
        elif sort_by == "feedback_score":
            order_column = models.MemoryBlock.feedback_score
        elif sort_by == "retrieval_count":
            order_column = models.MemoryBlock.retrieval_count
        elif sort_by == "id":
            order_column = models.MemoryBlock.id
        else:
            order_column = models.MemoryBlock.created_at # Default sort

        if sort_order == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())
    else:
        query = query.order_by(models.MemoryBlock.created_at.desc()) # Default sort

    memories = query.offset(skip).limit(limit).all()

    if get_total:
        return memories, total_count
    else:
        return memories

def update_memory_block(db: Session, memory_id: uuid.UUID, memory_block: schemas.MemoryBlockUpdate):
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        update_data = memory_block.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_memory_block, key, value)
        db.commit()
        db.refresh(db_memory_block)
    return db_memory_block

import logging # Added to top of file

logger = logging.getLogger(__name__) # Added to top of file

# ... (rest of the file)

def archive_memory_block(db: Session, memory_id: uuid.UUID):
    logger.info(f"Attempting to archive memory block with ID: {memory_id}")
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        logger.info(f"Memory block {memory_id} found. Setting archived=True and archived_at.")
        db_memory_block.archived = True
        db_memory_block.archived_at = datetime.now(timezone.utc)
        try:
            db.commit()
            db.refresh(db_memory_block)
            logger.info(f"Memory block {memory_id} successfully archived at {db_memory_block.archived_at}.")
            return db_memory_block # Return the updated memory block
        except Exception as e:
            db.rollback()
            logger.error(f"Error archiving memory block {memory_id}: {e}")
            raise # Re-raise the exception to be caught by the API endpoint
    logger.warning(f"Memory block with ID: {memory_id} not found for archiving.")
    return None # Return None if not found

def delete_memory_block(db: Session, memory_id: uuid.UUID):
    # This function now performs a hard delete, used for actual removal, not archiving
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        db.delete(db_memory_block)
        db.commit()
        return True
    return False

def retrieve_relevant_memories(
    db: Session,
    keywords: List[str],
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 100
):
    # This function is for agent-facing semantic search, not for the dashboard's simple search.
    # It will remain as a keyword-based search for now as per the plan,
    # with a note that complex logic will be implemented later.
    query = db.query(models.MemoryBlock)

    if agent_id:
        query = query.filter(models.MemoryBlock.agent_id == agent_id)
    if conversation_id:
        query = query.filter(models.MemoryBlock.conversation_id == conversation_id)

    # Simple keyword-based search across content, errors, and lessons_learned
    search_filters = []
    for keyword in keywords:
        search_filters.append(models.MemoryBlock.content.ilike(f"%{keyword}%"))
        search_filters.append(models.MemoryBlock.errors.ilike(f"%{keyword}%"))
        search_filters.append(models.MemoryBlock.lessons_learned.ilike(f"%{keyword}%"))
    
    if search_filters:
        query = query.filter(or_(*search_filters))

    return query.limit(limit).all()

def report_memory_feedback(db: Session, memory_id: uuid.UUID, feedback_type: str, feedback_details: Optional[str] = None):
    # Record feedback in feedback_logs
    feedback_log_create = schemas.FeedbackLogCreate(
        memory_id=memory_id,
        feedback_type=feedback_type,
        feedback_details=feedback_details
    )
    create_feedback_log(db, feedback_log_create)

    # Update feedback_score for the associated memory_block
    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
    if db_memory_block:
        if feedback_type == 'positive':
            db_memory_block.feedback_score += 1
        elif feedback_type == 'negative':
            db_memory_block.feedback_score -= 1
        # 'neutral' doesn't change the score
        db.commit()
        db.refresh(db_memory_block)
    return db_memory_block

# CRUD for FeedbackLog
def create_feedback_log(db: Session, feedback_log: schemas.FeedbackLogCreate):
    db_feedback_log = models.FeedbackLog(
        memory_id=feedback_log.memory_id, # This will be fixed in schemas.py
        feedback_type=feedback_log.feedback_type,
        feedback_details=feedback_log.feedback_details
    )
    db.add(db_feedback_log)
    db.commit()
    db.refresh(db_feedback_log)
    return db_feedback_log

def get_feedback_log(db: Session, feedback_id: uuid.UUID):
    return db.query(models.FeedbackLog).filter(models.FeedbackLog.feedback_id == feedback_id).first()

def get_feedback_logs_by_memory_block(db: Session, memory_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.FeedbackLog).filter(models.FeedbackLog.memory_id == memory_id).offset(skip).limit(limit).all()

def update_feedback_log(db: Session, feedback_id: uuid.UUID, feedback_log: schemas.FeedbackLogUpdate):
    db_feedback_log = db.query(models.FeedbackLog).filter(models.FeedbackLog.feedback_id == feedback_id).first()
    if db_feedback_log:
        for key, value in feedback_log.dict(exclude_unset=True).items():
            setattr(db_feedback_log, key, value)
        db.commit()
        db.refresh(db_feedback_log)
    return db_feedback_log

def delete_feedback_log(db: Session, feedback_id: uuid.UUID):
    db_feedback_log = db.query(models.FeedbackLog).filter(models.FeedbackLog.feedback_id == feedback_id).first()
    if db_feedback_log:
        db.delete(db_feedback_log)
        db.commit()
    return db_feedback_log

def _get_or_create_keyword(db: Session, keyword_text: str):
    # Remove leading/trailing whitespace and then trailing periods from the keyword text
    processed_keyword_text = keyword_text.strip().rstrip('.')
    
    keyword = db.query(models.Keyword).filter(models.Keyword.keyword_text == processed_keyword_text).first()
    if not keyword:
        keyword = models.Keyword(keyword_text=processed_keyword_text)
        db.add(keyword)
        db.flush()  # Use flush to get the ID before commit
    return keyword

# CRUD for MemoryBlockKeyword (Association Table)
def create_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    db_mbk = models.MemoryBlockKeyword(memory_id=memory_id, keyword_id=keyword_id)
    db.add(db_mbk)
    db.commit()
    db.refresh(db_mbk)
    return db_mbk

def delete_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    db_mbk = db.query(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.memory_id == memory_id,
        models.MemoryBlockKeyword.keyword_id == keyword_id
    ).first()
    if db_mbk:
        db.delete(db_mbk)
        db.commit()
    return db_mbk

def get_memory_block_keywords(db: Session, memory_id: uuid.UUID):
    return db.query(models.Keyword).join(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.memory_id == memory_id
    ).all()


# CRUD for ConsolidationSuggestion
def create_consolidation_suggestion(db: Session, suggestion: schemas.ConsolidationSuggestionCreate):
    db_suggestion = models.ConsolidationSuggestion(
        group_id=suggestion.group_id,
        suggested_content=suggestion.suggested_content,
        suggested_lessons_learned=suggestion.suggested_lessons_learned,
        suggested_keywords=suggestion.suggested_keywords,
        original_memory_ids=suggestion.original_memory_ids,
        status=suggestion.status or 'pending'
    )
    db.add(db_suggestion)
    db.commit()
    db.refresh(db_suggestion)
    return db_suggestion

def get_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID):
    return db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()

def get_consolidation_suggestions(db: Session, status: Optional[str] = None, group_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.ConsolidationSuggestion)
    if status: # Only filter if status is provided (not None or empty string)
        query = query.filter(models.ConsolidationSuggestion.status == status)
    if group_id:
        query = query.filter(models.ConsolidationSuggestion.group_id == group_id)
    
    total_items = query.count() # Get total count before applying limit and offset
    suggestions = query.offset(skip).limit(limit).all()
    
    return suggestions, total_items

def update_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID, suggestion: schemas.ConsolidationSuggestionUpdate):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion:
        update_data = suggestion.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_suggestion, key, value)
        db.commit()
        db.refresh(db_suggestion)
    return db_suggestion

def delete_consolidation_suggestion(db: Session, suggestion_id: uuid.UUID):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion:
        db.delete(db_suggestion)
        db.commit()
        return True
    return False

def apply_consolidation(db: Session, suggestion_id: uuid.UUID):
    db_suggestion = db.query(models.ConsolidationSuggestion).filter(models.ConsolidationSuggestion.suggestion_id == suggestion_id).first()
    if db_suggestion and db_suggestion.status == 'pending':
        # Create a new MemoryBlock with the consolidated content
        original_memory_ids = db_suggestion.original_memory_ids
        if original_memory_ids:
            first_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == original_memory_ids[0]).first()
            if first_memory_block:
                new_memory_block = models.MemoryBlock(
                    agent_id=first_memory_block.agent_id,
                    conversation_id=first_memory_block.conversation_id,
                    content=db_suggestion.suggested_content,
                    lessons_learned=db_suggestion.suggested_lessons_learned,
                    metadata_col={"consolidated_from": original_memory_ids}
                )
                db.add(new_memory_block)
                db.flush()

                # Add keywords to the new memory block
                for keyword_text in db_suggestion.suggested_keywords:
                    keyword = _get_or_create_keyword(db, keyword_text)
                    db_mbk = models.MemoryBlockKeyword(memory_id=new_memory_block.id, keyword_id=keyword.keyword_id)
                    db.add(db_mbk)

                # Archive original memory blocks instead of deleting them
                for memory_id in original_memory_ids:
                    db_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == memory_id).first()
                    if db_memory_block:
                        db_memory_block.archived = True # Set archived to True
                        db_memory_block.archived_at = datetime.now(timezone.utc) # Set archived timestamp
                        db.add(db_memory_block) # Re-add to session to mark as dirty

                # Update suggestion status
                db_suggestion.status = 'validated'
                db.commit()
                db.refresh(new_memory_block)
                return new_memory_block
    return None

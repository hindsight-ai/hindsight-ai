"""
CRUD operations for ORM models.

Implements scoped queries, fuzzy search, and helpers for agents, memory
blocks, keywords, organizations, audit logs, and bulk operations.
"""
from sqlalchemy.orm import Session, joinedload # Import joinedload
from . import models, schemas, scope_utils
from .repositories import keywords as repo_keywords
from .repositories import agents as repo_agents
from .repositories import organizations as repo_orgs
from .repositories import bulk_ops as repo_bulk
from .repositories import audits as repo_audits
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_, func, Text # Import func, and_, and Text
from .repositories import memory_blocks as repo_memories
from typing import List, Optional
from core.utils.scopes import SCOPE_PERSONAL, SCOPE_ORGANIZATION

# CRUD for BulkOperation (facade delegates to repository)
def create_bulk_operation(
    db: Session,
    bulk_operation: schemas.BulkOperationCreate,
    *,
    actor_user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_bulk.create_bulk_operation(db, bulk_operation, actor_user_id, organization_id)


def get_bulk_operation(db: Session, bulk_operation_id: uuid.UUID):
    return repo_bulk.get_bulk_operation(db, bulk_operation_id)


def get_bulk_operations(
    db: Session,
    *,
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    skip: int = 0,
    limit: int = 100,
):
    return repo_bulk.get_bulk_operations(db, organization_id, user_id, skip, limit)


def update_bulk_operation(
    db: Session, bulk_operation_id: uuid.UUID, bulk_operation: schemas.BulkOperationUpdate
):
    return repo_bulk.update_bulk_operation(db, bulk_operation_id, bulk_operation)

# CRUD for AuditLog (facade delegates to repository)
def create_audit_log(
    db: Session,
    audit_log: schemas.AuditLogCreate,
    *,
    actor_user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_audits.create_audit_log(db, audit_log, actor_user_id, organization_id)


def get_audit_logs(
    db: Session,
    *,
    organization_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    action_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    return repo_audits.get_audit_logs(
        db,
        organization_id=organization_id,
        user_id=user_id,
        action_type=action_type,
        status=status,
        skip=skip,
        limit=limit,
    )

# CRUD for Agent
def create_agent(db: Session, agent: schemas.AgentCreate):
    return repo_agents.create_agent(db, agent)

def get_agent(db: Session, agent_id: uuid.UUID):
    return repo_agents.get_agent(db, agent_id)

def get_agent_by_name(db: Session, agent_name: str, *, visibility_scope: str = None, owner_user_id=None, organization_id=None):
    return repo_agents.get_agent_by_name(
        db,
        agent_name,
        visibility_scope=visibility_scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )

def get_agents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_agents.get_agents(
        db,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
        scope=scope,
        organization_id=organization_id,
    )

def search_agents(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_agents.search_agents(
        db,
        query=query,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
        scope=scope,
        organization_id=organization_id,
    )

def update_agent(db: Session, agent_id: uuid.UUID, agent: schemas.AgentUpdate):
    return repo_agents.update_agent(db, agent_id, agent)

def delete_agent(db: Session, agent_id: uuid.UUID):
    return repo_agents.delete_agent(db, agent_id)

# CRUD for AgentTranscript
def create_agent_transcript(db: Session, transcript: schemas.AgentTranscriptCreate):
    return repo_agents.create_agent_transcript(db, transcript)

def get_agent_transcript(db: Session, transcript_id: uuid.UUID):
    return repo_agents.get_agent_transcript(db, transcript_id)

def get_agent_transcripts_by_agent(db: Session, agent_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return repo_agents.get_agent_transcripts_by_agent(db, agent_id, skip, limit)

def get_agent_transcripts_by_conversation(db: Session, conversation_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return repo_agents.get_agent_transcripts_by_conversation(db, conversation_id, skip, limit)

def update_agent_transcript(db: Session, transcript_id: uuid.UUID, transcript: schemas.AgentTranscriptUpdate):
    return repo_agents.update_agent_transcript(db, transcript_id, transcript)

def delete_agent_transcript(db: Session, transcript_id: uuid.UUID):
    return repo_agents.delete_agent_transcript(db, transcript_id)

# CRUD for Keyword
def create_keyword(db: Session, keyword: schemas.KeywordCreate):
    return repo_keywords.create_keyword(db, keyword)

def get_keyword(db: Session, keyword_id: uuid.UUID):
    return repo_keywords.get_keyword(db, keyword_id)

def get_keyword_by_text(db: Session, keyword_text: str):
    return repo_keywords.get_keyword_by_text(db, keyword_text)

def get_scoped_keyword_by_text(
    db: Session,
    keyword_text: str,
    *,
    visibility_scope: str,
    owner_user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_keywords.get_scoped_keyword_by_text(
        db,
        keyword_text,
        visibility_scope=visibility_scope,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
    )

def get_keywords(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    return repo_keywords.get_keywords(
        db,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
        scope=scope,
        organization_id=organization_id,
    )

def update_keyword(db: Session, keyword_id: uuid.UUID, keyword: schemas.KeywordUpdate):
    return repo_keywords.update_keyword(db, keyword_id, keyword)

def delete_keyword(db: Session, keyword_id: uuid.UUID):
    return repo_keywords.delete_keyword(db, keyword_id)

# CRUD for MemoryBlock
def create_memory_block(db: Session, memory_block: schemas.MemoryBlockCreate):
    """Delegate creation to the memory blocks repository.

    This preserves the `crud` facade while using the canonical implementation
    in `repositories/memory_blocks.py` where keyword extraction and
    associations live.
    """
    return repo_memories.create_memory_block(db, memory_block)

def get_memory_block(db: Session, memory_id: uuid.UUID):
    return repo_memories.get_memory_block(db, memory_id)

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
    is_archived: Optional[bool] = None, # New parameter to explicitly filter by archived status
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
    filter_scope: Optional[str] = None,
    filter_organization_id: Optional[uuid.UUID] = None,
):
    return repo_memories.get_all_memory_blocks(
        db,
        agent_id,
        conversation_id,
        search_query,
        start_date,
        end_date,
        min_feedback_score,
        max_feedback_score,
        min_retrieval_count,
        max_retrieval_count,
        keyword_ids,
        sort_by,
        sort_order,
        skip,
        limit,
        get_total,
        include_archived,
        is_archived,
        current_user,
        scope_ctx,
        filter_scope,
        filter_organization_id,
    )

def update_memory_block(db: Session, memory_id: uuid.UUID, memory_block: schemas.MemoryBlockUpdate):
    return repo_memories.update_memory_block(db, memory_id, memory_block)

import logging # Added to top of file

logger = logging.getLogger(__name__) # Added to top of file

# ... (rest of the file)

def archive_memory_block(db: Session, memory_id: uuid.UUID):
    return repo_memories.archive_memory_block(db, memory_id)

def delete_memory_block(db: Session, memory_id: uuid.UUID):
    return repo_memories.delete_memory_block(db, memory_id)

def retrieve_relevant_memories(
    db: Session,
    keywords: List[str],
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 100
):
    return repo_memories.retrieve_relevant_memories(db, keywords, agent_id, conversation_id, limit)

def report_memory_feedback(db: Session, memory_id: uuid.UUID, feedback_type: str, feedback_details: Optional[str] = None):
    return repo_memories.report_memory_feedback(db, memory_id, feedback_type, feedback_details)

# CRUD for FeedbackLog
def create_feedback_log(db: Session, feedback_log: schemas.FeedbackLogCreate):
    db_feedback_log = models.FeedbackLog(
    memory_id=feedback_log.memory_id,
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
        for key, value in feedback_log.model_dump(exclude_unset=True).items():
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

def _get_or_create_keyword(db: Session, keyword_text: str, *, visibility_scope: str = SCOPE_PERSONAL, owner_user_id=None, organization_id=None):
    # Remove leading/trailing whitespace and then trailing periods from the keyword text
    processed_keyword_text = keyword_text.strip().rstrip('.')
    
    q = db.query(models.Keyword).filter(models.Keyword.keyword_text == processed_keyword_text,
                                        models.Keyword.visibility_scope == visibility_scope)
    if visibility_scope == SCOPE_ORGANIZATION and organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    elif visibility_scope == SCOPE_PERSONAL and owner_user_id is not None:
        q = q.filter(models.Keyword.owner_user_id == owner_user_id)
    keyword = q.first()
    if not keyword:
        keyword = models.Keyword(
            keyword_text=processed_keyword_text,
            visibility_scope=visibility_scope,
            owner_user_id=owner_user_id,
            organization_id=organization_id,
        )
        db.add(keyword)
        db.flush()  # Use flush to get the ID before commit
    return keyword

# CRUD for MemoryBlockKeyword (Association Table)
def create_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    return repo_keywords.create_memory_block_keyword(db, memory_id, keyword_id)

def delete_memory_block_keyword(db: Session, memory_id: uuid.UUID, keyword_id: uuid.UUID):
    return repo_keywords.delete_memory_block_keyword(db, memory_id, keyword_id)

def get_memory_block_keywords(db: Session, memory_id: uuid.UUID):
    return repo_keywords.get_memory_block_keywords(db, memory_id)

def get_keyword_memory_blocks(
    db: Session,
    keyword_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
):
    return repo_keywords.get_keyword_memory_blocks(
        db,
        keyword_id,
        skip,
        limit,
        current_user=current_user,
        scope_ctx=scope_ctx,
    )

def get_keyword_memory_blocks_count(
    db: Session,
    keyword_id: uuid.UUID,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
):
    return repo_keywords.get_keyword_memory_blocks_count(
        db,
        keyword_id,
        current_user=current_user,
        scope_ctx=scope_ctx,
    )


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
        update_data = suggestion.model_dump(exclude_unset=True)
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
            # original_memory_ids may be stored as strings; coerce to UUID objects when possible
            norm_ids = []
            for mid in original_memory_ids:
                if isinstance(mid, uuid.UUID):
                    norm_ids.append(mid)
                else:
                    try:
                        norm_ids.append(uuid.UUID(str(mid)))
                    except Exception:
                        # Skip invalid IDs silently in consolidation context
                        continue
            if not norm_ids:
                return None
            first_memory_block = db.query(models.MemoryBlock).filter(models.MemoryBlock.id == norm_ids[0]).first()
            if first_memory_block:
                new_memory_block = models.MemoryBlock(
                    agent_id=first_memory_block.agent_id,
                    conversation_id=first_memory_block.conversation_id,
                    content=db_suggestion.suggested_content,
                    lessons_learned=db_suggestion.suggested_lessons_learned,
                    metadata_col={"consolidated_from": [str(i) for i in norm_ids]}
                )
                db.add(new_memory_block)
                db.flush()

                # Add keywords to the new memory block
                for keyword_text in db_suggestion.suggested_keywords or []:
                    keyword = _get_or_create_keyword(db, keyword_text)
                    db_mbk = models.MemoryBlockKeyword(memory_id=new_memory_block.id, keyword_id=keyword.keyword_id)
                    db.add(db_mbk)

                # Archive original memory blocks instead of deleting them
                for memory_id in norm_ids:
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

# CRUD for Dashboard Stats
def get_unique_conversation_count(
    db: Session,
    *,
    current_user: Optional[dict] = None,
    scope_ctx: Optional[scope_utils.ScopeContext] = None,
):
    """
    Get the count of unique conversations from memory blocks.
    This counts distinct conversation_id values in the MemoryBlock table.
    """
    q = db.query(func.count(func.distinct(models.MemoryBlock.conversation_id)))
    q = q.filter(models.MemoryBlock.archived == False)
    q = scope_utils.apply_scope_filter(q, current_user, models.MemoryBlock)
    if scope_ctx is not None:
        q = scope_utils.apply_optional_scope_narrowing(q, scope_ctx.scope, scope_ctx.organization_id, models.MemoryBlock)
    return q.scalar()

# Enhanced Search Functions
def search_memory_blocks_enhanced(
    db: Session,
    search_type: str = "basic",
    search_query: Optional[str] = None,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    include_archived: bool = False,
    **search_params
):
    """
    Enhanced search function that delegates to the search service.
    This provides a CRUD-level interface to the new search capabilities.
    """
    from core.search import get_search_service
    
    search_service = get_search_service()
    
    results, metadata = search_service.enhanced_search_memory_blocks(
        db=db,
        search_type=search_type,
        search_query=search_query,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit,
        include_archived=include_archived,
        **search_params
    )
    
    return results, metadata

def search_memory_blocks_fulltext(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    min_score: float = 0.1,
    include_archived: bool = False,
    *,
    current_user: Optional[dict] = None,
):
    """
    Full-text search using PostgreSQL's built-in capabilities.
    """
    from core.search import get_search_service
    
    search_service = get_search_service()
    
    return search_service.search_memory_blocks_fulltext(
        db=db,
        query=query,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit,
        min_score=min_score,
        include_archived=include_archived,
        current_user=current_user,
    )

def search_memory_blocks_semantic(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    similarity_threshold: float = 0.7,
    include_archived: bool = False,
    *,
    current_user: Optional[dict] = None,
):
    """
    Semantic search using embeddings (placeholder implementation).
    """
    from core.search import get_search_service
    
    search_service = get_search_service()
    
    return search_service.search_memory_blocks_semantic(
        db=db,
        query=query,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit,
        similarity_threshold=similarity_threshold,
        include_archived=include_archived,
        current_user=current_user,
    )

def search_memory_blocks_hybrid(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    fulltext_weight: float = 0.7,
    semantic_weight: float = 0.3,
    min_combined_score: float = 0.1,
    include_archived: bool = False,
    *,
    current_user: Optional[dict] = None,
):
    """
    Hybrid search combining full-text and semantic search.
    """
    from core.search import get_search_service
    
    search_service = get_search_service()
    
    return search_service.search_memory_blocks_hybrid(
        db=db,
        query=query,
        agent_id=agent_id,
        conversation_id=conversation_id,
        limit=limit,
        fulltext_weight=fulltext_weight,
        semantic_weight=semantic_weight,
        min_combined_score=min_combined_score,
        include_archived=include_archived,
        current_user=current_user,
    )
# CRUD for Organization and related entities (facade delegates to repository)
def create_organization(db: Session, organization: schemas.OrganizationCreate, user_id: uuid.UUID):
    return repo_orgs.create_organization(db, organization, user_id)


def get_organization(db: Session, organization_id: uuid.UUID):
    return repo_orgs.get_organization(db, organization_id)


def get_organizations(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return repo_orgs.get_organizations(db, user_id, skip, limit)


def update_organization(db: Session, organization_id: uuid.UUID, organization: schemas.OrganizationUpdate):
    return repo_orgs.update_organization(db, organization_id, organization)


def delete_organization(db: Session, organization_id: uuid.UUID):
    return repo_orgs.delete_organization(db, organization_id)


def create_organization_member(db: Session, organization_id: uuid.UUID, member: schemas.OrganizationMemberCreate):
    return repo_orgs.create_organization_member(db, organization_id, member)


def get_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    return repo_orgs.get_organization_member(db, organization_id, user_id)


def get_organization_members(db: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return repo_orgs.get_organization_members(db, organization_id, skip, limit)


def update_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID, member: schemas.OrganizationMemberUpdate):
    return repo_orgs.update_organization_member(db, organization_id, user_id, member)


def delete_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    return repo_orgs.delete_organization_member(db, organization_id, user_id)


def create_organization_invitation(
    db: Session,
    organization_id: uuid.UUID,
    invitation: schemas.OrganizationInvitationCreate,
    invited_by_user_id: uuid.UUID,
):
    return repo_orgs.create_organization_invitation(db, organization_id, invitation, invited_by_user_id)


def get_organization_invitation(db: Session, invitation_id: uuid.UUID):
    return repo_orgs.get_organization_invitation(db, invitation_id)


def get_organization_invitations(
    db: Session,
    organization_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
    *,
    status: str | None = None,
):
    return repo_orgs.get_organization_invitations(db, organization_id, skip, limit, status=status)


def update_organization_invitation(
    db: Session,
    invitation_id: uuid.UUID,
    invitation: schemas.OrganizationInvitationUpdate,
):
    return repo_orgs.update_organization_invitation(db, invitation_id, invitation)


def delete_organization_invitation(db: Session, invitation_id: uuid.UUID) -> bool:
    return repo_orgs.delete_organization_invitation(db, invitation_id)

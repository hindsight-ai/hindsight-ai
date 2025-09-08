from sqlalchemy.orm import Session, joinedload # Import joinedload
from . import models, schemas
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import or_, and_, func, Text # Import func, and_, and Text
from typing import List, Optional

# CRUD for Agent
def create_agent(db: Session, agent: schemas.AgentCreate):
    db_agent = models.Agent(
        agent_name=agent.agent_name,
        visibility_scope=getattr(agent, 'visibility_scope', 'personal') or 'personal',
        owner_user_id=getattr(agent, 'owner_user_id', None),
        organization_id=getattr(agent, 'organization_id', None),
    )
    db.add(db_agent)
    db.commit()
    db.refresh(db_agent)
    return db_agent

def get_agent(db: Session, agent_id: uuid.UUID):
    return db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()

def get_agent_by_name(db: Session, agent_name: str, *, visibility_scope: str = None, owner_user_id=None, organization_id=None):
    q = db.query(models.Agent).filter(func.lower(models.Agent.agent_name) == func.lower(agent_name))
    if visibility_scope == 'organization' and organization_id is not None:
        q = q.filter(models.Agent.visibility_scope == 'organization', models.Agent.organization_id == organization_id)
    elif visibility_scope == 'personal' and owner_user_id is not None:
        q = q.filter(models.Agent.visibility_scope == 'personal', models.Agent.owner_user_id == owner_user_id)
    elif visibility_scope == 'public':
        q = q.filter(models.Agent.visibility_scope == 'public')
    return q.first()

def get_agents(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    """List agents with scope filtering.

    - Guests: only public
    - Authenticated: public OR personal(owner) OR member orgs
    - Optional explicit scope/org filters narrow results
    """
    q = db.query(models.Agent)
    if current_user is None:
        q = q.filter(models.Agent.visibility_scope == 'public')
    else:
        # Superadmin shortcut: sees all
        if current_user.get('is_superadmin'):
            pass  # no filter; they can read everything
        else:
            org_ids = []
            try:
                for m in current_user.get('memberships', []):
                    mid = m.get('organization_id')
                    if mid:
                        try:
                            org_ids.append(uuid.UUID(mid))
                        except Exception:
                            pass
            except Exception:
                pass
            q = q.filter(
                or_(
                    models.Agent.visibility_scope == 'public',
                    models.Agent.owner_user_id == current_user.get('id'),
                    and_(
                        models.Agent.visibility_scope == 'organization',
                        models.Agent.organization_id.in_(org_ids) if org_ids else False,
                    ),
                )
            )

    # Optional narrowing filters
    if scope in ('personal', 'organization', 'public'):
        q = q.filter(models.Agent.visibility_scope == scope)
    if organization_id is not None:
        q = q.filter(models.Agent.organization_id == organization_id)

    return q.offset(skip).limit(limit).all()

def search_agents(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    # Use pg_trgm's similarity for fuzzy matching
    # A similarity threshold of 0.3 is a common starting point, adjust as needed
    SIMILARITY_THRESHOLD = 0.3
    q = db.query(models.Agent).filter(
        func.similarity(models.Agent.agent_name, query) >= SIMILARITY_THRESHOLD
    )
    # Apply same scope rules as list
    if current_user is None:
        q = q.filter(models.Agent.visibility_scope == 'public')
    else:
        org_ids = []
        try:
            for m in current_user.get('memberships', []):
                mid = m.get('organization_id')
                if mid:
                    try:
                        org_ids.append(uuid.UUID(mid))
                    except Exception:
                        pass
        except Exception:
            pass
        q = q.filter(
            or_(
                models.Agent.visibility_scope == 'public',
                models.Agent.owner_user_id == current_user.get('id'),
                and_(
                    models.Agent.visibility_scope == 'organization',
                    models.Agent.organization_id.in_(org_ids) if org_ids else False,
                ),
            )
        )
    if scope in ('personal', 'organization', 'public'):
        q = q.filter(models.Agent.visibility_scope == scope)
    if organization_id is not None:
        q = q.filter(models.Agent.organization_id == organization_id)

    return q.order_by(
        func.similarity(models.Agent.agent_name, query).desc()
    ).offset(skip).limit(limit).all()

def update_agent(db: Session, agent_id: uuid.UUID, agent: schemas.AgentUpdate):
    db_agent = db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()
    if db_agent:
        for key, value in agent.model_dump(exclude_unset=True).items():
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
        for key, value in transcript.model_dump(exclude_unset=True).items():
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
    db_keyword = models.Keyword(
        keyword_text=keyword.keyword_text,
        visibility_scope=getattr(keyword, 'visibility_scope', 'personal') or 'personal',
        owner_user_id=getattr(keyword, 'owner_user_id', None),
        organization_id=getattr(keyword, 'organization_id', None),
    )
    db.add(db_keyword)
    db.commit()
    db.refresh(db_keyword)
    return db_keyword

def get_keyword(db: Session, keyword_id: uuid.UUID):
    return db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()

def get_keyword_by_text(db: Session, keyword_text: str):
    # Global lookup (legacy); prefer scoped variant below
    return db.query(models.Keyword).filter(models.Keyword.keyword_text == keyword_text).first()

def get_scoped_keyword_by_text(
    db: Session,
    keyword_text: str,
    *,
    visibility_scope: str,
    owner_user_id: Optional[uuid.UUID] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    q = db.query(models.Keyword).filter(
        models.Keyword.visibility_scope == visibility_scope,
        func.lower(models.Keyword.keyword_text) == func.lower(keyword_text),
    )
    if visibility_scope == 'organization' and organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    elif visibility_scope == 'personal' and owner_user_id is not None:
        q = q.filter(models.Keyword.owner_user_id == owner_user_id)
    return q.first()

# CRUD for Organization
def create_organization(db: Session, organization: schemas.OrganizationCreate, user_id: uuid.UUID):
    db_organization = models.Organization(
        name=organization.name,
        slug=organization.slug,
        created_by=user_id
    )
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)
    # Add creator as owner
    db_member = models.OrganizationMembership(
        organization_id=db_organization.id,
        user_id=user_id,
        role='owner'
    )
    db.add(db_member)
    db.commit()
    return db_organization

def get_organization(db: Session, organization_id: uuid.UUID):
    return db.query(models.Organization).filter(models.Organization.id == organization_id).first()

def get_organizations(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.Organization).join(models.OrganizationMembership).filter(models.OrganizationMembership.user_id == user_id).offset(skip).limit(limit).all()

def update_organization(db: Session, organization_id: uuid.UUID, organization: schemas.OrganizationUpdate):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        update_data = organization.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_organization, key, value)
        db.commit()
        db.refresh(db_organization)
    return db_organization

def delete_organization(db: Session, organization_id: uuid.UUID):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        db.delete(db_organization)
        db.commit()
        return True
    return False

# CRUD for OrganizationMember
def create_organization_member(db: Session, organization_id: uuid.UUID, member: schemas.OrganizationMemberCreate):
    db_member = models.OrganizationMembership(
        organization_id=organization_id,
        **member.model_dump()
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def get_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    return db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id, models.OrganizationMembership.user_id == user_id).first()

def get_organization_members(db: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id).offset(skip).limit(limit).all()

def update_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID, member: schemas.OrganizationMemberUpdate):
    db_member = db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id, models.OrganizationMembership.user_id == user_id).first()
    if db_member:
        update_data = member.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_member, key, value)
        db.commit()
        db.refresh(db_member)
    return db_member

# CRUD for AuditLog
def create_audit_log(db: Session, audit_log: schemas.AuditLogCreate, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID] = None):
    data = audit_log.model_dump()
    metadata_payload = data.pop('metadata', None)
    db_audit_log = models.AuditLog(
        **data,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata_json=metadata_payload,
    )
    db.add(db_audit_log)
    db.commit()
    db.refresh(db_audit_log)
    return db_audit_log

def get_audit_logs(db: Session, organization_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, action_type: Optional[str] = None, status: Optional[str] = None, skip: int = 0, limit: int = 100):
    """Retrieve audit logs with optional filters.

    Parameters:
        organization_id: Restrict to a specific organization.
        user_id: Filter by actor user id.
        action_type: Filter by action type (e.g., 'member_add').
        status: Filter by status (e.g., 'success', 'failure').
        skip/limit: Pagination controls.
    """
    query = db.query(models.AuditLog)
    if organization_id:
        query = query.filter(models.AuditLog.organization_id == organization_id)
    if user_id:
        query = query.filter(models.AuditLog.actor_user_id == user_id)
    if action_type:
        query = query.filter(models.AuditLog.action_type == action_type)
    if status:
        query = query.filter(models.AuditLog.status == status)
    return query.order_by(models.AuditLog.created_at.desc()).offset(skip).limit(limit).all()

# CRUD for BulkOperation
def create_bulk_operation(db: Session, bulk_operation: schemas.BulkOperationCreate, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID] = None):
    db_bulk_operation = models.BulkOperation(
        **bulk_operation.model_dump(),
        actor_user_id=actor_user_id,
        organization_id=organization_id
    )
    db.add(db_bulk_operation)
    db.commit()
    db.refresh(db_bulk_operation)
    return db_bulk_operation

def get_bulk_operation(db: Session, bulk_operation_id: uuid.UUID):
    return db.query(models.BulkOperation).filter(models.BulkOperation.id == bulk_operation_id).first()

def get_bulk_operations(db: Session, organization_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100):
    query = db.query(models.BulkOperation)
    if organization_id:
        query = query.filter(models.BulkOperation.organization_id == organization_id)
    if user_id:
        query = query.filter(models.BulkOperation.actor_user_id == user_id)
    return query.order_by(models.BulkOperation.created_at.desc()).offset(skip).limit(limit).all()

def update_bulk_operation(db: Session, bulk_operation_id: uuid.UUID, bulk_operation: schemas.BulkOperationUpdate):
    db_bulk_operation = db.query(models.BulkOperation).filter(models.BulkOperation.id == bulk_operation_id).first()
    if db_bulk_operation:
        update_data = bulk_operation.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_bulk_operation, key, value)
        db.commit()
        db.refresh(db_bulk_operation)
    return db_bulk_operation


# CRUD for Organization
def create_organization(db: Session, organization: schemas.OrganizationCreate, user_id: uuid.UUID):
    db_organization = models.Organization(
        name=organization.name,
        slug=organization.slug,
        created_by=user_id
    )
    db.add(db_organization)
    db.commit()
    db.refresh(db_organization)
    # Add creator as owner
    db_member = models.OrganizationMembership(
        organization_id=db_organization.id,
        user_id=user_id,
        role='owner'
    )
    db.add(db_member)
    db.commit()
    return db_organization

def get_organization(db: Session, organization_id: uuid.UUID):
    return db.query(models.Organization).filter(models.Organization.id == organization_id).first()

def get_organizations(db: Session, user_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.Organization).join(models.OrganizationMembership).filter(models.OrganizationMembership.user_id == user_id).offset(skip).limit(limit).all()

def update_organization(db: Session, organization_id: uuid.UUID, organization: schemas.OrganizationUpdate):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        update_data = organization.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_organization, key, value)
        db.commit()
        db.refresh(db_organization)
    return db_organization

def delete_organization(db: Session, organization_id: uuid.UUID):
    db_organization = db.query(models.Organization).filter(models.Organization.id == organization_id).first()
    if db_organization:
        db.delete(db_organization)
        db.commit()
        return True
    return False

# CRUD for OrganizationMember
def create_organization_member(db: Session, organization_id: uuid.UUID, member: schemas.OrganizationMemberCreate):
    db_member = models.OrganizationMembership(
        organization_id=organization_id,
        **member.model_dump()
    )
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member

def get_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    return db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id, models.OrganizationMembership.user_id == user_id).first()

def get_organization_members(db: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id).offset(skip).limit(limit).all()

def update_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID, member: schemas.OrganizationMemberUpdate):
    db_member = db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id, models.OrganizationMembership.user_id == user_id).first()
    if db_member:
        update_data = member.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_member, key, value)
        db.commit()
        db.refresh(db_member)
    return db_member

def delete_organization_member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    db_member = db.query(models.OrganizationMembership).filter(models.OrganizationMembership.organization_id == organization_id, models.OrganizationMembership.user_id == user_id).first()
    if db_member:
        db.delete(db_member)
        db.commit()
        return True
    return False

# CRUD for OrganizationInvitation
def create_organization_invitation(db: Session, organization_id: uuid.UUID, invitation: schemas.OrganizationInvitationCreate, invited_by_user_id: uuid.UUID):
    db_invitation = models.OrganizationInvitation(
        organization_id=organization_id,
        email=invitation.email,
        role=invitation.role,
        invited_by_user_id=invited_by_user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7)
    )
    db.add(db_invitation)
    db.commit()
    db.refresh(db_invitation)
    return db_invitation

def get_organization_invitation(db: Session, invitation_id: uuid.UUID):
    return db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()

def get_organization_invitations(db: Session, organization_id: uuid.UUID, skip: int = 0, limit: int = 100):
    return db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.organization_id == organization_id).offset(skip).limit(limit).all()

def update_organization_invitation(db: Session, invitation_id: uuid.UUID, invitation: schemas.OrganizationInvitationUpdate):
    db_invitation = db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()
    if db_invitation:
        update_data = invitation.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_invitation, key, value)
        db.commit()
        db.refresh(db_invitation)
    return db_invitation

def delete_organization_invitation(db: Session, invitation_id: uuid.UUID):
    db_invitation = db.query(models.OrganizationInvitation).filter(models.OrganizationInvitation.id == invitation_id).first()
    if db_invitation:
        db.delete(db_invitation)
        db.commit()
        return True
    return False

def get_keywords(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    *,
    current_user: Optional[dict] = None,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
):
    q = db.query(models.Keyword)
    if current_user is None:
        q = q.filter(models.Keyword.visibility_scope == 'public')
    else:
        if current_user.get('is_superadmin'):
            pass
        else:
            org_ids = []
            try:
                for m in current_user.get('memberships', []):
                    mid = m.get('organization_id')
                    if mid:
                        try:
                            org_ids.append(uuid.UUID(mid))
                        except Exception:
                            pass
            except Exception:
                pass
            q = q.filter(
                or_(
                    models.Keyword.visibility_scope == 'public',
                    models.Keyword.owner_user_id == current_user.get('id'),
                    and_(
                        models.Keyword.visibility_scope == 'organization',
                        models.Keyword.organization_id.in_(org_ids) if org_ids else False,
                    ),
                )
            )
    if scope in ('personal', 'organization', 'public'):
        q = q.filter(models.Keyword.visibility_scope == scope)
    if organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    return q.offset(skip).limit(limit).all()

def update_keyword(db: Session, keyword_id: uuid.UUID, keyword: schemas.KeywordUpdate):
    db_keyword = db.query(models.Keyword).filter(models.Keyword.keyword_id == keyword_id).first()
    if db_keyword:
        for key, value in keyword.model_dump(exclude_unset=True).items():
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
        feedback_score=memory_block.feedback_score or 0,  # Default to 0 if not provided
        visibility_scope=getattr(memory_block, 'visibility_scope', 'personal') or 'personal',
        owner_user_id=getattr(memory_block, 'owner_user_id', None),
        organization_id=getattr(memory_block, 'organization_id', None),
    )
    db.add(db_memory_block)
    db.flush()  # Flush to get memory_id before commit

    # Use NLP-based keyword extraction; fallback heuristics if none
    extracted_keywords = set()
    try:
        from core.core.keyword_extraction import extract_keywords  # type: ignore
        extracted_keywords = set(extract_keywords(memory_block.content)) or set()
    except Exception:  # pragma: no cover
        extracted_keywords = set()

    if not extracted_keywords:
        import re
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", memory_block.content.lower())
        extracted_keywords = set(tokens[:10])

    # Create associations with keywords
    for keyword_text in extracted_keywords:
        keyword = _get_or_create_keyword(
            db,
            keyword_text,
            visibility_scope=db_memory_block.visibility_scope,
            owner_user_id=db_memory_block.owner_user_id,
            organization_id=db_memory_block.organization_id,
        )
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
    # Use model_validate with from_attributes per Pydantic v2 best practices
    return schemas.MemoryBlock.model_validate(db_memory_block, from_attributes=True)

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
    is_archived: Optional[bool] = None, # New parameter to explicitly filter by archived status
    current_user: Optional[dict] = None,
    filter_scope: Optional[str] = None,
    filter_organization_id: Optional[uuid.UUID] = None,
):
    query = db.query(models.MemoryBlock).options(joinedload(models.MemoryBlock.memory_block_keywords).joinedload(models.MemoryBlockKeyword.keyword)) # Eager load keywords

    # Apply scope filters
    if current_user is None:
        query = query.filter(models.MemoryBlock.visibility_scope == 'public')
    else:
        # Allowed: public OR personal owned OR orgs where user is a member
        org_ids = []
        try:
            memberships = current_user.get('memberships', [])
            for m in memberships:
                mid = m.get('organization_id')
                if mid:
                    try:
                        org_ids.append(uuid.UUID(mid))
                    except Exception:
                        pass
        except Exception:
            pass
        query = query.filter(
            or_(
                models.MemoryBlock.visibility_scope == 'public',
                models.MemoryBlock.owner_user_id == current_user.get('id'),
                and_(
                    models.MemoryBlock.visibility_scope == 'organization',
                    models.MemoryBlock.organization_id.in_(org_ids) if org_ids else False
                ),
            )
        )

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
                models.MemoryBlock.id.cast(Text).ilike(search_pattern), # Search UUID as string
                models.MemoryBlock.content.ilike(search_pattern),
                models.MemoryBlock.errors.ilike(search_pattern),
                models.MemoryBlock.lessons_learned.ilike(search_pattern),
                # Searching JSON metadata requires casting to text
                models.MemoryBlock.metadata_col.cast(Text).ilike(search_pattern),
                models.MemoryBlock.agent_id.cast(Text).ilike(search_pattern), # Search agent_id as string
                models.MemoryBlock.conversation_id.cast(Text).ilike(search_pattern) # Search conversation_id as string
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

    # Optional explicit narrowing
    if filter_scope in ('personal', 'organization', 'public'):
        query = query.filter(models.MemoryBlock.visibility_scope == filter_scope)
        if filter_scope == 'organization' and filter_organization_id is not None:
            query = query.filter(models.MemoryBlock.organization_id == filter_organization_id)
        if filter_scope == 'personal' and current_user is not None:
            query = query.filter(models.MemoryBlock.owner_user_id == current_user.get('id'))

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
        update_data = memory_block.model_dump(exclude_unset=True)
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
    feedback_log_create = schemas.FeedbackLogCreate(memory_id=memory_id, feedback_type=feedback_type, feedback_details=feedback_details)
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

def _get_or_create_keyword(db: Session, keyword_text: str, *, visibility_scope: str = 'personal', owner_user_id=None, organization_id=None):
    # Remove leading/trailing whitespace and then trailing periods from the keyword text
    processed_keyword_text = keyword_text.strip().rstrip('.')
    
    q = db.query(models.Keyword).filter(models.Keyword.keyword_text == processed_keyword_text,
                                        models.Keyword.visibility_scope == visibility_scope)
    if visibility_scope == 'organization' and organization_id is not None:
        q = q.filter(models.Keyword.organization_id == organization_id)
    elif visibility_scope == 'personal' and owner_user_id is not None:
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

def get_keyword_memory_blocks(db: Session, keyword_id: uuid.UUID, skip: int = 0, limit: int = 50):
    """Get all memory blocks associated with a specific keyword."""
    return db.query(models.MemoryBlock).join(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.keyword_id == keyword_id
    ).offset(skip).limit(limit).all()

def get_keyword_memory_blocks_count(db: Session, keyword_id: uuid.UUID):
    """Get the count of memory blocks associated with a specific keyword."""
    return db.query(models.MemoryBlock).join(models.MemoryBlockKeyword).filter(
        models.MemoryBlockKeyword.keyword_id == keyword_id
    ).count()


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

# CRUD for Dashboard Stats
def get_unique_conversation_count(db: Session):
    """
    Get the count of unique conversations from memory blocks.
    This counts distinct conversation_id values in the MemoryBlock table.
    """
    return db.query(func.count(func.distinct(models.MemoryBlock.conversation_id))).filter(
        models.MemoryBlock.archived == False  # Only count non-archived memory blocks
    ).scalar()

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
    include_archived: bool = False
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
        include_archived=include_archived
    )

def search_memory_blocks_semantic(
    db: Session,
    query: str,
    agent_id: Optional[uuid.UUID] = None,
    conversation_id: Optional[uuid.UUID] = None,
    limit: int = 50,
    similarity_threshold: float = 0.7,
    include_archived: bool = False
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
        include_archived=include_archived
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
    include_archived: bool = False
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
        include_archived=include_archived
    )

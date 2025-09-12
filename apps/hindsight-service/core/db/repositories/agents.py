"""
Agent repository functions.

Implements create/read/update/delete for agents and transcripts, including
scope-aware queries and fuzzy search.
"""
from __future__ import annotations

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from core.db import models, schemas, scope_utils


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


def get_agent_by_name(
    db: Session,
    agent_name: str,
    *,
    visibility_scope: str | None = None,
    owner_user_id=None,
    organization_id=None,
):
    q = db.query(models.Agent).filter(func.lower(models.Agent.agent_name) == func.lower(agent_name))
    if visibility_scope == 'organization' and organization_id is not None:
        # Accept either UUID object or string
        if isinstance(organization_id, str):
            try:
                import uuid as _uuid
                organization_id = _uuid.UUID(organization_id)
            except Exception:
                pass
        q = q.filter(models.Agent.visibility_scope == 'organization', models.Agent.organization_id == organization_id)
    elif visibility_scope == 'personal' and owner_user_id is not None:
        if isinstance(owner_user_id, str):
            try:
                import uuid as _uuid
                owner_user_id = _uuid.UUID(owner_user_id)
            except Exception:
                pass
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
    """List agents with scope filtering."""
    q = db.query(models.Agent)
    q = scope_utils.apply_scope_filter(q, current_user, models.Agent)
    q = scope_utils.apply_optional_scope_narrowing(q, scope, organization_id, models.Agent)
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
    SIMILARITY_THRESHOLD = 0.3
    q = db.query(models.Agent).filter(
        func.similarity(models.Agent.agent_name, query) >= SIMILARITY_THRESHOLD
    )
    q = scope_utils.apply_scope_filter(q, current_user, models.Agent)
    q = scope_utils.apply_optional_scope_narrowing(q, scope, organization_id, models.Agent)
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
    """Delete an agent and its related records with proper error handling."""
    if agent_id is None:
        return False
    try:
        db_agent = db.query(models.Agent).filter(models.Agent.agent_id == agent_id).first()
        if not db_agent:
            return False
        # Delete associated AgentTranscript records
        db.query(models.AgentTranscript).filter(
            models.AgentTranscript.agent_id == agent_id
        ).delete(synchronize_session=False)
        # Delete associated MemoryBlock records
        db.query(models.MemoryBlock).filter(
            models.MemoryBlock.agent_id == agent_id
        ).delete(synchronize_session=False)
        # Now delete the agent
        db.delete(db_agent)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to delete agent {agent_id}: {str(e)}")


# Transcripts
def create_agent_transcript(db: Session, transcript: schemas.AgentTranscriptCreate):
    db_transcript = models.AgentTranscript(
        agent_id=transcript.agent_id,
        conversation_id=transcript.conversation_id,
        transcript_content=transcript.transcript_content,
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
    """Delete an agent transcript with proper error handling."""
    if transcript_id is None:
        return None
    try:
        db_transcript = db.query(models.AgentTranscript).filter(
            models.AgentTranscript.transcript_id == transcript_id
        ).first()
        if db_transcript:
            db.delete(db_transcript)
            db.commit()
        return db_transcript
    except Exception as e:
        db.rollback()
        raise RuntimeError(f"Failed to delete agent transcript {transcript_id}: {str(e)}")

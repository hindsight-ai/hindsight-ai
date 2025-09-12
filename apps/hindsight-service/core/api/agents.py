"""
Agents API endpoints.

CRUD and scope-change operations for agent resources with permission checks.
"""
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from core.db import schemas, crud
from core.db.database import get_db
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_read, can_write
from core.api.deps import get_current_user_context

router = APIRouter(prefix="/agents", tags=["agents"])  # normalized prefix

@router.post("/", response_model=schemas.Agent, status_code=status.HTTP_201_CREATED)
def create_agent_endpoint(
    agent: schemas.AgentCreate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    u, current_user = user_context

    scope = getattr(agent, 'visibility_scope', 'personal') or 'personal'
    owner_user_id = u.id if scope == 'personal' else None
    org_id = getattr(agent, 'organization_id', None)
    if scope == 'organization':
        by_org = current_user.get('memberships_by_org', {})
        key = str(org_id) if org_id else None
        m = by_org.get(key) if key else None
        role = (m or {}).get('role') if m else None
        can_write = bool((m or {}).get('can_write'))
        if not m or not (can_write or role in ('owner', 'admin', 'editor')):
            raise HTTPException(status_code=403, detail="No write permission in target organization")
    if scope == 'public' and not current_user.get('is_superadmin'):
        raise HTTPException(status_code=403, detail="Only superadmin can create public agents")

    existing = crud.get_agent_by_name(
        db,
        agent_name=agent.agent_name,
        visibility_scope=scope,
        owner_user_id=owner_user_id,
        organization_id=org_id,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this name already exists in the selected scope")

    agent_for_create = agent.model_copy(update={
        'visibility_scope': scope,
        'owner_user_id': owner_user_id,
        'organization_id': org_id if scope == 'organization' else None,
    })
    created = crud.create_agent(db=db, agent=agent_for_create)
    try:
        from core.audit import log_agent, AuditAction, AuditStatus
        log_agent(
            db,
            actor_user_id=u.id,
            organization_id=created.organization_id,
            agent_id=created.agent_id,
            action=AuditAction.AGENT_CREATE,
            name=created.agent_name,
            status=AuditStatus.SUCCESS,
        )
    except Exception:
        pass
    return created

@router.get("/", response_model=List[schemas.Agent])
def get_all_agents_endpoint(
    skip: int = 0,
    limit: int = 100,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    agents = crud.get_agents(
        db,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope=scope,
        organization_id=organization_id,
    )
    return agents

@router.get("/{agent_id}", response_model=schemas.Agent)
def get_agent_endpoint(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    db_agent = crud.get_agent(db, agent_id=agent_id)
    if not db_agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    if not can_read(db_agent, current_user):
        raise HTTPException(status_code=404, detail="Agent not found")
    return db_agent

@router.get("/search/", response_model=List[schemas.Agent])
def search_agents_endpoint(
    query: str,
    skip: int = 0,
    limit: int = 100,
    scope: Optional[str] = None,
    organization_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    current_user = None
    if email:
        u = get_or_create_user(db, email=email, display_name=name)
        memberships = get_user_memberships(db, u.id)
        current_user = {
            "id": u.id,
            "is_superadmin": bool(u.is_superadmin),
            "memberships": memberships,
            "memberships_by_org": {m["organization_id"]: m for m in memberships},
        }
    agents = crud.search_agents(
        db,
        query=query,
        skip=skip,
        limit=limit,
        current_user=current_user,
        scope=scope,
        organization_id=organization_id,
    )
    return agents

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent_endpoint(
    agent_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    agent = crud.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    u, current_user = user_context
    if not can_write(agent, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    crud.delete_agent(db, agent_id=agent_id)
    try:
        from core.audit import log, AuditAction, AuditStatus
        log(
            db,
            action=AuditAction.AGENT_DELETE,
            status=AuditStatus.SUCCESS,
            target_type="agent",
            target_id=str(agent_id),
            actor_user_id=current_user.get("id") if current_user else None,
            organization_id=agent.organization_id,
            metadata={
                "agent_name": agent.agent_name,
                "visibility_scope": agent.visibility_scope,
            },
        )
    except Exception:
        pass
    return {"message": "Agent deleted successfully"}

@router.put("/{agent_id}", response_model=schemas.Agent)
def update_agent_endpoint(
    agent_id: uuid.UUID,
    agent_update: schemas.AgentUpdate,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    agent = crud.get_agent(db, agent_id=agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    u, current_user = user_context
    if not can_write(agent, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")
    if agent_update.agent_name and agent_update.agent_name != agent.agent_name:
        existing = crud.get_agent_by_name(
            db,
            agent_name=agent_update.agent_name,
            visibility_scope=agent.visibility_scope,
            owner_user_id=agent.owner_user_id,
            organization_id=agent.organization_id,
        )
        if existing and existing.agent_id != agent_id:
            raise HTTPException(status_code=409, detail="Agent with this name already exists in the selected scope")
    updated_agent = crud.update_agent(db, agent_id=agent_id, agent=agent_update)
    return updated_agent

@router.post("/{agent_id}/change-scope", response_model=schemas.Agent)
def change_agent_scope(
    agent_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    user_context = Depends(get_current_user_context),
):
    agent = crud.get_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    u, current_user = user_context
    target_scope = (payload.get("visibility_scope") or '').lower()
    if target_scope not in ("personal", "organization", "public"):
        raise HTTPException(status_code=422, detail="Invalid target visibility_scope")
    target_org_id = payload.get("organization_id")
    new_owner_user_id = payload.get("new_owner_user_id")
    from core.api.permissions import can_move_scope
    if target_scope == 'organization':
        if not target_org_id:
            raise HTTPException(status_code=422, detail="organization_id required for organization scope")
        try:
            target_org_uuid = uuid.UUID(str(target_org_id))
        except Exception:
            raise HTTPException(status_code=422, detail="Invalid organization_id")
        if agent.visibility_scope == 'personal' and not (current_user.get('is_superadmin') or agent.owner_user_id == current_user.get('id')):
            raise HTTPException(status_code=409, detail="Owner consent required to move personal agent to organization")
        if not can_move_scope(agent, 'organization', target_org_uuid, current_user):
            raise HTTPException(status_code=403, detail="Forbidden")
    elif target_scope == 'personal':
        if not can_move_scope(agent, 'personal', None, current_user):
            if not current_user.get("is_superadmin"):
                raise HTTPException(status_code=403, detail="Forbidden")
    elif target_scope == 'public':
        if not current_user.get("is_superadmin"):
            raise HTTPException(status_code=403, detail="Only superadmin can publish to public")
    owner_id = None
    org_uuid = None
    if target_scope == 'organization':
        org_uuid = target_org_uuid  # type: ignore
    elif target_scope == 'personal':
        owner_id = u.id
        if new_owner_user_id:
            try:
                owner_uuid = uuid.UUID(str(new_owner_user_id))
            except Exception:
                raise HTTPException(status_code=422, detail="Invalid new_owner_user_id")
            if not current_user.get("is_superadmin"):
                raise HTTPException(status_code=403, detail="Only superadmin can set a different personal owner")
            owner_id = owner_uuid
    existing = crud.get_agent_by_name(
        db,
        agent_name=agent.agent_name,
        visibility_scope=target_scope,
        owner_user_id=owner_id,
        organization_id=org_uuid,
    )
    if existing and existing.agent_id != agent.agent_id:
        raise HTTPException(status_code=409, detail="Agent with this name already exists in the target scope")
    previous_scope = agent.visibility_scope
    previous_org_id = agent.organization_id
    previous_owner_id = agent.owner_user_id
    agent.visibility_scope = target_scope
    agent.owner_user_id = owner_id
    agent.organization_id = org_uuid
    db.commit()
    db.refresh(agent)
    try:
        from core.audit import log, AuditAction, AuditStatus
        log(
            db,
            action=AuditAction.AGENT_SCOPE_CHANGE,
            status=AuditStatus.SUCCESS,
            target_type="agent",
            target_id=str(agent.agent_id),
            actor_user_id=current_user.get("id"),
            organization_id=agent.organization_id or previous_org_id,
            metadata={
                "old_scope": previous_scope,
                "new_scope": agent.visibility_scope,
                "old_org_id": str(previous_org_id) if previous_org_id else None,
                "new_org_id": str(agent.organization_id) if agent.organization_id else None,
                "old_owner_user_id": str(previous_owner_id) if previous_owner_id else None,
                "new_owner_user_id": str(agent.owner_user_id) if agent.owner_user_id else None,
            },
        )
    except Exception:
        pass
    return agent

from typing import Optional, List
import uuid
import threading

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from core.db.database import get_db
from core.db import models, schemas, crud
from core.api.auth import resolve_identity_from_headers, get_or_create_user, get_user_memberships
from core.api.permissions import can_manage_org
from core.bulk_operations_worker import perform_bulk_move, perform_bulk_delete

router = APIRouter(tags=["bulk-operations"])

def _require_current_user(db: Session,
                          x_auth_request_user: Optional[str],
                          x_auth_request_email: Optional[str],
                          x_forwarded_user: Optional[str],
                          x_forwarded_email: Optional[str]):
    name, email = resolve_identity_from_headers(
        x_auth_request_user=x_auth_request_user,
        x_auth_request_email=x_auth_request_email,
        x_forwarded_user=x_forwarded_user,
        x_forwarded_email=x_forwarded_email,
    )
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user = get_or_create_user(db, email=email, display_name=name)
    # Build a compact context with memberships_by_org
    memberships = get_user_memberships(db, user.id)
    memberships_by_org = {m["organization_id"]: m for m in memberships}
    current_user = {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "is_superadmin": bool(user.is_superadmin),
        "memberships": memberships,
        "memberships_by_org": memberships_by_org,
    }
    return user, current_user

@router.get("/organizations/{org_id}/inventory")
def get_organization_inventory(
    org_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    agent_count = db.query(models.Agent).filter(models.Agent.organization_id == org_id).count()
    memory_block_count = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).count()
    keyword_count = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).count()

    return {
        "agent_count": agent_count,
        "memory_block_count": memory_block_count,
        "keyword_count": keyword_count,
    }

@router.post("/organizations/{org_id}/bulk-move")
def bulk_move(
    org_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    dry_run = payload.get("dry_run", True)
    destination_organization_id = payload.get("destination_organization_id")
    destination_owner_user_id = payload.get("destination_owner_user_id")
    resource_types = payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

    if not destination_organization_id and not destination_owner_user_id:
        raise HTTPException(status_code=422, detail="Either destination_organization_id or destination_owner_user_id is required")

    if destination_organization_id and destination_owner_user_id:
        raise HTTPException(status_code=422, detail="Cannot specify both destination_organization_id and destination_owner_user_id")

    if destination_organization_id and not can_manage_org(destination_organization_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden to move resources to the destination organization")

    plan = {
        "resources_to_move": {},
        "conflicts": {},
    }

    if "agents" in resource_types:
        agents = db.query(models.Agent).filter(models.Agent.organization_id == org_id).all()
        plan["resources_to_move"]["agents"] = len(agents)
        plan["conflicts"]["agents"] = []
        for agent in agents:
            existing = crud.get_agent_by_name(
                db,
                agent_name=agent.agent_name,
                visibility_scope="organization" if destination_organization_id else "personal",
                organization_id=destination_organization_id,
                owner_user_id=destination_owner_user_id,
            )
            if existing:
                plan["conflicts"]["agents"].append({"name": agent.agent_name, "id": agent.agent_id})

    if "keywords" in resource_types:
        keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).all()
        plan["resources_to_move"]["keywords"] = len(keywords)
        plan["conflicts"]["keywords"] = []
        for keyword in keywords:
            existing = crud.get_scoped_keyword_by_text(
                db,
                keyword_text=keyword.keyword_text,
                visibility_scope="organization" if destination_organization_id else "personal",
                organization_id=destination_organization_id,
                owner_user_id=destination_owner_user_id,
            )
            if existing:
                plan["conflicts"]["keywords"].append({"text": keyword.keyword_text, "id": keyword.keyword_id})

    if "memory_blocks" in resource_types:
        memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).all()
        plan["resources_to_move"]["memory_blocks"] = len(memory_blocks)

    if dry_run:
        return plan

    # Create bulk operation record
    bulk_op_create = schemas.BulkOperationCreate(
        type="bulk_move",
        request_payload=payload,
    )
    bulk_operation = crud.create_bulk_operation(db, bulk_op_create, actor_user_id=user.id, organization_id=org_id)

    # Start worker thread
    worker_thread = threading.Thread(
        target=perform_bulk_move,
        args=(bulk_operation.id, user.id, org_id, payload)
    )
    worker_thread.start()

    return {"operation_id": bulk_operation.id, "status": "started"}

@router.post("/organizations/{org_id}/bulk-delete")
def bulk_delete(
    org_id: uuid.UUID,
    payload: dict,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not can_manage_org(org_id, current_user):
        raise HTTPException(status_code=403, detail="Forbidden")

    dry_run = payload.get("dry_run", True)
    resource_types = payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

    plan = {
        "resources_to_delete": {},
    }

    if "agents" in resource_types:
        agents = db.query(models.Agent).filter(models.Agent.organization_id == org_id).count()
        plan["resources_to_delete"]["agents"] = agents

    if "keywords" in resource_types:
        keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).count()
        plan["resources_to_delete"]["keywords"] = keywords

    if "memory_blocks" in resource_types:
        memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).count()
        plan["resources_to_delete"]["memory_blocks"] = memory_blocks

    if dry_run:
        return plan

    # Create bulk operation record
    bulk_op_create = schemas.BulkOperationCreate(
        type="bulk_delete",
        request_payload=payload,
    )
    bulk_operation = crud.create_bulk_operation(db, bulk_op_create, actor_user_id=user.id, organization_id=org_id)

    # Start worker thread
    worker_thread = threading.Thread(
        target=perform_bulk_delete,
        args=(bulk_operation.id, user.id, org_id, payload)
    )
    worker_thread.start()

    return {"operation_id": bulk_operation.id, "status": "started"}

@router.get("/admin/operations/{operation_id}", response_model=schemas.BulkOperation)
def get_operation_status(
    operation_id: uuid.UUID,
    db: Session = Depends(get_db),
    x_auth_request_user: Optional[str] = Header(default=None),
    x_auth_request_email: Optional[str] = Header(default=None),
    x_forwarded_user: Optional[str] = Header(default=None),
    x_forwarded_email: Optional[str] = Header(default=None),
):
    user, current_user = _require_current_user(db, x_auth_request_user, x_auth_request_email, x_forwarded_user, x_forwarded_email)
    if not current_user.get("is_superadmin"):
        raise HTTPException(status_code=403, detail="Forbidden")

    operation = crud.get_bulk_operation(db, bulk_operation_id=operation_id)
    if not operation:
        raise HTTPException(status_code=404, detail="Operation not found")

    return operation

"""
Audit logging helpers and enums.

Centralized helpers to persist normalized audit records with consistent
schema; includes convenience wrappers per target type.
"""
from __future__ import annotations
import uuid
from enum import Enum
from typing import Any, Optional, Dict
from sqlalchemy.orm import Session

from core.db import crud, schemas

class AuditAction(str, Enum):
    # Organization
    ORGANIZATION_CREATE = "organization_create"
    ORGANIZATION_UPDATE = "organization_update"
    ORGANIZATION_DELETE = "organization_delete"
    # Membership
    MEMBER_ADD = "member_add"
    MEMBER_REMOVE = "member_remove"
    MEMBER_ROLE_CHANGE = "member_role_change"
    # Invitations
    INVITATION_CREATE = "invitation_create"
    INVITATION_RESEND = "invitation_resend"
    INVITATION_REVOKE = "invitation_revoke"
    INVITATION_ACCEPT = "invitation_accept"
    INVITATION_DECLINE = "invitation_decline"
    # Agent
    AGENT_CREATE = "agent_create"
    AGENT_UPDATE = "agent_update"
    AGENT_DELETE = "agent_delete"
    AGENT_SCOPE_CHANGE = "agent_scope_change"
    # Memory Block
    MEMORY_CREATE = "memory_create"
    MEMORY_UPDATE = "memory_update"
    MEMORY_DELETE = "memory_delete"
    MEMORY_ARCHIVE = "memory_archive"
    MEMORY_SCOPE_CHANGE = "memory_scope_change"
    # Keyword
    KEYWORD_CREATE = "keyword_create"
    KEYWORD_UPDATE = "keyword_update"
    KEYWORD_DELETE = "keyword_delete"
    # Consolidation / Optimization / Pruning
    CONSOLIDATION_VALIDATE = "consolidation_validate"
    CONSOLIDATION_REJECT = "consolidation_reject"
    CONSOLIDATION_DELETE = "consolidation_delete"
    PRUNING_SUGGEST = "pruning_suggest"
    PRUNING_CONFIRM = "pruning_confirm"
    # Bulk ops
    BULK_OPERATION_START = "bulk_operation_start"
    BULK_OPERATION_COMPLETE = "bulk_operation_complete"
    # Personal Access Tokens
    TOKEN_CREATE = "token_create"
    TOKEN_ROTATE = "token_rotate"
    TOKEN_REVOKE = "token_revoke"


class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


def log(
    db: Session,
    *,
    action: AuditAction | str,
    status: AuditStatus | str = AuditStatus.SUCCESS,
    target_type: str,
    target_id: Optional[uuid.UUID] = None,
    actor_user_id: uuid.UUID,
    organization_id: Optional[uuid.UUID] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> schemas.AuditLog:
    """Central audit logging helper.

    Ensures consistent schema and future-proof single place for enrichment.
    """
    # Ensure we persist pure string values, not Enum reprs (avoid 'AuditAction.XYZ')
    action_value = action.value if isinstance(action, AuditAction) else str(action)
    status_value = status.value if isinstance(status, AuditStatus) else str(status)
    audit_log = schemas.AuditLogCreate(
        action_type=action_value,
        status=status_value,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )
    return crud.create_audit_log(
        db,
        audit_log=audit_log,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
    )

__all__ = ["AuditAction", "AuditStatus", "log"]

# Convenience wrappers (non-breaking). Keep optional organization_id explicit.
def log_agent(db: Session, *, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID], agent_id: uuid.UUID, action: AuditAction, name: Optional[str] = None, status: AuditStatus | str = AuditStatus.SUCCESS):
    return log(
        db,
        action=action,
        status=status,
        target_type="agent",
        target_id=agent_id,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata={"name": name} if name else None,
    )

def log_keyword(db: Session, *, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID], keyword_id: uuid.UUID, action: AuditAction, text: Optional[str] = None, status: AuditStatus | str = AuditStatus.SUCCESS):
    return log(
        db,
        action=action,
        status=status,
        target_type="keyword",
        target_id=keyword_id,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata={"text": text} if text else None,
    )

def log_memory(db: Session, *, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID], memory_block_id: uuid.UUID, action: AuditAction, status: AuditStatus | str = AuditStatus.SUCCESS, metadata: Optional[Dict[str, Any]] = None):
    return log(
        db,
        action=action,
        status=status,
        target_type="memory_block",
        target_id=memory_block_id,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata=metadata,
    )

def log_bulk_operation(db: Session, *, actor_user_id: uuid.UUID, organization_id: Optional[uuid.UUID], bulk_operation_id: uuid.UUID, action: AuditAction, status: AuditStatus | str = AuditStatus.SUCCESS, metadata: Optional[Dict[str, Any]] = None):
    return log(
        db,
        action=action,
        status=status,
        target_type="bulk_operation",
        target_id=bulk_operation_id,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        metadata=metadata,
    )

__all__.extend(["log_agent", "log_keyword", "log_memory", "log_bulk_operation"])

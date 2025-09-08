import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import create_engine  # (legacy import; retained if future dynamic engines needed)

from core.db import models, schemas, crud
from core.db.database import get_db_session_local

logger = logging.getLogger(__name__)

def _get_db():
    """Helper to get a new DB session for the worker thread."""
    SessionLocal = get_db_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def perform_bulk_move(operation_id: uuid.UUID, actor_user_id: uuid.UUID, organization_id: uuid.UUID, payload: dict):
    db = next(_get_db())
    try:
        operation = crud.get_bulk_operation(db, operation_id)
        if not operation:
            logger.error(f"Bulk operation {operation_id} not found for execution.")
            return

        operation.status = "running"
        operation.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(operation)

        destination_organization_id = payload.get("destination_organization_id")
        destination_owner_user_id = payload.get("destination_owner_user_id")
        resource_types = payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

        total_moved = 0
        errors = []

        # Process Agents
        if "agents" in resource_types:
            agents = db.query(models.Agent).filter(models.Agent.organization_id == organization_id).all()
            for agent in agents:
                try:
                    agent.organization_id = destination_organization_id
                    agent.owner_user_id = destination_owner_user_id
                    db.add(agent)
                    db.commit()
                    total_moved += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to move agent {agent.agent_id}: {e}")
                    logger.error(f"Failed to move agent {agent.agent_id}: {e}")

        # Process Keywords
        if "keywords" in resource_types:
            keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == organization_id).all()
            for keyword in keywords:
                try:
                    keyword.organization_id = destination_organization_id
                    keyword.owner_user_id = destination_owner_user_id
                    db.add(keyword)
                    db.commit()
                    total_moved += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to move keyword {keyword.keyword_id}: {e}")
                    logger.error(f"Failed to move keyword {keyword.keyword_id}: {e}")

        # Process Memory Blocks
        if "memory_blocks" in resource_types:
            memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == organization_id).all()
            for mb in memory_blocks:
                try:
                    mb.organization_id = destination_organization_id
                    mb.owner_user_id = destination_owner_user_id
                    db.add(mb)
                    db.commit()
                    total_moved += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to move memory block {mb.id}: {e}")
                    logger.error(f"Failed to move memory block {mb.id}: {e}")

        operation.status = "completed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_moved": total_moved, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}
            operation.status = "failed"
        db.commit()

    except Exception as e:
        db.rollback()
        operation.status = "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.error_log = {"message": str(e)}
        db.commit()
        logger.error(f"Error during bulk move operation {operation_id}: {e}")

def perform_bulk_delete(operation_id: uuid.UUID, actor_user_id: uuid.UUID, organization_id: uuid.UUID, payload: dict):
    db = next(_get_db())
    try:
        operation = crud.get_bulk_operation(db, operation_id)
        if not operation:
            logger.error(f"Bulk operation {operation_id} not found for execution.")
            return

        operation.status = "running"
        operation.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(operation)

        resource_types = payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

        total_deleted = 0
        errors = []

        # Process Agents
        if "agents" in resource_types:
            agents = db.query(models.Agent).filter(models.Agent.organization_id == organization_id).all()
            for agent in agents:
                try:
                    crud.delete_agent(db, agent.agent_id)
                    total_deleted += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to delete agent {agent.agent_id}: {e}")
                    logger.error(f"Failed to delete agent {agent.agent_id}: {e}")

        # Process Keywords
        if "keywords" in resource_types:
            keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == organization_id).all()
            for keyword in keywords:
                try:
                    crud.delete_keyword(db, keyword.keyword_id)
                    total_deleted += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to delete keyword {keyword.keyword_id}: {e}")
                    logger.error(f"Failed to delete keyword {keyword.keyword_id}: {e}")

        # Process Memory Blocks
        if "memory_blocks" in resource_types:
            memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == organization_id).all()
            for mb in memory_blocks:
                try:
                    crud.delete_memory_block(db, mb.id)
                    total_deleted += 1
                except Exception as e:
                    db.rollback()
                    errors.append(f"Failed to delete memory block {mb.id}: {e}")
                    logger.error(f"Failed to delete memory block {mb.id}: {e}")

        operation.status = "completed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_deleted": total_deleted, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}
            operation.status = "failed"
        db.commit()

    except Exception as e:
        db.rollback()
        operation.status = "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.error_log = {"message": str(e)}
        db.commit()
        logger.error(f"Error during bulk delete operation {operation_id}: {e}")

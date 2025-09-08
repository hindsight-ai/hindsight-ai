import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError, ObjectDeletedError
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
    """Perform move; resilient to concurrent deletions or stale rows.
    Uses per-item flush to limit transaction span and converts StaleData/ObjectDeleted into logical errors.
    """
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

        def _safe_commit(entity_desc: str, entity_id: str):
            try:
                db.commit()
                return True
            except (StaleDataError, ObjectDeletedError) as se:
                db.rollback()
                msg = f"Concurrent modification deleting {entity_desc} {entity_id}: {se}";
                logger.warning(msg)
                errors.append(msg)
            except Exception as e:  # noqa
                db.rollback()
                msg = f"Failed to persist {entity_desc} {entity_id}: {e}";
                logger.error(msg)
                errors.append(msg)
            return False

        # Process Agents
        if "agents" in resource_types:
            for agent in db.query(models.Agent).filter(models.Agent.organization_id == organization_id).all():
                agent.organization_id = destination_organization_id
                agent.owner_user_id = destination_owner_user_id
                if _safe_commit("agent", str(agent.agent_id)):
                    total_moved += 1

        # Process Keywords
        if "keywords" in resource_types:
            for keyword in db.query(models.Keyword).filter(models.Keyword.organization_id == organization_id).all():
                keyword.organization_id = destination_organization_id
                keyword.owner_user_id = destination_owner_user_id
                if _safe_commit("keyword", str(keyword.keyword_id)):
                    total_moved += 1

        # Process Memory Blocks
        if "memory_blocks" in resource_types:
            for mb in db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == organization_id).all():
                mb.organization_id = destination_organization_id
                mb.owner_user_id = destination_owner_user_id
                if _safe_commit("memory_block", str(mb.id)):
                    total_moved += 1

        operation.status = "completed" if not errors else "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_moved": total_moved, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}
        db.commit()
    except Exception as e:  # Final safeguard
        try:
            db.rollback()
        except Exception:
            pass
        if 'operation' in locals() and operation:
            operation.status = "failed"
            operation.finished_at = datetime.now(timezone.utc)
            operation.error_log = {"message": str(e)}
            try:
                db.commit()
            except Exception:
                pass
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
        db.commit(); db.refresh(operation)

        resource_types = payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

        total_deleted = 0
        errors = []

        def _safe_delete(desc: str, identifier: str, action):
            nonlocal total_deleted
            try:
                action()
                db.commit()
                total_deleted += 1
            except (StaleDataError, ObjectDeletedError) as se:
                db.rollback()
                msg = f"Concurrent modification deleting {desc} {identifier}: {se}";
                logger.warning(msg)
                errors.append(msg)
            except Exception as e:  # noqa
                db.rollback()
                msg = f"Failed to delete {desc} {identifier}: {e}";
                logger.error(msg)
                errors.append(msg)

        if "agents" in resource_types:
            for agent in db.query(models.Agent).filter(models.Agent.organization_id == organization_id).all():
                _safe_delete("agent", str(agent.agent_id), lambda a=agent: crud.delete_agent(db, a.agent_id))

        if "keywords" in resource_types:
            for keyword in db.query(models.Keyword).filter(models.Keyword.organization_id == organization_id).all():
                _safe_delete("keyword", str(keyword.keyword_id), lambda k=keyword: crud.delete_keyword(db, k.keyword_id))

        if "memory_blocks" in resource_types:
            for mb in db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == organization_id).all():
                _safe_delete("memory_block", str(mb.id), lambda m=mb: crud.delete_memory_block(db, m.id))

        operation.status = "completed" if not errors else "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_deleted": total_deleted, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}
        db.commit()
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        if 'operation' in locals() and operation:
            operation.status = "failed"
            operation.finished_at = datetime.now(timezone.utc)
            operation.error_log = {"message": str(e)}
            try:
                db.commit()
            except Exception:
                pass
        logger.error(f"Error during bulk delete operation {operation_id}: {e}")

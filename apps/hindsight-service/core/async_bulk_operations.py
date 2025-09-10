"""
Improved async bulk operations system.

Replaces the basic threading approach with a proper async task system
that provides better scalability, monitoring, and error handling.
"""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError, ObjectDeletedError

from core.db import models, crud
from core.audit import log_bulk_operation, AuditAction, AuditStatus
from core.db.database import get_db_session_local

logger = logging.getLogger(__name__)


class BulkOperationTask:
    """Represents a bulk operation task with async execution."""

    def __init__(self, operation_id: uuid.UUID, task_type: str, actor_user_id: uuid.UUID,
                 organization_id: uuid.UUID, payload: Dict[str, Any]):
        self.operation_id = operation_id
        self.task_type = task_type
        self.actor_user_id = actor_user_id
        self.organization_id = organization_id
        self.payload = payload
        self.status = "pending"
        self.progress = 0
        self.errors = []

    async def execute(self) -> Dict[str, Any]:
        """Execute the bulk operation asynchronously."""
        try:
            async with get_async_db_session() as db:
                return await self._execute_operation(db)
        except Exception as e:
            logger.error(f"Error executing bulk operation {self.operation_id}: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_operation(self, db: Session) -> Dict[str, Any]:
        """Execute the specific operation type."""
        if self.task_type == "bulk_move":
            return await self._perform_bulk_move(db)
        elif self.task_type == "bulk_delete":
            return await self._perform_bulk_delete(db)
        else:
            raise ValueError(f"Unknown task type: {self.task_type}")

    async def _perform_bulk_move(self, db: Session) -> Dict[str, Any]:
        """Perform bulk move operation with proper async handling."""
        operation = crud.get_bulk_operation(db, self.operation_id)
        if not operation:
            return {"status": "failed", "error": "Operation not found"}

        operation.status = "running"
        operation.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(operation)

        destination_org_id = self.payload.get("destination_organization_id")
        destination_owner_id = self.payload.get("destination_owner_user_id")
        resource_types = self.payload.get("resource_types", ["agents", "memory_blocks", "keywords"])

        total_moved = 0
        errors = []

        # Process each resource type
        for resource_type in resource_types:
            moved_count = await self._process_resource_type(
                db, resource_type, self.organization_id,
                destination_org_id, destination_owner_id, errors
            )
            total_moved += moved_count

        # Update operation status
        operation.status = "completed" if not errors else "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_moved": total_moved, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}

        db.commit()

        # Log completion
        try:
            log_bulk_operation(
                db,
                actor_user_id=self.actor_user_id,
                organization_id=self.organization_id,
                bulk_operation_id=self.operation_id,
                action=AuditAction.BULK_OPERATION_COMPLETE,
                status=AuditStatus.SUCCESS if not errors else AuditStatus.FAILURE,
                metadata={"total_moved": total_moved, "errors_count": len(errors)},
            )
        except Exception:
            pass

        return {
            "status": operation.status,
            "total_moved": total_moved,
            "errors_count": len(errors)
        }

    async def _perform_bulk_delete(self, db: Session) -> Dict[str, Any]:
        """Perform bulk delete operation with proper async handling."""
        operation = crud.get_bulk_operation(db, self.operation_id)
        if not operation:
            return {"status": "failed", "error": "Operation not found"}

        operation.status = "running"
        operation.started_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(operation)

        resource_types = self.payload.get("resource_types", ["agents", "memory_blocks", "keywords"])
        total_deleted = 0
        errors = []

        # Process each resource type
        for resource_type in resource_types:
            deleted_count = await self._delete_resource_type(
                db, resource_type, self.organization_id, errors
            )
            total_deleted += deleted_count

        # Update operation status
        operation.status = "completed" if not errors else "failed"
        operation.finished_at = datetime.now(timezone.utc)
        operation.result_summary = {"total_deleted": total_deleted, "errors_count": len(errors)}
        if errors:
            operation.error_log = {"errors": errors}

        db.commit()

        # Log completion
        try:
            log_bulk_operation(
                db,
                actor_user_id=self.actor_user_id,
                organization_id=self.organization_id,
                bulk_operation_id=self.operation_id,
                action=AuditAction.BULK_OPERATION_COMPLETE,
                status=AuditStatus.SUCCESS if not errors else AuditStatus.FAILURE,
                metadata={"total_deleted": total_deleted, "errors_count": len(errors)},
            )
        except Exception:
            pass

        return {
            "status": operation.status,
            "total_deleted": total_deleted,
            "errors_count": len(errors)
        }

    async def _process_resource_type(self, db: Session, resource_type: str,
                                   org_id: uuid.UUID, dest_org_id: Optional[uuid.UUID],
                                   dest_owner_id: Optional[uuid.UUID],
                                   errors: list) -> int:
        """Process a specific resource type for bulk move."""
        if resource_type == "agents":
            return await self._move_agents(db, org_id, dest_org_id, dest_owner_id, errors)
        elif resource_type == "memory_blocks":
            return await self._move_memory_blocks(db, org_id, dest_org_id, dest_owner_id, errors)
        elif resource_type == "keywords":
            return await self._move_keywords(db, org_id, dest_org_id, dest_owner_id, errors)
        return 0

    async def _delete_resource_type(self, db: Session, resource_type: str,
                                  org_id: uuid.UUID, errors: list) -> int:
        """Process a specific resource type for bulk delete."""
        if resource_type == "agents":
            return await self._delete_agents(db, org_id, errors)
        elif resource_type == "memory_blocks":
            return await self._delete_memory_blocks(db, org_id, errors)
        elif resource_type == "keywords":
            return await self._delete_keywords(db, org_id, errors)
        return 0

    async def _move_agents(self, db: Session, org_id: uuid.UUID,
                          dest_org_id: Optional[uuid.UUID], dest_owner_id: Optional[uuid.UUID],
                          errors: list) -> int:
        """Move agents with proper error handling."""
        agents = db.query(models.Agent).filter(models.Agent.organization_id == org_id).all()
        moved_count = 0

        for agent in agents:
            try:
                agent.organization_id = dest_org_id
                agent.owner_user_id = dest_owner_id
                db.commit()
                moved_count += 1
            except (StaleDataError, ObjectDeletedError) as e:
                db.rollback()
                errors.append(f"Concurrent modification for agent {agent.agent_id}: {e}")
            except Exception as e:
                db.rollback()
                errors.append(f"Failed to move agent {agent.agent_id}: {e}")
        
        return moved_count

    async def _move_memory_blocks(self, db: Session, org_id: uuid.UUID,
                                 dest_org_id: Optional[uuid.UUID], dest_owner_id: Optional[uuid.UUID],
                                 errors: list) -> int:
        """Move memory blocks with proper error handling."""
        memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).all()
        moved_count = 0

        for mb in memory_blocks:
            try:
                mb.organization_id = dest_org_id
                mb.owner_user_id = dest_owner_id
                db.commit()
                moved_count += 1
            except (StaleDataError, ObjectDeletedError) as e:
                db.rollback()
                errors.append(f"Concurrent modification for memory block {mb.id}: {e}")
            except Exception as e:
                db.rollback()
                errors.append(f"Failed to move memory block {mb.id}: {e}")
        
        return moved_count

    async def _move_keywords(self, db: Session, org_id: uuid.UUID,
                           dest_org_id: Optional[uuid.UUID], dest_owner_id: Optional[uuid.UUID],
                           errors: list) -> int:
        """Move keywords with proper error handling."""
        keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).all()
        moved_count = 0

        for keyword in keywords:
            try:
                keyword.organization_id = dest_org_id
                keyword.owner_user_id = dest_owner_id
                db.commit()
                moved_count += 1
            except (StaleDataError, ObjectDeletedError) as e:
                db.rollback()
                errors.append(f"Concurrent modification for keyword {keyword.keyword_id}: {e}")
            except Exception as e:
                db.rollback()
                errors.append(f"Failed to move keyword {keyword.keyword_id}: {e}")
        
        return moved_count

    async def _delete_agents(self, db: Session, org_id: uuid.UUID, errors: list) -> int:
        """Delete agents with proper error handling."""
        agents = db.query(models.Agent).filter(models.Agent.organization_id == org_id).all()
        deleted_count = 0

        for agent in agents:
            try:
                crud.delete_agent(db, agent.agent_id)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete agent {agent.agent_id}: {e}")
        
        return deleted_count

    async def _delete_memory_blocks(self, db: Session, org_id: uuid.UUID, errors: list) -> int:
        """Delete memory blocks with proper error handling."""
        memory_blocks = db.query(models.MemoryBlock).filter(models.MemoryBlock.organization_id == org_id).all()
        deleted_count = 0

        for mb in memory_blocks:
            try:
                crud.delete_memory_block(db, mb.id)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete memory block {mb.id}: {e}")
        
        return deleted_count

    async def _delete_keywords(self, db: Session, org_id: uuid.UUID, errors: list) -> int:
        """Delete keywords with proper error handling."""
        keywords = db.query(models.Keyword).filter(models.Keyword.organization_id == org_id).all()
        deleted_count = 0

        for keyword in keywords:
            try:
                crud.delete_keyword(db, keyword.keyword_id)
                deleted_count += 1
            except Exception as e:
                errors.append(f"Failed to delete keyword {keyword.keyword_id}: {e}")
        
        return deleted_count


class AsyncBulkOperationsManager:
    """Manages async bulk operations with proper task queuing and monitoring."""

    def __init__(self):
        self._running_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        self._task_results: Dict[uuid.UUID, Dict[str, Any]] = {}

    async def submit_task(self, operation_id: uuid.UUID, task_type: str,
                         actor_user_id: uuid.UUID, organization_id: uuid.UUID,
                         payload: Dict[str, Any]) -> None:
        """Submit a bulk operation task for async execution."""
        task = BulkOperationTask(operation_id, task_type, actor_user_id, organization_id, payload)

        # Create async task
        asyncio_task = asyncio.create_task(task.execute())
        self._running_tasks[operation_id] = asyncio_task

        # Set up completion callback
        asyncio_task.add_done_callback(
            lambda t, op_id=operation_id: self._on_task_complete(op_id, t)
        )

    def _on_task_complete(self, operation_id: uuid.UUID, task: asyncio.Task) -> None:
        """Handle task completion."""
        try:
            result = task.result()
            self._task_results[operation_id] = result
        except Exception as e:
            logger.error(f"Task {operation_id} failed with exception: {e}")
            self._task_results[operation_id] = {"status": "failed", "error": str(e)}
        finally:
            # Clean up completed task
            self._running_tasks.pop(operation_id, None)

    def get_task_status(self, operation_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get the status of a bulk operation task."""
        if operation_id in self._running_tasks:
            return {"status": "running"}

        if operation_id in self._task_results:
            return self._task_results[operation_id]

        return None

    def cancel_task(self, operation_id: uuid.UUID) -> bool:
        """Cancel a running bulk operation task."""
        if operation_id in self._running_tasks:
            task = self._running_tasks[operation_id]
            task.cancel()
            return True
        return False

    def get_running_tasks_count(self) -> int:
        """Get the count of currently running tasks."""
        return len(self._running_tasks)


# Global manager instance
_bulk_operations_manager = AsyncBulkOperationsManager()


@asynccontextmanager
async def get_async_db_session():
    """Get an async database session."""
    SessionLocal = get_db_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def execute_bulk_operation_async(operation_id: uuid.UUID, task_type: str,
                                     actor_user_id: uuid.UUID, organization_id: uuid.UUID,
                                     payload: Dict[str, Any]) -> None:
    """Execute a bulk operation asynchronously using the manager."""
    await _bulk_operations_manager.submit_task(
        operation_id, task_type, actor_user_id, organization_id, payload
    )


def get_bulk_operation_status(operation_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    """Get the status of a bulk operation."""
    return _bulk_operations_manager.get_task_status(operation_id)


def cancel_bulk_operation(operation_id: uuid.UUID) -> bool:
    """Cancel a running bulk operation."""
    return _bulk_operations_manager.cancel_task(operation_id)


def get_running_bulk_operations_count() -> int:
    """Get the count of currently running bulk operations."""
    return _bulk_operations_manager.get_running_tasks_count()

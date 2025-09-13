"""
Workers namespace shim for async bulk operations.

New code may import from `core.workers.async_bulk_operations`, while legacy
imports from `core.async_bulk_operations` continue to work. This module
re-exports the implementation.
"""

from core.async_bulk_operations import (  # type: ignore
    BulkOperationTask,
    AsyncBulkOperationsManager,
    get_async_db_session,
    execute_bulk_operation_async,
    get_bulk_operation_status,
    cancel_bulk_operation,
    get_running_bulk_operations_count,
)

__all__ = [
    "BulkOperationTask",
    "AsyncBulkOperationsManager",
    "get_async_db_session",
    "execute_bulk_operation_async",
    "get_bulk_operation_status",
    "cancel_bulk_operation",
    "get_running_bulk_operations_count",
]


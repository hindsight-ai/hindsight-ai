"""Regression guards for bulk-operation state-machine reconciliation (#76).

Three concerns this file pins:

1. **Worker-crash → DB transitions to "failed"**: when a bulk-operation
   worker raises an uncaught exception mid-execution, the DB row MUST
   transition to a terminal state (`failed`) before the coroutine
   returns. Pre-#76 the worker only recorded "failed" in the in-memory
   dict and left the DB row stuck at `running` forever.

2. **Cancel reconciliation**: `cancel_task` records `cancelled` in the
   in-memory `_task_results` BEFORE the task callback fires, so the
   `asyncio.CancelledError` propagating through `_on_task_complete`
   does not clobber the cancel state with "failed".

3. **Duplicate `GET /admin/operations/{operation_id}` registration**:
   the dummy 403-only route at `bulk_operations.py:267` (which used to
   shadow the real implementation at line 350) is removed. Verifying
   only one registration remains.
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi.routing import APIRoute

from core.async_bulk_operations import (
    AsyncBulkOperationsManager,
    BulkOperationTask,
)
from core.db import models, schemas, crud


def test_worker_crash_transitions_db_row_to_failed():
    """Worker raises mid-execution → DB row must become "failed", not stay "running".

    Mock-based unit test (no real DB) — verifies the except-branch in
    BulkOperationTask.execute opens a NEW session and writes a terminal
    status. Pre-#76 there was no such write.
    """
    from unittest.mock import patch, MagicMock, AsyncMock
    from contextlib import asynccontextmanager

    op_id = uuid.uuid4()

    # Track DB mutations on the operation row.
    fake_op = MagicMock(status="running")
    fake_op.error_log = None
    fake_op.finished_at = None

    # Mock the second `async with get_async_db_session()` context (the
    # except-branch). Its db.commit() should be called after status="failed".
    fake_db = MagicMock()
    fake_db.commit = MagicMock()

    @asynccontextmanager
    async def fake_session():
        yield fake_db

    task = BulkOperationTask(
        operation_id=op_id,
        task_type="bulk_move",
        actor_user_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        payload={},
    )

    async def _explode(*_args, **_kwargs):
        raise RuntimeError("simulated worker crash")

    task._execute_operation = _explode  # type: ignore

    with patch("core.async_bulk_operations.get_async_db_session", fake_session), \
         patch("core.async_bulk_operations.crud.get_bulk_operation", return_value=fake_op):
        result = asyncio.new_event_loop().run_until_complete(task.execute())

    assert result["status"] == "failed", result
    assert fake_op.status == "failed", (
        f"REGRESSION (#76): worker except-branch should set DB status to "
        f"'failed', got {fake_op.status!r}. Pre-#76 the row stayed 'running' "
        f"forever because the except branch only updated the in-memory dict."
    )
    assert fake_op.finished_at is not None, (
        "DB terminal-state write must include finished_at."
    )
    assert fake_op.error_log == {"errors": ["simulated worker crash"]}, (
        f"error_log should record the crash reason; got {fake_op.error_log!r}"
    )
    fake_db.commit.assert_called(), (
        "The except-branch must call db.commit() to persist the terminal state."
    )


def test_cancel_task_records_cancelled_state_in_memory():
    """cancel_task() must record "cancelled" so the post-cancel callback
    does not clobber it with "failed" (CancelledError default)."""
    mgr = AsyncBulkOperationsManager()
    op_id = uuid.uuid4()

    async def _slow():
        await asyncio.sleep(60)
        return {"status": "completed"}

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(_slow())
        mgr._running_tasks[op_id] = task

        # Cancel — should record "cancelled" in _task_results.
        result = mgr.cancel_task(op_id)
        assert result is True
        assert mgr._task_results[op_id] == {"status": "cancelled"}

        # Drive the cancellation through the asyncio loop.
        async def _wait():
            try:
                await task
            except asyncio.CancelledError:
                pass
        loop.run_until_complete(_wait())
        # Manually invoke the callback (in real usage asyncio fires it).
        mgr._on_task_complete(op_id, task)

        # Must remain "cancelled" — _on_task_complete must not clobber it.
        assert mgr._task_results[op_id] == {"status": "cancelled"}, (
            "REGRESSION (#76): cancel state was clobbered by _on_task_complete; "
            "the asyncio.CancelledError propagating through the callback must "
            "not overwrite the explicit cancel record."
        )
        assert op_id not in mgr._running_tasks, (
            "Running-tasks dict should be cleaned up after cancellation completes."
        )
    finally:
        loop.close()


def test_on_task_complete_records_cancelled_for_uncancelled_callers():
    """If a task is cancelled externally (not via cancel_task), the callback's
    asyncio.CancelledError branch records 'cancelled' as the result."""
    mgr = AsyncBulkOperationsManager()
    op_id = uuid.uuid4()

    async def _slow():
        await asyncio.sleep(60)

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(_slow())
        mgr._running_tasks[op_id] = task
        # Cancel directly (bypass cancel_task — simulates external cancel)
        task.cancel()
        async def _wait():
            try:
                await task
            except asyncio.CancelledError:
                pass
        loop.run_until_complete(_wait())
        mgr._on_task_complete(op_id, task)
        assert mgr._task_results[op_id] == {"status": "cancelled"}, (
            f"_on_task_complete should record cancelled for an externally-"
            f"cancelled task; got {mgr._task_results[op_id]!r}"
        )
    finally:
        loop.close()


def test_on_task_complete_records_failed_for_unexpected_exception():
    """If a task raises a non-CancelledError, the callback records 'failed'."""
    mgr = AsyncBulkOperationsManager()
    op_id = uuid.uuid4()

    async def _explode():
        raise RuntimeError("boom")

    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(_explode())
        mgr._running_tasks[op_id] = task
        loop.run_until_complete(asyncio.gather(task, return_exceptions=True))
        mgr._on_task_complete(op_id, task)
        result = mgr._task_results[op_id]
        assert result["status"] == "failed"
        assert "boom" in result.get("error", ""), result
    finally:
        loop.close()


def test_admin_operations_route_registered_only_once():
    """The dummy 403 route at bulk_operations.py:267 used to shadow the real
    implementation. Verify only one registration remains."""
    from core.api.bulk_operations import router

    # The router has prefix "/bulk-operations" — the registered path is the
    # combined string. Match on the suffix to be flexible.
    matching = [
        r for r in router.routes
        if isinstance(r, APIRoute)
        and r.path.endswith("/admin/operations/{operation_id}")
        and r.methods == {"GET"}
    ]
    assert len(matching) == 1, (
        f"REGRESSION (#76): expected exactly one GET /admin/operations/{{operation_id}} "
        f"route, found {len(matching)}. The dummy 403-only route at "
        f"bulk_operations.py:267 must be removed (it shadowed the real "
        f"implementation at line 350+ which had proper permission checks)."
    )

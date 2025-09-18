"""
Unit tests for the async_bulk_operations module.
Tests the new async bulk operations system that replaces the threading approach.
"""
import uuid
import pytest
pytest.importorskip("pytest_asyncio")
pytest.importorskip("anyio")

import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
import anyio

from core import async_bulk_operations
from core.async_bulk_operations import (
    BulkOperationTask, 
    AsyncBulkOperationsManager,
    execute_bulk_operation_async,
    get_bulk_operation_status,
    cancel_bulk_operation,
    get_running_bulk_operations_count,
    get_async_db_session
)
from core.db import models


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = Mock()
    db.query.return_value.filter.return_value.all.return_value = []
    db.commit = Mock()
    db.rollback = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def sample_operation_data():
    """Sample data for bulk operations."""
    return {
        "operation_id": uuid.uuid4(),
        "task_type": "bulk_move",
        "actor_user_id": uuid.uuid4(),
        "organization_id": uuid.uuid4(),
        "payload": {
            "destination_organization_id": str(uuid.uuid4()),
            "resource_types": ["agents", "keywords", "memory_blocks"]
        }
    }


class TestBulkOperationTask:
    """Test the BulkOperationTask class."""

    def test_task_initialization(self, sample_operation_data):
        """Test that BulkOperationTask initializes correctly."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type=sample_operation_data["task_type"],
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )
        
        assert task.operation_id == sample_operation_data["operation_id"]
        assert task.task_type == sample_operation_data["task_type"]
        assert task.actor_user_id == sample_operation_data["actor_user_id"]
        assert task.organization_id == sample_operation_data["organization_id"]
        assert task.payload == sample_operation_data["payload"]
        assert task.status == "pending"
        assert task.progress == 0
        assert task.errors == []

    @pytest.mark.asyncio
    async def test_execute_with_db_error(self, sample_operation_data):
        """Test task execution when database session fails."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type=sample_operation_data["task_type"],
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )

        # Mock get_async_db_session to raise an exception
        with patch('core.async_bulk_operations.get_async_db_session') as mock_get_db:
            mock_get_db.side_effect = Exception("Database connection failed")
            
            result = await task.execute()
            
            assert result["status"] == "failed"
            assert "Database connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_unknown_task_type(self, sample_operation_data, mock_db):
        """Test execution with unknown task type."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="unknown_task",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )

        with patch('core.async_bulk_operations.get_async_db_session') as mock_get_db:
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await task.execute()
            
            assert result["status"] == "failed"
            assert "Unknown task type: unknown_task" in result["error"]

    @pytest.mark.asyncio
    async def test_bulk_move_operation_not_found(self, sample_operation_data, mock_db):
        """Test bulk move when operation is not found in database."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_move",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )

        # Mock crud.get_bulk_operation to return None
        with patch('core.async_bulk_operations.get_async_db_session') as mock_get_db, \
             patch('core.async_bulk_operations.crud.get_bulk_operation') as mock_get_op:
            
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_op.return_value = None
            
            result = await task.execute()
            
            assert result["status"] == "failed"
            assert result["error"] == "Operation not found"

    @pytest.mark.asyncio
    async def test_bulk_move_success(self, sample_operation_data, mock_db):
        """Test successful bulk move operation."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_move",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )

        # Create mock operation
        mock_operation = Mock()
        mock_operation.status = "pending"
        mock_operation.started_at = None
        mock_operation.finished_at = None
        mock_operation.result_summary = None
        mock_operation.error_log = None

        # Mock agents for move
        mock_agents = [
            Mock(agent_id=uuid.uuid4(), organization_id=sample_operation_data["organization_id"]),
            Mock(agent_id=uuid.uuid4(), organization_id=sample_operation_data["organization_id"])
        ]

        with patch('core.async_bulk_operations.get_async_db_session') as mock_get_db, \
             patch('core.async_bulk_operations.crud.get_bulk_operation') as mock_get_op, \
             patch('core.async_bulk_operations.log_bulk_operation') as mock_log:
            
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_op.return_value = mock_operation
            
            # Setup database query mocks for different resource types
            def query_side_effect(model_class):
                query_mock = Mock()
                if model_class == models.Agent:
                    query_mock.filter.return_value.all.return_value = mock_agents
                else:
                    query_mock.filter.return_value.all.return_value = []
                return query_mock
            
            mock_db.query.side_effect = query_side_effect
            
            result = await task.execute()
            
            # Verify operation was updated correctly
            assert mock_operation.status == "completed"
            assert mock_operation.started_at is not None
            assert mock_operation.finished_at is not None
            assert mock_operation.result_summary["total_moved"] == 2  # 2 agents moved
            mock_log.assert_called()

    @pytest.mark.asyncio 
    async def test_bulk_delete_success(self, sample_operation_data, mock_db):
        """Test successful bulk delete operation."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_delete",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload={"resource_types": ["agents"]}
        )

        # Create mock operation
        mock_operation = Mock()
        mock_operation.status = "pending"

        # Mock agents for deletion
        mock_agents = [Mock(agent_id=uuid.uuid4()) for _ in range(3)]

        with patch('core.async_bulk_operations.get_async_db_session') as mock_get_db, \
             patch('core.async_bulk_operations.crud.get_bulk_operation') as mock_get_op, \
             patch('core.async_bulk_operations.crud.delete_agent') as mock_delete, \
             patch('core.async_bulk_operations.log_bulk_operation') as mock_log:
            
            mock_get_db.return_value.__aenter__ = AsyncMock(return_value=mock_db)
            mock_get_db.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_op.return_value = mock_operation
            mock_delete.return_value = True
            
            # Setup database query for agents
            mock_db.query.return_value.filter.return_value.all.return_value = mock_agents
            
            result = await task.execute()
            
            # Verify deletion was called for each agent
            assert mock_delete.call_count == 3
            assert mock_operation.status == "completed"

    @pytest.mark.asyncio
    async def test_move_memory_blocks_success(self, sample_operation_data, mock_db):
        """Memory blocks should be reassigned without errors."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_move",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"],
        )

        blocks = [Mock(id=uuid.uuid4()) for _ in range(2)]
        mock_db.query.return_value.filter.return_value.all.return_value = blocks

        errors: list[str] = []
        moved = await task._move_memory_blocks(
            mock_db,
            sample_operation_data["organization_id"],
            uuid.uuid4(),
            uuid.uuid4(),
            errors,
        )

        assert moved == 2
        assert errors == []

    @pytest.mark.asyncio
    async def test_move_keywords_records_generic_failure(self, sample_operation_data, mock_db):
        """Generic exceptions while moving keywords are captured and logged."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_move",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"],
        )

        keywords = [Mock(keyword_id=uuid.uuid4()) for _ in range(2)]
        mock_db.query.return_value.filter.return_value.all.return_value = keywords

        commit_calls = {"count": 0}

        def commit_side_effect():
            commit_calls["count"] += 1
            if commit_calls["count"] >= 2:
                raise Exception("boom")

        mock_db.commit.side_effect = commit_side_effect

        errors: list[str] = []
        moved = await task._move_keywords(
            mock_db,
            sample_operation_data["organization_id"],
            uuid.uuid4(),
            uuid.uuid4(),
            errors,
        )

        assert moved == 1
        assert len(errors) == 1
        assert "Failed to move keyword" in errors[0]
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_memory_blocks_records_errors(self, sample_operation_data, mock_db):
        """Deleting memory blocks surfaces exceptions as error entries."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_delete",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload={"resource_types": ["memory_blocks"]},
        )

        blocks = [Mock(id=uuid.uuid4()) for _ in range(2)]
        mock_db.query.return_value.filter.return_value.all.return_value = blocks

        with patch('core.async_bulk_operations.crud.delete_memory_block') as mock_delete:
            mock_delete.side_effect = [True, Exception("fail")]
            errors: list[str] = []
            deleted = await task._delete_memory_blocks(mock_db, sample_operation_data["organization_id"], errors)

        assert deleted == 1
        assert len(errors) == 1
        assert "Failed to delete memory block" in errors[0]

    @pytest.mark.asyncio
    async def test_delete_keywords_success(self, sample_operation_data, mock_db):
        """Keyword deletion success path increments counter."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_delete",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload={"resource_types": ["keywords"]},
        )

        keywords = [Mock(keyword_id=uuid.uuid4()) for _ in range(3)]
        mock_db.query.return_value.filter.return_value.all.return_value = keywords

        with patch('core.async_bulk_operations.crud.delete_keyword') as mock_delete:
            mock_delete.return_value = True
            errors: list[str] = []
            deleted = await task._delete_keywords(mock_db, sample_operation_data["organization_id"], errors)

        assert deleted == 3
        assert errors == []


class TestAsyncBulkOperationsManager:
    """Test the AsyncBulkOperationsManager class."""

    def test_manager_initialization(self):
        """Test that the manager initializes correctly."""
        manager = AsyncBulkOperationsManager()
        
        assert manager._running_tasks == {}
        assert manager._task_results == {}

    @pytest.mark.asyncio
    async def test_submit_task(self, sample_operation_data):
        """Test submitting a task to the manager."""
        manager = AsyncBulkOperationsManager()
        
        with patch.object(BulkOperationTask, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = {"status": "completed"}
            
            await manager.submit_task(
                operation_id=sample_operation_data["operation_id"],
                task_type=sample_operation_data["task_type"],
                actor_user_id=sample_operation_data["actor_user_id"],
                organization_id=sample_operation_data["organization_id"],
                payload=sample_operation_data["payload"]
            )
            
            # Task should be in running tasks initially
            assert sample_operation_data["operation_id"] in manager._running_tasks
            
            # Wait for task completion
            await asyncio.sleep(0.1)
            
            # Task should be completed and moved to results
            assert sample_operation_data["operation_id"] not in manager._running_tasks
            assert sample_operation_data["operation_id"] in manager._task_results
            assert manager._task_results[sample_operation_data["operation_id"]]["status"] == "completed"

    def test_get_task_status_running(self, sample_operation_data):
        """Test getting status of a running task."""
        manager = AsyncBulkOperationsManager()
        
        # Mock a running task
        mock_task = Mock()
        manager._running_tasks[sample_operation_data["operation_id"]] = mock_task
        
        status = manager.get_task_status(sample_operation_data["operation_id"])
        
        assert status == {"status": "running"}

    def test_get_task_status_completed(self, sample_operation_data):
        """Test getting status of a completed task."""
        manager = AsyncBulkOperationsManager()
        
        # Mock a completed task result
        expected_result = {"status": "completed", "total_moved": 5}
        manager._task_results[sample_operation_data["operation_id"]] = expected_result
        
        status = manager.get_task_status(sample_operation_data["operation_id"])
        
        assert status == expected_result

    def test_get_task_status_not_found(self, sample_operation_data):
        """Test getting status of a non-existent task."""
        manager = AsyncBulkOperationsManager()
        
        status = manager.get_task_status(sample_operation_data["operation_id"])
        
        assert status is None

    def test_cancel_task_success(self, sample_operation_data):
        """Test successfully canceling a running task."""
        manager = AsyncBulkOperationsManager()
        
        # Mock a running task
        mock_task = Mock()
        mock_task.cancel = Mock()
        manager._running_tasks[sample_operation_data["operation_id"]] = mock_task
        
        result = manager.cancel_task(sample_operation_data["operation_id"])
        
        assert result is True
        mock_task.cancel.assert_called_once()

    def test_cancel_task_not_found(self, sample_operation_data):
        """Test canceling a non-existent task."""
        manager = AsyncBulkOperationsManager()
        
        result = manager.cancel_task(sample_operation_data["operation_id"])
        
        assert result is False

    def test_get_running_tasks_count(self, sample_operation_data):
        """Test getting the count of running tasks."""
        manager = AsyncBulkOperationsManager()
        
        # Initially should be 0
        assert manager.get_running_tasks_count() == 0
        
        # Add some mock running tasks
        manager._running_tasks[sample_operation_data["operation_id"]] = Mock()
        manager._running_tasks[uuid.uuid4()] = Mock()
        
        assert manager.get_running_tasks_count() == 2


class TestModuleFunctions:
    """Test the module-level functions."""

    @pytest.mark.asyncio
    async def test_execute_bulk_operation_async(self, sample_operation_data):
        """Test the execute_bulk_operation_async function."""
        with patch('core.async_bulk_operations._bulk_operations_manager.submit_task') as mock_submit:
            mock_submit.return_value = None
            
            await execute_bulk_operation_async(
                operation_id=sample_operation_data["operation_id"],
                task_type=sample_operation_data["task_type"],
                actor_user_id=sample_operation_data["actor_user_id"],
                organization_id=sample_operation_data["organization_id"],
                payload=sample_operation_data["payload"]
            )
            
            mock_submit.assert_called_once_with(
                sample_operation_data["operation_id"],
                sample_operation_data["task_type"],
                sample_operation_data["actor_user_id"],
                sample_operation_data["organization_id"],
                sample_operation_data["payload"]
            )

    def test_get_bulk_operation_status(self, sample_operation_data):
        """Test the get_bulk_operation_status function."""
        expected_status = {"status": "completed"}
        
        with patch('core.async_bulk_operations._bulk_operations_manager.get_task_status') as mock_get_status:
            mock_get_status.return_value = expected_status
            
            status = get_bulk_operation_status(sample_operation_data["operation_id"])
            
            assert status == expected_status
            mock_get_status.assert_called_once_with(sample_operation_data["operation_id"])

    def test_cancel_bulk_operation(self, sample_operation_data):
        """Test the cancel_bulk_operation function."""
        with patch('core.async_bulk_operations._bulk_operations_manager.cancel_task') as mock_cancel:
            mock_cancel.return_value = True
            
            result = cancel_bulk_operation(sample_operation_data["operation_id"])
            
            assert result is True
            mock_cancel.assert_called_once_with(sample_operation_data["operation_id"])

    def test_get_running_bulk_operations_count(self):
        """Test the get_running_bulk_operations_count function."""
        with patch('core.async_bulk_operations._bulk_operations_manager.get_running_tasks_count') as mock_count:
            mock_count.return_value = 3
            
            count = get_running_bulk_operations_count()
            
            assert count == 3
            mock_count.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_async_db_session(self):
        """Test the get_async_db_session context manager."""
        mock_session = Mock()
        
        with patch('core.async_bulk_operations.get_db_session_local') as mock_get_session_local:
            mock_session_local = Mock()
            mock_session_local.return_value = mock_session
            mock_get_session_local.return_value = mock_session_local
            
            async with get_async_db_session() as db:
                assert db == mock_session
            
            # Verify session was closed
            mock_session.close.assert_called_once()


class TestResourceTypeProcessing:
    """Test the resource type processing methods."""

    @pytest.mark.asyncio
    async def test_move_agents_with_stale_data_error(self, sample_operation_data, mock_db):
        """Test moving agents when encountering stale data errors."""
        from sqlalchemy.orm.exc import StaleDataError
        
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_move",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload=sample_operation_data["payload"]
        )

        # Create mock agents, one that will cause an error
        mock_agent1 = Mock()
        mock_agent1.agent_id = uuid.uuid4()
        mock_agent2 = Mock()
        mock_agent2.agent_id = uuid.uuid4()
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_agent1, mock_agent2]
        
        # First commit succeeds, second fails with StaleDataError
        commit_call_count = 0
        def commit_side_effect():
            nonlocal commit_call_count
            commit_call_count += 1
            if commit_call_count == 2:
                raise StaleDataError("Stale data", None, None)
        
        mock_db.commit.side_effect = commit_side_effect

        errors = []
        dest_org_id = uuid.uuid4()
        dest_owner_id = uuid.uuid4()
        
        moved_count = await task._move_agents(mock_db, sample_operation_data["organization_id"], dest_org_id, dest_owner_id, errors)
        
        # Should have moved 1 agent successfully, 1 failed
        assert moved_count == 1
        assert len(errors) == 1
        assert "Concurrent modification" in errors[0]
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_agents_success(self, sample_operation_data, mock_db):
        """Test successful agent deletion."""
        task = BulkOperationTask(
            operation_id=sample_operation_data["operation_id"],
            task_type="bulk_delete",
            actor_user_id=sample_operation_data["actor_user_id"],
            organization_id=sample_operation_data["organization_id"],
            payload={"resource_types": ["agents"]}
        )

        # Mock agents for deletion
        mock_agents = [Mock(agent_id=uuid.uuid4()) for _ in range(2)]
        mock_db.query.return_value.filter.return_value.all.return_value = mock_agents
        
        with patch('core.async_bulk_operations.crud.delete_agent') as mock_delete:
            mock_delete.return_value = True
            
            errors = []
            deleted_count = await task._delete_agents(mock_db, sample_operation_data["organization_id"], errors)
            
            assert deleted_count == 2
            assert len(errors) == 0
            assert mock_delete.call_count == 2

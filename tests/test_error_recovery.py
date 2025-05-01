"""Tests for error recovery system."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.error_recovery import ErrorRecovery
from app.models.task import Task

@pytest.mark.anyio
async def test_recover_stuck_tasks(test_db: AsyncSession):
    """
    Tests that stuck tasks are correctly recovered based on their retry count.
    
    Creates multiple tasks in a "running" state older than the allowed age, invokes the recovery process, and asserts that tasks below the maximum retry count are reset for retry while those exceeding the limit are marked as failed.
    """
    # Create stuck tasks
    stuck_tasks = []
    for i in range(3):
        task = Task(
            id=str(uuid4()),
            type=f"test_{i}",
            status="running",
            progress=50.0,
            input_data={"test": f"data_{i}"},
            updated_at=datetime.utcnow() - timedelta(minutes=60),  # 1 hour old
            retry_count=i  # Different retry counts
        )
        stuck_tasks.append(task)
        test_db.add(task)
    await test_db.commit()

    # Run recovery
    recovery = ErrorRecovery(test_db)
    recovered = await recovery.recover_stuck_tasks(max_age_minutes=30, max_retries=2)

    assert len(recovered) == 3
    
    # Check task states
    for task in recovered:
        if task.retry_count >= 2:
            assert task.status == "failed"
            assert "max_retries_exceeded" in task.error["type"]
        else:
            assert task.status == "pending"
            assert task.progress == 0.0
            assert "Retrying task" in task.message

@pytest.mark.anyio
async def test_cleanup_incomplete_tasks(test_db: AsyncSession):
    """
    Tests that incomplete tasks are marked as failed after a system crash.
    
    Creates tasks in "pending" or "running" states, invokes the error recovery cleanup,
    and verifies that affected tasks are marked as "failed" with a "system_crash" error type.
    Also checks cleanup for both a specific agent and all agents.
    """
    # Create incomplete tasks
    agent_id = str(uuid4())
    incomplete_tasks = []
    for status in ["pending", "running"]:
        task = Task(
            id=str(uuid4()),
            agent_id=agent_id,
            type="test",
            status=status,
            progress=25.0,
            input_data={"test": "data"}
        )
        incomplete_tasks.append(task)
        test_db.add(task)
    await test_db.commit()

    # Run cleanup for specific agent
    recovery = ErrorRecovery(test_db)
    cleaned = await recovery.cleanup_incomplete_tasks(agent_id)

    assert len(cleaned) == 2
    for task in cleaned:
        assert task.status == "failed"
        assert task.error["type"] == "system_crash"

    # Run cleanup for all agents
    other_task = Task(
        id=str(uuid4()),
        agent_id=str(uuid4()),
        type="test",
        status="running",
        progress=75.0,
        input_data={"test": "data"}
    )
    test_db.add(other_task)
    await test_db.commit()

    cleaned = await recovery.cleanup_incomplete_tasks()
    assert len(cleaned) == 3

@pytest.mark.anyio
async def test_retry_failed_task(test_db: AsyncSession):
    """
    Tests that a failed task can be retried, resetting its status and incrementing the retry count.
    
    Verifies that retrying a failed task resets its status to "pending", clears errors, increments the retry count, and adds a retry message. Also checks that retrying a non-failed or non-existent task returns None.
    """
    # Create failed task
    task = Task(
        id=str(uuid4()),
        type="test",
        status="failed",
        progress=0.0,
        error={"type": "test_error", "message": "Test error"},
        retry_count=1
    )
    test_db.add(task)
    await test_db.commit()

    # Retry task
    recovery = ErrorRecovery(test_db)
    retried = await recovery.retry_failed_task(str(task.id))

    assert retried is not None
    assert retried.status == "pending"
    assert retried.progress == 0.0
    assert retried.error is None
    assert "retry" in retried.message.lower()
    assert retried.retry_count == 2

    # Try to retry non-failed task
    task.status = "running"
    await test_db.commit()
    retried = await recovery.retry_failed_task(str(task.id))
    assert retried is None

    # Try to retry non-existent task
    retried = await recovery.retry_failed_task(str(uuid4()))
    assert retried is None

@pytest.mark.anyio
async def test_recovery_monitor(test_db: AsyncSession):
    """Test recovery monitor background task."""
    # Create stuck task
    task = Task(
        id=str(uuid4()),
        type="test",
        status="running",
        progress=50.0,
        updated_at=datetime.utcnow() - timedelta(minutes=60),
        retry_count=0
    )
    test_db.add(task)
    await test_db.commit()

    # Run monitor for one iteration
    recovery = ErrorRecovery(test_db)
    await recovery.start_recovery_monitor(
        check_interval=1,  # 1 second
        max_age_minutes=30,
        max_retries=3
    )

    # Verify task was recovered
    updated_task = await test_db.get(Task, task.id)
    assert updated_task.status == "pending"
    assert updated_task.retry_count == 1 
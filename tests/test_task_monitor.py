"""Tests for task monitoring system."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.task_monitor import TaskMonitor
from app.models.task import Task
from app.models.agent import Agent
from app.core.exceptions import TaskMonitorError

@pytest.mark.anyio
async def test_monitor_task_progress(test_db: AsyncSession):
    """
    Tests updating task progress and completion for a monitored task.
    
    Creates an agent and a running task, updates the task's progress and message, and verifies that progress, status, and result fields are correctly updated as the task transitions from running to completed.
    """
    # Create agent and task
    agent = Agent(
        id=str(uuid4()),
        type="test_agent",
        status="active"
    )
    test_db.add(agent)
    
    task = Task(
        id=str(uuid4()),
        agent_id=str(agent.id),
        type="test",
        status="running",
        progress=0.0,
        input_data={"test": "data"}
    )
    test_db.add(task)
    await test_db.commit()

    # Initialize monitor
    monitor = TaskMonitor(test_db)
    
    # Update progress
    updated = await monitor.update_task_progress(
        task_id=str(task.id),
        progress=50.0,
        message="Half complete"
    )
    
    assert updated.progress == 50.0
    assert updated.message == "Half complete"
    assert updated.status == "running"
    
    # Complete task
    completed = await monitor.update_task_progress(
        task_id=str(task.id),
        progress=100.0,
        message="Task complete",
        result={"output": "test_result"}
    )
    
    assert completed.progress == 100.0
    assert completed.status == "completed"
    assert completed.result == {"output": "test_result"}

@pytest.mark.anyio
async def test_monitor_task_failure(test_db: AsyncSession):
    """
    Tests that reporting a failure on a running task updates its status to "failed" and records the error data while preserving the original progress.
    """
    # Create task
    task = Task(
        id=str(uuid4()),
        type="test",
        status="running",
        progress=25.0
    )
    test_db.add(task)
    await test_db.commit()

    # Initialize monitor
    monitor = TaskMonitor(test_db)
    
    # Report failure
    error_data = {
        "type": "test_error",
        "message": "Test failure",
        "details": {"reason": "test"}
    }
    
    failed = await monitor.report_task_failure(
        task_id=str(task.id),
        error=error_data
    )
    
    assert failed.status == "failed"
    assert failed.error == error_data
    assert failed.progress == 25.0  # Progress preserved

@pytest.mark.anyio
async def test_monitor_agent_tasks(test_db: AsyncSession):
    """
    Tests retrieval of all tasks associated with a specific agent.
    
    Creates an agent and multiple running tasks, then verifies that the task monitor
    returns all tasks for the agent with correct progress values.
    """
    # Create agent and tasks
    agent = Agent(
        id=str(uuid4()),
        type="test_agent",
        status="active"
    )
    test_db.add(agent)
    
    tasks = []
    for i in range(3):
        task = Task(
            id=str(uuid4()),
            agent_id=str(agent.id),
            type=f"test_{i}",
            status="running",
            progress=float(i * 25)
        )
        tasks.append(task)
        test_db.add(task)
    await test_db.commit()

    # Initialize monitor
    monitor = TaskMonitor(test_db)
    
    # Get agent tasks
    agent_tasks = await monitor.get_agent_tasks(str(agent.id))
    
    assert len(agent_tasks) == 3
    for i, task in enumerate(agent_tasks):
        assert task.progress == float(i * 25)

@pytest.mark.anyio
async def test_monitor_task_timeout(test_db: AsyncSession):
    """
    Tests that tasks not updated within the timeout threshold are marked as failed due to timeout, while recently updated tasks remain running.
    
    Creates two running tasks with different last update times, invokes the timeout check, and asserts that only the outdated task is marked as failed with a timeout error.
    """
    # Create old task
    old_task = Task(
        id=str(uuid4()),
        type="test",
        status="running",
        progress=50.0,
        updated_at=datetime.utcnow() - timedelta(hours=2)  # 2 hours old
    )
    test_db.add(old_task)
    
    # Create recent task
    recent_task = Task(
        id=str(uuid4()),
        type="test",
        status="running",
        progress=50.0,
        updated_at=datetime.utcnow() - timedelta(minutes=5)  # 5 minutes old
    )
    test_db.add(recent_task)
    await test_db.commit()

    # Initialize monitor
    monitor = TaskMonitor(test_db)
    
    # Check for timeouts
    timed_out = await monitor.check_task_timeouts(timeout_minutes=60)
    
    assert len(timed_out) == 1
    assert timed_out[0].id == old_task.id
    assert timed_out[0].status == "failed"
    assert timed_out[0].error["type"] == "timeout"
    
    # Verify recent task unchanged
    updated_recent = await test_db.get(Task, recent_task.id)
    assert updated_recent.status == "running"

@pytest.mark.anyio
async def test_monitor_error_handling(test_db: AsyncSession):
    """
    Tests error conditions in the TaskMonitor, including updating a non-existent task,
    providing invalid progress values, and attempting to update a completed task.
    
    Asserts that TaskMonitorError is raised with appropriate messages for each scenario.
    """
    monitor = TaskMonitor(test_db)
    
    # Test invalid task ID
    with pytest.raises(TaskMonitorError) as exc:
        await monitor.update_task_progress(
            task_id=str(uuid4()),  # Non-existent task
            progress=50.0
        )
    assert "Task not found" in str(exc.value)
    
    # Test invalid progress value
    task = Task(
        id=str(uuid4()),
        type="test",
        status="running"
    )
    test_db.add(task)
    await test_db.commit()
    
    with pytest.raises(TaskMonitorError) as exc:
        await monitor.update_task_progress(
            task_id=str(task.id),
            progress=150.0  # Invalid progress value
        )
    assert "Invalid progress value" in str(exc.value)
    
    # Test updating completed task
    task.status = "completed"
    await test_db.commit()
    
    with pytest.raises(TaskMonitorError) as exc:
        await monitor.update_task_progress(
            task_id=str(task.id),
            progress=75.0
        )
    assert "Cannot update completed task" in str(exc.value) 
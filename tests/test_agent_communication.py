"""
Integration tests for agent communication.

These tests verify the communication between different agents in the system.
"""
import pytest
from unittest.mock import AsyncMock, patch
from typing import Dict, Any, List

from core.agents.super_agent import SuperAgent
from core.agents.journey_agent import JourneyAgent
from core.agents.codifier_agent import CodifierAgent
from core.agents.test_engineer_agent import TestEngineerAgent
from core.models.message import Message
from core.models.task import Task
from core.tools.message_queue import MessageQueue

@pytest.fixture
async def message_queue():
    """Create a message queue for testing."""
    queue = MessageQueue()
    try:
        yield queue
    finally:
        await queue.clear()

@pytest.fixture
async def super_agent():
    """Create a SuperAgent instance for testing."""
    agent = SuperAgent()
    await agent.initialize()
    return agent

@pytest.fixture
async def journey_agent():
    """Create a JourneyAgent instance for testing."""
    agent = JourneyAgent()
    await agent.initialize()
    return agent

@pytest.fixture
async def codifier_agent():
    """Create a CodifierAgent instance for testing."""
    agent = CodifierAgent()
    await agent.initialize()
    return agent

@pytest.fixture
async def test_engineer_agent():
    """Create a TestEngineerAgent instance for testing."""
    agent = TestEngineerAgent()
    await agent.initialize()
    return agent

@pytest.mark.asyncio
async def test_super_agent_delegation(
    super_agent: SuperAgent,
    journey_agent: JourneyAgent,
    message_queue: MessageQueue
):
    """Test that SuperAgent can delegate tasks to JourneyAgent."""
    # Create a task
    task = Task(
        id="test-task-1",
        title="Analyze codebase",
        description="Perform initial codebase analysis",
        priority="high"
    )
    
    # SuperAgent delegates to JourneyAgent
    delegation_message = await super_agent.delegate_task(
        task=task,
        target_agent=journey_agent,
        queue=message_queue
    )
    
    assert delegation_message.status == "sent"
    assert delegation_message.target_agent_id == journey_agent.id
    
    # JourneyAgent receives the task
    received_message = await message_queue.get_message(journey_agent.id)
    assert received_message is not None
    assert received_message.task_id == task.id

@pytest.mark.asyncio
async def test_journey_agent_to_codifier(
    journey_agent: JourneyAgent,
    codifier_agent: CodifierAgent,
    message_queue: MessageQueue
):
    """Test communication from JourneyAgent to CodifierAgent."""
    # JourneyAgent creates documentation request
    request = {
        "type": "documentation",
        "files": ["test_file.py"],
        "format": "markdown"
    }
    
    # Send request to CodifierAgent
    message = await journey_agent.send_message(
        target_agent=codifier_agent,
        content=request,
        queue=message_queue
    )
    
    assert message.status == "sent"
    
    # CodifierAgent receives the request
    received = await message_queue.get_message(codifier_agent.id)
    assert received is not None
    assert received.content["type"] == "documentation"

@pytest.mark.asyncio
async def test_multi_agent_workflow(
    super_agent: SuperAgent,
    journey_agent: JourneyAgent,
    codifier_agent: CodifierAgent,
    test_engineer_agent: TestEngineerAgent,
    message_queue: MessageQueue
):
    """Test a complete workflow involving multiple agents."""
    # Create initial task
    task = Task(
        id="test-task-2",
        title="Complete feature implementation",
        description="Implement and document new feature",
        priority="high"
    )
    
    # SuperAgent starts the workflow
    await super_agent.start_workflow(task, message_queue)
    
    # JourneyAgent receives and processes task
    journey_message = await message_queue.get_message(journey_agent.id)
    assert journey_message is not None
    
    # JourneyAgent requests documentation
    await journey_agent.request_documentation(
        files=["feature.py"],
        target_agent=codifier_agent,
        queue=message_queue
    )
    
    # CodifierAgent receives documentation request
    codifier_message = await message_queue.get_message(codifier_agent.id)
    assert codifier_message is not None
    
    # CodifierAgent completes documentation and notifies TestEngineer
    await codifier_agent.send_completion_notice(
        target_agent=test_engineer_agent,
        queue=message_queue
    )
    
    # TestEngineer receives notification
    test_engineer_message = await message_queue.get_message(test_engineer_agent.id)
    assert test_engineer_message is not None
    
    # Verify workflow completion notification reaches SuperAgent
    completion_message = await message_queue.get_message(super_agent.id)
    assert completion_message is not None
    assert completion_message.type == "workflow_complete"

@pytest.mark.asyncio
async def test_error_handling(
    super_agent: SuperAgent,
    journey_agent: JourneyAgent,
    message_queue: MessageQueue
):
    """Test error handling in agent communication."""
    # Simulate network error
    with patch.object(message_queue, 'send_message', side_effect=Exception("Network error")):
        with pytest.raises(Exception):
            await super_agent.send_message(
                target_agent=journey_agent,
                content={"type": "task"},
                queue=message_queue
            )
    
    # Verify error recovery
    error_message = await message_queue.get_message(super_agent.id)
    assert error_message is not None
    assert error_message.type == "error"

@pytest.mark.asyncio
async def test_message_priority(
    super_agent: SuperAgent,
    journey_agent: JourneyAgent,
    message_queue: MessageQueue
):
    """Test message priority handling."""
    # Send messages with different priorities
    low_priority = await super_agent.send_message(
        target_agent=journey_agent,
        content={"type": "task", "priority": "low"},
        queue=message_queue
    )
    
    high_priority = await super_agent.send_message(
        target_agent=journey_agent,
        content={"type": "task", "priority": "high"},
        queue=message_queue
    )
    
    # Verify high priority message is received first
    first_received = await message_queue.get_message(journey_agent.id)
    assert first_received.id == high_priority.id
    
    second_received = await message_queue.get_message(journey_agent.id)
    assert second_received.id == low_priority.id 
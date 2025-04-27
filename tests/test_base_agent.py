"""Tests for the base agent functionality."""
import pytest
from core.agents.base import BaseAgent
from core.models.message import Message
from core.models.task import Task

pytestmark = pytest.mark.asyncio

async def test_base_agent_initialization(base_agent: BaseAgent):
    """Test that the base agent initializes correctly."""
    assert base_agent.agent_id == "test-agent"
    assert base_agent.name == "Test Agent"
    assert base_agent.description == "A test agent instance"

async def test_agent_message_handling(base_agent: BaseAgent, mock_message_queue):
    """Test that the agent can handle messages correctly."""
    # Attach mock queue to agent
    base_agent.message_queue = mock_message_queue
    
    # Create a test message
    test_message = Message(
        sender_id="test-sender",
        recipient_id="test-agent",
        content="Test message content",
        message_type="test"
    )
    
    # Send message
    await base_agent.send_message(test_message)
    
    # Verify message was queued
    assert not await mock_message_queue.empty()
    
    # Retrieve and verify message
    queued_message = await mock_message_queue.get()
    assert queued_message.sender_id == "test-sender"
    assert queued_message.recipient_id == "test-agent"
    assert queued_message.content == "Test message content"

async def test_agent_task_processing(base_agent: BaseAgent, db_session):
    """Test that the agent can process tasks correctly."""
    # Create a test task
    test_task = Task(
        task_id="test-task-1",
        agent_id="test-agent",
        description="Test task description",
        status="pending"
    )
    
    # Add task to database
    db_session.add(test_task)
    await db_session.commit()
    
    # Process task
    processed_task = await base_agent.process_task(test_task)
    
    # Verify task processing
    assert processed_task.task_id == "test-task-1"
    assert processed_task.agent_id == "test-agent"
    assert processed_task.status == "completed"

async def test_agent_tool_usage(base_agent: BaseAgent, mock_tool_registry):
    """Test that the agent can use tools correctly."""
    # Create a mock tool
    def mock_tool(input_data):
        return f"Processed: {input_data}"
    
    # Register mock tool
    mock_tool_registry.register_tool("test_tool", mock_tool)
    
    # Attach tool registry to agent
    base_agent.tool_registry = mock_tool_registry
    
    # Use tool
    tool = base_agent.tool_registry.get_tool("test_tool")
    result = tool("test input")
    
    # Verify tool usage
    assert result == "Processed: test input"

async def test_agent_state_management(base_agent: BaseAgent):
    """Test that the agent can manage its state correctly."""
    # Set agent state
    test_state = {"key": "value"}
    base_agent.set_state(test_state)
    
    # Verify state
    assert base_agent.get_state() == test_state
    
    # Update state
    base_agent.update_state({"new_key": "new_value"})
    
    # Verify updated state
    updated_state = base_agent.get_state()
    assert updated_state["key"] == "value"
    assert updated_state["new_key"] == "new_value"

async def test_agent_error_handling(base_agent: BaseAgent):
    """Test that the agent handles errors correctly."""
    # Create an invalid task
    invalid_task = Task(
        task_id="invalid-task",
        agent_id="test-agent",
        description="Invalid task description",
        status="invalid_status"  # Invalid status
    )
    
    # Process invalid task and expect error
    with pytest.raises(ValueError):
        await base_agent.process_task(invalid_task)

async def test_cleanup(cleanup_test_data, db_session):
    """Test that the cleanup fixture works correctly."""
    # Add test data
    test_task = Task(
        task_id="cleanup-test",
        agent_id="test-agent",
        description="Test cleanup",
        status="pending"
    )
    db_session.add(test_task)
    await db_session.commit()
    
    # Cleanup happens automatically after test
    # Verify cleanup in next test
    result = await db_session.execute(
        "SELECT COUNT(*) FROM tasks"
    )
    count = result.scalar()
    assert count == 0 
"""
Integration tests for database operations.

These tests verify the interaction between the application and the database.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from core.db.session import async_session, engine
from core.db.models import Task, Agent, Message, Tool
from core.db.crud import (
    task_crud,
    agent_crud,
    message_crud,
    tool_crud
)

@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Task.metadata.create_all)
        await conn.run_sync(Agent.metadata.create_all)
        await conn.run_sync(Message.metadata.create_all)
        await conn.run_sync(Tool.metadata.create_all)
    
    async with async_session() as session:
        try:
            yield session
        finally:
            # Clean up after tests
            async with engine.begin() as conn:
                await conn.run_sync(Task.metadata.drop_all)
                await conn.run_sync(Agent.metadata.drop_all)
                await conn.run_sync(Message.metadata.drop_all)
                await conn.run_sync(Tool.metadata.drop_all)

@pytest.mark.asyncio
async def test_task_crud_operations(db_session: AsyncSession):
    """Test CRUD operations for tasks."""
    # Create task
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "priority": "high",
        "status": "pending"
    }
    created_task = await task_crud.create(db_session, task_data)
    assert created_task.title == task_data["title"]
    
    # Read task
    retrieved_task = await task_crud.get(db_session, created_task.id)
    assert retrieved_task is not None
    assert retrieved_task.id == created_task.id
    
    # Update task
    update_data = {"status": "in_progress"}
    updated_task = await task_crud.update(
        db_session,
        created_task.id,
        update_data
    )
    assert updated_task.status == "in_progress"
    
    # Delete task
    await task_crud.delete(db_session, created_task.id)
    deleted_task = await task_crud.get(db_session, created_task.id)
    assert deleted_task is None

@pytest.mark.asyncio
async def test_agent_crud_operations(db_session: AsyncSession):
    """Test CRUD operations for agents."""
    # Create agent
    agent_data = {
        "name": "TestAgent",
        "type": "super",
        "status": "active",
        "capabilities": ["task_delegation", "code_analysis"]
    }
    created_agent = await agent_crud.create(db_session, agent_data)
    assert created_agent.name == agent_data["name"]
    
    # Read agent
    retrieved_agent = await agent_crud.get(db_session, created_agent.id)
    assert retrieved_agent is not None
    assert retrieved_agent.type == "super"
    
    # Update agent
    update_data = {"status": "inactive"}
    updated_agent = await agent_crud.update(
        db_session,
        created_agent.id,
        update_data
    )
    assert updated_agent.status == "inactive"
    
    # Delete agent
    await agent_crud.delete(db_session, created_agent.id)
    deleted_agent = await agent_crud.get(db_session, created_agent.id)
    assert deleted_agent is None

@pytest.mark.asyncio
async def test_message_crud_operations(db_session: AsyncSession):
    """Test CRUD operations for messages."""
    # Create message
    message_data = {
        "content": {"type": "task", "action": "analyze"},
        "sender_id": "agent1",
        "receiver_id": "agent2",
        "status": "sent"
    }
    created_message = await message_crud.create(db_session, message_data)
    assert created_message.sender_id == message_data["sender_id"]
    
    # Read message
    retrieved_message = await message_crud.get(db_session, created_message.id)
    assert retrieved_message is not None
    assert retrieved_message.status == "sent"
    
    # Update message
    update_data = {"status": "delivered"}
    updated_message = await message_crud.update(
        db_session,
        created_message.id,
        update_data
    )
    assert updated_message.status == "delivered"
    
    # Delete message
    await message_crud.delete(db_session, created_message.id)
    deleted_message = await message_crud.get(db_session, created_message.id)
    assert deleted_message is None

@pytest.mark.asyncio
async def test_tool_crud_operations(db_session: AsyncSession):
    """Test CRUD operations for tools."""
    # Create tool
    tool_data = {
        "name": "TestTool",
        "description": "A test tool",
        "type": "analysis",
        "config": {"timeout": 30, "retries": 3}
    }
    created_tool = await tool_crud.create(db_session, tool_data)
    assert created_tool.name == tool_data["name"]
    
    # Read tool
    retrieved_tool = await tool_crud.get(db_session, created_tool.id)
    assert retrieved_tool is not None
    assert retrieved_tool.type == "analysis"
    
    # Update tool
    update_data = {"config": {"timeout": 60, "retries": 5}}
    updated_tool = await tool_crud.update(
        db_session,
        created_tool.id,
        update_data
    )
    assert updated_tool.config["timeout"] == 60
    
    # Delete tool
    await tool_crud.delete(db_session, created_tool.id)
    deleted_tool = await tool_crud.get(db_session, created_tool.id)
    assert deleted_tool is None

@pytest.mark.asyncio
async def test_relationship_operations(db_session: AsyncSession):
    """Test operations involving relationships between entities."""
    # Create related entities
    agent_data = {
        "name": "TestAgent",
        "type": "super",
        "status": "active"
    }
    agent = await agent_crud.create(db_session, agent_data)
    
    task_data = {
        "title": "Test Task",
        "description": "Test Description",
        "assigned_agent_id": agent.id
    }
    task = await task_crud.create(db_session, task_data)
    
    # Verify relationship
    retrieved_task = await task_crud.get(db_session, task.id)
    assert retrieved_task.assigned_agent_id == agent.id
    
    # Test cascading delete
    await agent_crud.delete(db_session, agent.id)
    orphaned_task = await task_crud.get(db_session, task.id)
    assert orphaned_task.assigned_agent_id is None

@pytest.mark.asyncio
async def test_transaction_rollback(db_session: AsyncSession):
    """Test transaction rollback on error."""
    # Start transaction
    async with db_session.begin():
        # Create task successfully
        task_data = {
            "title": "Test Task",
            "description": "Test Description"
        }
        task = await task_crud.create(db_session, task_data)
        
        # Attempt invalid operation that should trigger rollback
        with pytest.raises(Exception):
            await task_crud.update(
                db_session,
                task.id,
                {"invalid_field": "value"}
            )
    
    # Verify transaction was rolled back
    retrieved_task = await task_crud.get(db_session, task.id)
    assert retrieved_task is None 
"""
Integration tests for agent-related API endpoints.

These tests verify the functionality of agent management endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, Dict

from core.db.session import async_session, engine
from core.db.models import Agent, Task, Message, Tool
from app.main import app
from app.core.security import create_access_token
from app.api.deps import get_db

# Override the database dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Agent.metadata.create_all)
        await conn.run_sync(Task.metadata.create_all)
        await conn.run_sync(Message.metadata.create_all)
        await conn.run_sync(Tool.metadata.create_all)
    
    async with async_session() as session:
        try:
            yield session
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Agent.metadata.drop_all)
                await conn.run_sync(Task.metadata.drop_all)
                await conn.run_sync(Message.metadata.drop_all)
                await conn.run_sync(Tool.metadata.drop_all)

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers."""
    access_token = create_access_token({"sub": "test_user"})
    return {"Authorization": f"Bearer {access_token}"}

def test_create_agent(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent creation endpoint."""
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector",
        "capabilities": ["code_review", "testing"],
        "status": "active"
    }
    response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == agent_data["name"]
    assert "id" in data

def test_get_agent(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent retrieval endpoint."""
    # First create an agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector"
    }
    create_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = create_response.json()["id"]
    
    # Then retrieve it
    response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == agent_id
    assert data["name"] == agent_data["name"]

def test_update_agent(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent update endpoint."""
    # Create agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector"
    }
    create_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = create_response.json()["id"]
    
    # Update agent
    update_data = {
        "status": "inactive",
        "capabilities": ["code_review", "testing", "documentation"]
    }
    response = client.patch(
        f"/api/v1/agents/{agent_id}",
        json=update_data,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"
    assert "documentation" in data["capabilities"]

def test_delete_agent(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent deletion endpoint."""
    # Create agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector"
    }
    create_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = create_response.json()["id"]
    
    # Delete agent
    response = client.delete(
        f"/api/v1/agents/{agent_id}",
        headers=auth_headers
    )
    assert response.status_code == 204
    
    # Verify deletion
    get_response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404

def test_list_agents(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent listing endpoint."""
    # Create multiple agents
    agents = [
        {
            "name": "Agent1",
            "description": "First test agent",
            "agent_type": "inspector"
        },
        {
            "name": "Agent2",
            "description": "Second test agent",
            "agent_type": "journey"
        }
    ]
    for agent_data in agents:
        client.post(
            "/api/v1/agents/",
            json=agent_data,
            headers=auth_headers
        )
    
    # List agents
    response = client.get(
        "/api/v1/agents/",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(agent["name"] == "Agent1" for agent in data)
    assert any(agent["name"] == "Agent2" for agent in data)

def test_filter_agents(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent filtering endpoint."""
    # Create agents with different types
    agents = [
        {
            "name": "Inspector1",
            "description": "First inspector",
            "agent_type": "inspector"
        },
        {
            "name": "Journey1",
            "description": "First journey agent",
            "agent_type": "journey"
        }
    ]
    for agent_data in agents:
        client.post(
            "/api/v1/agents/",
            json=agent_data,
            headers=auth_headers
        )
    
    # Filter agents by type
    response = client.get(
        "/api/v1/agents/?agent_type=inspector",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(agent["agent_type"] == "inspector" for agent in data)

def test_agent_task_assignment(client: TestClient, auth_headers: Dict[str, str]):
    """Test assigning tasks to agents."""
    # Create an agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector"
    }
    agent_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = agent_response.json()["id"]
    
    # Create a task
    task_data = {
        "title": "Test Task",
        "description": "A test task"
    }
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = task_response.json()["id"]
    
    # Assign task to agent
    response = client.post(
        f"/api/v1/agents/{agent_id}/tasks/{task_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify assignment
    response = client.get(
        f"/api/v1/agents/{agent_id}/tasks",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert any(task["id"] == task_id for task in data)

def test_agent_message_history(client: TestClient, auth_headers: Dict[str, str]):
    """Test retrieving agent message history."""
    # Create an agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector"
    }
    agent_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = agent_response.json()["id"]
    
    # Create messages
    messages = [
        {
            "content": "Test message 1",
            "message_type": "task_assignment"
        },
        {
            "content": "Test message 2",
            "message_type": "status_update"
        }
    ]
    for message_data in messages:
        client.post(
            f"/api/v1/agents/{agent_id}/messages",
            json=message_data,
            headers=auth_headers
        )
    
    # Retrieve message history
    response = client.get(
        f"/api/v1/agents/{agent_id}/messages",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(msg["content"] == "Test message 1" for msg in data)
    assert any(msg["content"] == "Test message 2" for msg in data)

def test_agent_capabilities(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent capabilities management."""
    # Create an agent with capabilities
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector",
        "capabilities": ["code_review"]
    }
    agent_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = agent_response.json()["id"]
    
    # Add new capabilities
    new_capabilities = ["testing", "documentation"]
    response = client.post(
        f"/api/v1/agents/{agent_id}/capabilities",
        json={"capabilities": new_capabilities},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert all(cap in data["capabilities"] for cap in new_capabilities)
    
    # Remove capabilities
    remove_capabilities = ["code_review"]
    response = client.delete(
        f"/api/v1/agents/{agent_id}/capabilities",
        json={"capabilities": remove_capabilities},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "code_review" not in data["capabilities"]

def test_agent_status_updates(client: TestClient, auth_headers: Dict[str, str]):
    """Test agent status updates."""
    # Create an agent
    agent_data = {
        "name": "TestAgent",
        "description": "A test agent",
        "agent_type": "inspector",
        "status": "active"
    }
    agent_response = client.post(
        "/api/v1/agents/",
        json=agent_data,
        headers=auth_headers
    )
    agent_id = agent_response.json()["id"]
    
    # Update status
    status_update = {"status": "busy"}
    response = client.patch(
        f"/api/v1/agents/{agent_id}/status",
        json=status_update,
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "busy"
    
    # Verify status history
    response = client.get(
        f"/api/v1/agents/{agent_id}/status/history",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2  # Initial status + update
    assert data[-1]["status"] == "busy" 
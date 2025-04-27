"""
Integration tests for WebSocket functionality.

These tests verify real-time communication between clients and agents.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from typing import AsyncGenerator, Dict

from core.db.session import async_session, engine
from core.db.models import Agent, Task, Message
from app.main import app
from app.core.security import create_access_token
from app.api.deps import get_db

# Override database dependency
async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Agent.metadata.create_all)
        await conn.run_sync(Task.metadata.create_all)
        await conn.run_sync(Message.metadata.create_all)
    
    async with async_session() as session:
        try:
            yield session
        finally:
            async with engine.begin() as conn:
                await conn.run_sync(Agent.metadata.drop_all)
                await conn.run_sync(Task.metadata.drop_all)
                await conn.run_sync(Message.metadata.drop_all)

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture
async def websocket_client():
    """Create a WebSocket test client."""
    async with AsyncClient(app=app, base_url="ws://test") as client:
        yield client

@pytest.fixture
def auth_token() -> str:
    """Create authentication token."""
    return create_access_token({"sub": "test_user"})

@pytest.mark.asyncio
async def test_websocket_connection(websocket_client: AsyncClient, auth_token: str):
    """Test basic WebSocket connection."""
    async with websocket_client.websocket_connect(
        "/ws",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as websocket:
        # Test connection is established
        await websocket.send_json({"type": "ping"})
        response = await websocket.receive_json()
        assert response["type"] == "pong"

@pytest.mark.asyncio
async def test_agent_communication(websocket_client: AsyncClient, auth_token: str):
    """Test real-time communication between agents."""
    async with websocket_client.websocket_connect(
        "/ws/agent/test-agent",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as agent_socket:
        # Send task to agent
        await agent_socket.send_json({
            "type": "task",
            "action": "analyze",
            "data": {"code": "def test(): pass"}
        })
        
        # Verify task received
        response = await agent_socket.receive_json()
        assert response["type"] == "task_received"
        assert "task_id" in response
        
        # Wait for task completion
        response = await agent_socket.receive_json()
        assert response["type"] == "task_completed"
        assert "result" in response

@pytest.mark.asyncio
async def test_multi_agent_workflow(
    websocket_client: AsyncClient,
    auth_token: str
):
    """Test communication in multi-agent workflow."""
    # Connect multiple agent sockets
    async with websocket_client.websocket_connect(
        "/ws/agent/super-agent",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as super_socket, \
    websocket_client.websocket_connect(
        "/ws/agent/worker-agent",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as worker_socket:
        # Super agent delegates task
        await super_socket.send_json({
            "type": "delegate_task",
            "target_agent": "worker-agent",
            "task": {"action": "process", "data": {"key": "value"}}
        })
        
        # Worker receives task
        worker_msg = await worker_socket.receive_json()
        assert worker_msg["type"] == "task_assigned"
        
        # Worker completes task
        await worker_socket.send_json({
            "type": "task_completed",
            "task_id": worker_msg["task_id"],
            "result": {"status": "success"}
        })
        
        # Super agent receives completion
        super_msg = await super_socket.receive_json()
        assert super_msg["type"] == "subtask_completed"

@pytest.mark.asyncio
async def test_error_handling(websocket_client: AsyncClient, auth_token: str):
    """Test WebSocket error handling."""
    async with websocket_client.websocket_connect(
        "/ws/agent/test-agent",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as websocket:
        # Send invalid message
        await websocket.send_json({"type": "invalid"})
        
        # Verify error response
        response = await websocket.receive_json()
        assert response["type"] == "error"
        assert "detail" in response

@pytest.mark.asyncio
async def test_connection_management(
    websocket_client: AsyncClient,
    auth_token: str
):
    """Test WebSocket connection management."""
    # Test connection limit
    connections = []
    for i in range(5):  # Attempt to create 5 connections
        connection = await websocket_client.websocket_connect(
            f"/ws/agent/agent-{i}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        connections.append(connection)
    
    # Verify connections
    for conn in connections:
        await conn.send_json({"type": "ping"})
        response = await conn.receive_json()
        assert response["type"] == "pong"
    
    # Clean up
    for conn in connections:
        await conn.close()

@pytest.mark.asyncio
async def test_message_broadcast(
    websocket_client: AsyncClient,
    auth_token: str
):
    """Test broadcasting messages to multiple clients."""
    async with websocket_client.websocket_connect(
        "/ws/room/test-room",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as client1, \
    websocket_client.websocket_connect(
        "/ws/room/test-room",
        headers={"Authorization": f"Bearer {auth_token}"}
    ) as client2:
        # Send broadcast message
        await client1.send_json({
            "type": "broadcast",
            "message": "Hello everyone!"
        })
        
        # Verify both clients receive message
        response1 = await client1.receive_json()
        response2 = await client2.receive_json()
        
        assert response1["type"] == "broadcast"
        assert response2["type"] == "broadcast"
        assert response1["message"] == "Hello everyone!"
        assert response2["message"] == "Hello everyone!" 
"""
End-to-end workflow tests.

These tests verify complete system functionality across multiple components.
"""
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient
from typing import AsyncGenerator, Dict, List

from core.db.session import async_session, engine
from core.db.models import Agent, Task, Message, Tool
from app.main import app
from app.core.security import create_access_token
from app.api.deps import get_db
from core.agents.super_agent import SuperAgent
from core.agents.journey_agent import JourneyAgent
from core.agents.codifier_agent import CodifierAgent

# Override database dependency
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
async def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Create authentication headers."""
    access_token = create_access_token({"sub": "test_user"})
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture
async def agents() -> Dict[str, Agent]:
    """Initialize test agents."""
    super_agent = SuperAgent()
    journey_agent = JourneyAgent()
    codifier_agent = CodifierAgent()
    
    await super_agent.initialize()
    await journey_agent.initialize()
    await codifier_agent.initialize()
    
    return {
        "super": super_agent,
        "journey": journey_agent,
        "codifier": codifier_agent
    }

@pytest.mark.asyncio
async def test_code_analysis_workflow(
    client: TestClient,
    auth_headers: Dict[str, str],
    agents: Dict[str, Agent]
):
    """Test complete code analysis workflow."""
    # Create analysis task
    task_data = {
        "title": "Analyze code structure",
        "description": "Perform code analysis",
        "code": "def example(): pass",
        "requirements": ["style_check", "security_scan"]
    }
    
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    
    # Verify task assignment
    assignment_response = client.post(
        f"/api/v1/agents/{agents['super'].id}/tasks/{task_id}",
        headers=auth_headers
    )
    assert assignment_response.status_code == 200
    
    # Monitor task progress
    async with AsyncClient(app=app, base_url="ws://test") as ws_client:
        async with ws_client.websocket_connect(
            f"/ws/task/{task_id}",
            headers=auth_headers
        ) as websocket:
            # Wait for analysis completion
            while True:
                message = await websocket.receive_json()
                if message["type"] == "task_completed":
                    result = message["result"]
                    break
    
    # Verify analysis results
    assert "style_check" in result
    assert "security_scan" in result

@pytest.mark.asyncio
async def test_documentation_generation_workflow(
    client: TestClient,
    auth_headers: Dict[str, str],
    agents: Dict[str, Agent]
):
    """Test documentation generation workflow."""
    # Create documentation task
    task_data = {
        "title": "Generate documentation",
        "description": "Create API documentation",
        "files": ["api.py", "models.py"],
        "format": "markdown"
    }
    
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    assert task_response.status_code == 201
    task_id = task_response.json()["id"]
    
    # Assign to CodifierAgent
    client.post(
        f"/api/v1/agents/{agents['codifier'].id}/tasks/{task_id}",
        headers=auth_headers
    )
    
    # Monitor documentation generation
    async with AsyncClient(app=app, base_url="ws://test") as ws_client:
        async with ws_client.websocket_connect(
            f"/ws/task/{task_id}",
            headers=auth_headers
        ) as websocket:
            while True:
                message = await websocket.receive_json()
                if message["type"] == "task_completed":
                    docs = message["result"]["documentation"]
                    break
    
    # Verify documentation
    assert "api.py" in docs
    assert "models.py" in docs

@pytest.mark.asyncio
async def test_multi_agent_task_workflow(
    client: TestClient,
    auth_headers: Dict[str, str],
    agents: Dict[str, Agent]
):
    """Test workflow involving multiple agents."""
    # Create complex task
    task_data = {
        "title": "Process codebase",
        "description": "Analyze and document code",
        "steps": [
            {"type": "analysis", "target": "code_structure"},
            {"type": "documentation", "target": "api_docs"},
            {"type": "validation", "target": "quality_check"}
        ]
    }
    
    # Create task
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = task_response.json()["id"]
    
    # Start workflow
    client.post(
        f"/api/v1/workflows/start",
        json={"task_id": task_id},
        headers=auth_headers
    )
    
    # Monitor workflow progress
    async with AsyncClient(app=app, base_url="ws://test") as ws_client:
        async with ws_client.websocket_connect(
            f"/ws/workflow/{task_id}",
            headers=auth_headers
        ) as websocket:
            steps_completed = []
            while len(steps_completed) < 3:  # Wait for all steps
                message = await websocket.receive_json()
                if message["type"] == "step_completed":
                    steps_completed.append(message["step"])
    
    # Verify all steps completed
    assert "analysis" in [step["type"] for step in steps_completed]
    assert "documentation" in [step["type"] for step in steps_completed]
    assert "validation" in [step["type"] for step in steps_completed]

@pytest.mark.asyncio
async def test_error_recovery_workflow(
    client: TestClient,
    auth_headers: Dict[str, str],
    agents: Dict[str, Agent]
):
    """Test workflow error recovery."""
    # Create task with invalid parameters
    task_data = {
        "title": "Invalid task",
        "description": "This should fail",
        "invalid_param": "error"
    }
    
    # Submit task
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = task_response.json()["id"]
    
    # Monitor error handling
    async with AsyncClient(app=app, base_url="ws://test") as ws_client:
        async with ws_client.websocket_connect(
            f"/ws/task/{task_id}",
            headers=auth_headers
        ) as websocket:
            # Should receive error and recovery attempt
            error_received = False
            recovery_attempted = False
            
            while not (error_received and recovery_attempted):
                message = await websocket.receive_json()
                if message["type"] == "error":
                    error_received = True
                elif message["type"] == "recovery_attempt":
                    recovery_attempted = True
    
    # Verify error was handled
    task_status = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers
    ).json()["status"]
    
    assert task_status in ["failed", "recovered"]

@pytest.mark.asyncio
async def test_state_persistence_workflow(
    client: TestClient,
    auth_headers: Dict[str, str],
    agents: Dict[str, Agent]
):
    """Test workflow state persistence across agent restarts."""
    # Create long-running task
    task_data = {
        "title": "Persistent task",
        "description": "Task surviving restarts",
        "duration": "long"
    }
    
    # Submit task
    task_response = client.post(
        "/api/v1/tasks/",
        json=task_data,
        headers=auth_headers
    )
    task_id = task_response.json()["id"]
    
    # Start task
    client.post(
        f"/api/v1/tasks/{task_id}/start",
        headers=auth_headers
    )
    
    # Simulate agent restart
    await agents["super"].shutdown()
    await agents["super"].initialize()
    
    # Verify task state preserved
    task_status = client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers
    ).json()
    
    assert task_status["state_preserved"] == True
    assert "progress" in task_status 
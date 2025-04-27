"""
Integration tests for the WrenchAI system.

These tests verify the integration between different components:
1. Agent-to-agent communication
2. Database integration
3. API endpoints
4. Tool integration
5. End-to-end workflows
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List
import json
import os
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from wrenchai.core.agents.super_agent import SuperAgent
from wrenchai.core.agents.journey_agent import JourneyAgent
from wrenchai.core.agents.codifier_agent import Codifier
from wrenchai.core.agents.test_engineer_agent import TestEngineer
from wrenchai.core.agent_system import AgentManager
from wrenchai.core.tools.tool_registry import ToolRegistry
from wrenchai.core.db.models import Base
from wrenchai.fastapi.app.main import app
from wrenchai.core.tools.secrets_manager import secrets

# Test database URL
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

@pytest.fixture
async def test_db():
    """Create a test database and tables."""
    engine = create_async_engine(TEST_DB_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    # Cleanup
    await engine.dispose()
    if os.path.exists("./test.db"):
        os.remove("./test.db")

@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_secrets():
    """Mock the secrets manager."""
    with patch('wrenchai.core.tools.secrets_manager.secrets') as mock:
        mock.get_secret.return_value = "test-secret"
        yield mock

@pytest.fixture
def agent_manager():
    """Create an agent manager with test configuration."""
    manager = AgentManager(config_dir="tests/test_configs")
    tool_registry = ToolRegistry()
    manager.set_tool_registry(tool_registry)
    return manager

class TestAgentCommunication:
    """Test agent-to-agent communication."""
    
    @pytest.mark.asyncio
    async def test_agent_message_passing(self, agent_manager):
        """Test that agents can pass messages between each other."""
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create a test message
        message = {
            "type": "task_assignment",
            "content": "Create a new repository",
            "metadata": {"priority": "high"}
        }
        
        # Send message from super agent to journey agent
        response = await super_agent.send_message(journey_agent.id, message)
        
        # Verify message was received and processed
        assert response["status"] == "success"
        assert "message_id" in response
        
        # Check journey agent received the message
        received = await journey_agent.get_messages()
        assert len(received) > 0
        assert received[0]["content"] == message["content"]
    
    @pytest.mark.asyncio
    async def test_multi_agent_collaboration(self, agent_manager):
        """Test multiple agents collaborating on a task."""
        # Initialize agents
        super_agent = agent_manager.initialize_agent("SuperAgent")
        journey_agent = agent_manager.initialize_agent("JourneyAgent")
        codifier = agent_manager.initialize_agent("Codifier")
        
        # Create a collaborative task
        task = {
            "type": "documentation",
            "content": "Document the API endpoints",
            "workflow": ["analyze", "document", "review"]
        }
        
        # Start the collaboration
        workflow_result = await super_agent.coordinate_task(
            task,
            [journey_agent.id, codifier.id]
        )
        
        # Verify workflow completion
        assert workflow_result["status"] == "completed"
        assert "documentation" in workflow_result["outputs"]
        assert workflow_result["participants"] == [journey_agent.id, codifier.id]

class TestDatabaseIntegration:
    """Test database integration with the system."""
    
    @pytest.mark.asyncio
    async def test_agent_state_persistence(self, test_db, agent_manager):
        """Test that agent state can be persisted to the database."""
        # Initialize an agent
        agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Create some agent state
        state = {
            "task_id": "test-task",
            "status": "in_progress",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save state to database
        await agent.save_state(test_db, state)
        
        # Retrieve state from database
        loaded_state = await agent.load_state(test_db)
        
        # Verify state was persisted correctly
        assert loaded_state["task_id"] == state["task_id"]
        assert loaded_state["status"] == state["status"]
    
    @pytest.mark.asyncio
    async def test_workflow_history_tracking(self, test_db, agent_manager):
        """Test tracking of workflow history in the database."""
        # Initialize workflow
        workflow_id = "test-workflow"
        agents = [
            agent_manager.initialize_agent("SuperAgent"),
            agent_manager.initialize_agent("JourneyAgent")
        ]
        
        # Create some workflow steps
        steps = [
            {"step_id": 1, "action": "initialize", "status": "completed"},
            {"step_id": 2, "action": "process", "status": "in_progress"}
        ]
        
        # Record workflow history
        for step in steps:
            await agent_manager.record_workflow_step(
                test_db,
                workflow_id,
                step,
                [agent.id for agent in agents]
            )
        
        # Retrieve workflow history
        history = await agent_manager.get_workflow_history(test_db, workflow_id)
        
        # Verify history was recorded correctly
        assert len(history) == len(steps)
        assert history[0]["step_id"] == steps[0]["step_id"]
        assert history[1]["status"] == steps[1]["status"]

class TestAPIEndpoints:
    """Test API endpoint integration."""
    
    def test_agent_api_endpoints(self, test_client):
        """Test agent-related API endpoints."""
        # Test creating a new agent
        response = test_client.post(
            "/api/v1/agents/",
            json={
                "role": "JourneyAgent",
                "name": "test-journey-agent",
                "tools": ["web_search", "code_generation"]
            }
        )
        assert response.status_code == 200
        agent_id = response.json()["agent_id"]
        
        # Test getting agent status
        response = test_client.get(f"/api/v1/agents/{agent_id}/status")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"
        
        # Test assigning a task to the agent
        response = test_client.post(
            f"/api/v1/agents/{agent_id}/tasks",
            json={
                "type": "analysis",
                "content": "Analyze the codebase"
            }
        )
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Test getting task status
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        assert "status" in response.json()
    
    def test_workflow_api_endpoints(self, test_client):
        """Test workflow-related API endpoints."""
        # Test creating a new workflow
        response = test_client.post(
            "/api/v1/workflows/",
            json={
                "name": "test-workflow",
                "description": "Test workflow",
                "steps": [
                    {
                        "step_id": 1,
                        "action": "initialize",
                        "agent_role": "SuperAgent"
                    }
                ]
            }
        )
        assert response.status_code == 200
        workflow_id = response.json()["workflow_id"]
        
        # Test getting workflow status
        response = test_client.get(f"/api/v1/workflows/{workflow_id}")
        assert response.status_code == 200
        assert "status" in response.json()
        
        # Test updating workflow
        response = test_client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={"status": "completed"}
        )
        assert response.status_code == 200
        
        # Test listing workflows
        response = test_client.get("/api/v1/workflows/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

class TestToolIntegration:
    """Test integration with various tools."""
    
    @pytest.mark.asyncio
    async def test_tool_registry_integration(self, agent_manager):
        """Test that agents can access and use tools from the registry."""
        # Initialize an agent with tools
        agent = agent_manager.initialize_agent(
            "JourneyAgent",
            mcp_servers=["github", "run-python"]
        )
        
        # Test tool availability
        tools = agent.get_available_tools()
        assert "github" in tools
        assert "run-python" in tools
        
        # Test tool execution
        result = await agent.execute_tool(
            "github",
            "list_repositories",
            {"owner": "test-org"}
        )
        assert result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self, agent_manager):
        """Test handling of tool execution errors."""
        agent = agent_manager.initialize_agent("JourneyAgent")
        
        # Test handling of missing tool
        with pytest.raises(ValueError):
            await agent.execute_tool(
                "nonexistent_tool",
                "some_action",
                {}
            )
        
        # Test handling of invalid parameters
        with pytest.raises(ValueError):
            await agent.execute_tool(
                "github",
                "list_repositories",
                {"invalid_param": "value"}
            )

class TestEndToEndWorkflows:
    """Test end-to-end workflows."""
    
    @pytest.mark.asyncio
    async def test_documentation_workflow(self, agent_manager, test_db):
        """Test the complete documentation workflow."""
        # Initialize the workflow
        workflow_id = "doc-workflow-test"
        workflow_config = {
            "name": "Documentation Generation",
            "steps": [
                {
                    "step_id": "analyze",
                    "agent": "JourneyAgent",
                    "action": "analyze_codebase"
                },
                {
                    "step_id": "document",
                    "agent": "Codifier",
                    "action": "generate_documentation"
                },
                {
                    "step_id": "test",
                    "agent": "TestEngineer",
                    "action": "validate_documentation"
                }
            ]
        }
        
        # Run the workflow
        result = await agent_manager.run_workflow(
            workflow_id,
            workflow_config,
            {"codebase_path": "./tests/test_data"}
        )
        
        # Verify workflow completion
        assert result["status"] == "completed"
        assert "documentation" in result["outputs"]
        assert result["outputs"]["documentation"]["validation"]["passed"]
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, agent_manager, test_db):
        """Test workflow error recovery capabilities."""
        # Initialize workflow with intentional error
        workflow_id = "error-recovery-test"
        workflow_config = {
            "name": "Error Recovery Test",
            "steps": [
                {
                    "step_id": "error_step",
                    "agent": "JourneyAgent",
                    "action": "trigger_error",
                    "recovery": {
                        "max_retries": 3,
                        "fallback_action": "alternative_path"
                    }
                }
            ]
        }
        
        # Run the workflow
        result = await agent_manager.run_workflow(
            workflow_id,
            workflow_config,
            {"trigger_recovery": True}
        )
        
        # Verify error recovery
        assert result["status"] == "completed"
        assert result["recovery_attempts"] > 0
        assert result["final_path"] == "alternative_path" 
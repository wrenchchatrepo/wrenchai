"""Tests for the playbook execution API endpoints.

Tests the FastAPI endpoints for playbook execution and logs retrieval.
"""

import pytest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.playbooks import router, task_statuses
from app.schemas.responses import ResponseModel
from core.playbook_logger import playbook_logger

@pytest.fixture
def app():
    """Create a test FastAPI app with the playbook router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/playbooks")
    return app

@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)

@pytest.fixture
def mock_super_agent():
    """Create a mock SuperAgent for testing."""
    with patch('app.core.agents.SuperAgent') as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent_class.create.return_value = mock_agent
        mock_agent.execute_playbook.return_value = {"success": True}
        yield mock_agent

@pytest.fixture
def mock_playbook_logger():
    """Mock the playbook logger."""
    with patch('app.api.v1.endpoints.playbooks.playbook_logger') as mock_logger:
        mock_logger.start_playbook_execution.return_value = "test_execution_id"
        mock_logger.get_playbook_execution.return_value = {
            "execution_id": "test_execution_id",
            "name": "Test Playbook",
            "status": "completed",
            "steps": []
        }
        mock_logger.get_playbook_execution_metrics.return_value = {
            "total_duration_seconds": 5.0
        }
        mock_logger.query_playbook_executions.return_value = []
        yield mock_logger

@pytest.fixture
def sample_playbook_config():
    """Sample playbook configuration for testing."""
    return {
        "name": "test_playbook",
        "project": {
            "name": "Test Project",
            "description": "Test project description",
            "branch": "main"
        },
        "parameters": {"param1": "value1"},
        "agents": ["super"]
    }

@pytest.mark.asyncio
async def test_execute_playbook(client, mock_super_agent, sample_playbook_config, monkeypatch):
    """Test the execute playbook endpoint."""
    # Mock the get_agents function
    async def mock_get_agents(agent_names, settings):
        return {"super": mock_super_agent}
    
    monkeypatch.setattr(
        "app.api.v1.endpoints.playbooks.get_agents",
        mock_get_agents
    )
    
    # Test executing a playbook
    response = client.post(
        "/api/playbooks/execute",
        json=sample_playbook_config
    )
    
    # Check response
    assert response.status_code == 202
    data = response.json()
    assert data["success"] == True
    assert "task_id" in data["data"]

@pytest.mark.asyncio
async def test_get_execution_status(client):
    """Test getting the status of a playbook execution."""
    # Add a test task status
    task_id = "test_task_123"
    task_statuses[task_id] = {
        "status": "completed",
        "message": "Execution completed",
        "result": {"success": True}
    }
    
    # Get status
    response = client.get(f"/api/playbooks/status/{task_id}")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert data["data"]["status"] == "completed"
    
    # Clean up
    del task_statuses[task_id]

@pytest.mark.asyncio
async def test_get_execution_logs(client, mock_playbook_logger):
    """Test getting execution logs for a playbook."""
    # Get logs
    response = client.get("/api/playbooks/logs/test_execution_id")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert "execution" in data["data"]
    assert "metrics" in data["data"]
    
    # Verify logger was called
    mock_playbook_logger.get_playbook_execution.assert_called_once()

@pytest.mark.asyncio
async def test_get_execution_logs_not_found(client, mock_playbook_logger):
    """Test getting logs for a non-existent execution."""
    # Set up mock to return None
    mock_playbook_logger.get_playbook_execution.return_value = None
    
    # Get logs
    response = client.get("/api/playbooks/logs/nonexistent_id")
    
    # Check response
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_recent_executions(client, mock_playbook_logger):
    """Test getting recent playbook executions."""
    # Set up mock to return some executions
    mock_playbook_logger.query_playbook_executions.return_value = [
        {
            "execution_id": "exec1",
            "name": "Playbook 1",
            "status": "completed",
            "steps": [],
            "errors": []
        },
        {
            "execution_id": "exec2",
            "name": "Playbook 2",
            "status": "failed",
            "steps": [],
            "errors": [{"error": "test error"}]
        }
    ]
    
    # Get recent executions
    response = client.get("/api/playbooks/recent_executions?limit=5")
    
    # Check response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] == True
    assert len(data["data"]) == 2
    
    # Verify logger was called with correct parameters
    mock_playbook_logger.query_playbook_executions.assert_called_once_with(
        status=None,
        limit=5
    )

@pytest.mark.asyncio
async def test_get_recent_executions_with_status(client, mock_playbook_logger):
    """Test getting recent playbook executions filtered by status."""
    # Get recent executions with status filter
    response = client.get("/api/playbooks/recent_executions?status=completed")
    
    # Check response
    assert response.status_code == 200
    
    # Verify logger was called with correct parameters
    mock_playbook_logger.query_playbook_executions.assert_called_once_with(
        status="completed",
        limit=10  # default
    )
"""Unit tests for playbook execution and logging.

Tests the core functionality of playbook execution, verification, 
and logging with various test playbooks.
"""

import pytest
import os
import json
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timedelta

from core.playbook_logger import (
    PlaybookExecutionLogger,
    track_playbook_execution
)

# Sample test playbook data
TEST_PLAYBOOK = {
    "name": "Test Playbook",
    "description": "A test playbook for unit testing",
    "agents": [
        {"type": "super", "config": {"model": "gpt-4"}},
        {"type": "worker", "config": {"model": "gpt-3.5-turbo"}} 
    ],
    "steps": [
        {
            "name": "Initialize Project",
            "action": "initialize",
            "params": {"template": "basic"}
        },
        {
            "name": "Process Data",
            "action": "process",
            "params": {"input": "data.csv", "output": "results.json"}
        }
    ]
}

# Sample test execution result
TEST_EXECUTION_RESULT = {
    "success": True,
    "output": {
        "initialized": True,
        "processed": True,
        "results_path": "/tmp/results.json"
    }
}

@pytest.fixture
def mock_execution_logger():
    """Mock execution logger for testing."""
    with patch('core.playbook_logger.init_execution_logger') as mock_init:
        mock_logger = MagicMock()
        mock_init.return_value = mock_logger
        
        # Set up return values
        mock_logger.create_execution.return_value = "test_execution_id"
        
        yield mock_logger

@pytest.fixture
def mock_playbook_logger():
    """Mock playbook logger for testing."""
    with patch('core.playbook_logger.playbook_logger') as mock_logger:
        mock_logger.start_playbook_execution.return_value = "test_execution_id"
        mock_logger.get_playbook_execution.return_value = {
            "execution_id": "test_execution_id",
            "name": "Test Playbook",
            "status": "completed",
            "events": [],
            "steps": [
                {
                    "step_id": "step1",
                    "name": "Initialize Project",
                    "status": "completed"
                },
                {
                    "step_id": "step2",
                    "name": "Process Data",
                    "status": "completed"
                }
            ]
        }
        yield mock_logger

@pytest.fixture
def sample_playbook():
    """Sample playbook for testing."""
    return TEST_PLAYBOOK

@pytest.mark.asyncio
async def test_playbook_logger_initialization():
    """Test that the playbook logger initializes correctly."""
    with patch('core.playbook_logger.init_execution_logger') as mock_init:
        # Create a logger instance
        logger = PlaybookExecutionLogger()
        
        # Check that init_execution_logger was called
        mock_init.assert_called_once()

def test_start_playbook_execution(mock_playbook_logger):
    """Test starting playbook execution logging."""
    # Start a playbook execution
    execution_id = mock_playbook_logger.start_playbook_execution(
        playbook_id="test_pb_123",
        playbook_name="Test Playbook",
        playbook_description="Test description",
        metadata={"key": "value"}
    )
    
    # Verify execution was started
    assert execution_id == "test_execution_id"
    mock_playbook_logger.start_playbook_execution.assert_called_once()
    
    # Check that metadata was passed correctly
    call_args = mock_playbook_logger.start_playbook_execution.call_args[1]
    assert call_args["playbook_id"] == "test_pb_123"
    assert call_args["playbook_name"] == "Test Playbook"
    assert call_args["metadata"]["key"] == "value"

def test_log_step_execution(mock_playbook_logger):
    """Test logging step execution."""
    # Start a step
    mock_playbook_logger.log_step_execution(
        execution_id="test_execution_id",
        step_id="step1",
        step_name="Initialize Project",
        step_type="initialize",
        status="started"
    )
    
    # Complete a step
    mock_playbook_logger.log_step_execution(
        execution_id="test_execution_id",
        step_id="step1",
        step_name="Initialize Project",
        step_type="initialize",
        status="completed",
        step_data={"result": {"initialized": True}, "duration_seconds": 1.5}
    )
    
    # Verify step logging was called
    assert mock_playbook_logger.log_step_execution.call_count == 2

def test_log_agent_execution(mock_playbook_logger):
    """Test logging agent execution."""
    # Log agent action
    mock_playbook_logger.log_agent_execution(
        execution_id="test_execution_id",
        agent_id="agent1",
        agent_type="super",
        action="process_data",
        input_data={"data": "example"},
        output_data={"result": "processed"},
        duration_seconds=0.5
    )
    
    # Verify agent logging was called
    mock_playbook_logger.log_agent_execution.assert_called_once()
    
    # Check call arguments
    call_args = mock_playbook_logger.log_agent_execution.call_args[1]
    assert call_args["agent_id"] == "agent1"
    assert call_args["agent_type"] == "super"
    assert call_args["action"] == "process_data"

def test_complete_playbook_execution(mock_playbook_logger):
    """Test completing playbook execution."""
    # Complete the execution
    mock_playbook_logger.complete_playbook_execution(
        execution_id="test_execution_id",
        success=True,
        result={"output": "example output"}
    )
    
    # Verify completion was called
    mock_playbook_logger.complete_playbook_execution.assert_called_once()
    
    # Check call arguments
    call_args = mock_playbook_logger.complete_playbook_execution.call_args[1]
    assert call_args["execution_id"] == "test_execution_id"
    assert call_args["success"] == True

def test_error_playbook_execution(mock_playbook_logger):
    """Test logging and completing a failed playbook execution."""
    # Complete with error
    mock_playbook_logger.complete_playbook_execution(
        execution_id="test_execution_id",
        success=False,
        error="Test error message"
    )
    
    # Verify completion was called
    mock_playbook_logger.complete_playbook_execution.assert_called_once()
    
    # Check call arguments
    call_args = mock_playbook_logger.complete_playbook_execution.call_args[1]
    assert call_args["execution_id"] == "test_execution_id"
    assert call_args["success"] == False
    assert call_args["error"] == "Test error message"

def test_context_manager(mock_playbook_logger):
    """Test the context manager for playbook execution tracking."""
    # Use context manager
    with patch('core.playbook_logger.track_playbook_execution') as mock_track:
        mock_track.return_value.__enter__.return_value = "test_execution_id"
        
        with track_playbook_execution(
            playbook_id="test_pb_123",
            playbook_name="Test Playbook",
            metadata={"test": "metadata"}
        ) as execution_id:
            assert execution_id == "test_execution_id"

@pytest.mark.asyncio
async def test_get_execution_logs(mock_playbook_logger):
    """Test retrieving execution logs."""
    # Get execution logs
    logs = mock_playbook_logger.get_playbook_execution("test_execution_id")
    
    # Verify get_playbook_execution was called
    mock_playbook_logger.get_playbook_execution.assert_called_once_with("test_execution_id")
    
    # Check log structure
    assert logs["execution_id"] == "test_execution_id"
    assert logs["name"] == "Test Playbook"
    assert len(logs["steps"]) == 2

@pytest.mark.asyncio
async def test_query_playbook_executions(mock_playbook_logger):
    """Test querying for playbook executions."""
    # Set up mock query response
    mock_playbook_logger.query_playbook_executions.return_value = [
        {
            "execution_id": "exec1",
            "name": "Playbook 1",
            "status": "completed",
            "start_time": datetime.utcnow() - timedelta(hours=1),
            "end_time": datetime.utcnow(),
            "steps": [{}],
            "errors": []
        },
        {
            "execution_id": "exec2",
            "name": "Playbook 2",
            "status": "failed",
            "start_time": datetime.utcnow() - timedelta(hours=2),
            "end_time": datetime.utcnow() - timedelta(hours=1),
            "steps": [{}],
            "errors": [{"error": "test error"}]
        }
    ]
    
    # Query executions
    executions = mock_playbook_logger.query_playbook_executions(
        status="completed",
        limit=10
    )
    
    # Verify query was called
    mock_playbook_logger.query_playbook_executions.assert_called_once()
    
    # Check results
    assert len(executions) == 2
    assert executions[0]["execution_id"] == "exec1"
    assert executions[1]["execution_id"] == "exec2"

@pytest.mark.asyncio
async def test_playbook_execution_metrics(mock_playbook_logger):
    """Test getting metrics for playbook execution."""
    # Set up mock metrics response
    mock_playbook_logger.get_playbook_execution_metrics.return_value = {
        "total_duration_seconds": 10.5,
        "step_count": 2,
        "success_rate": 100.0,
        "llm_tokens_used": 1500,
        "tool_calls": 5,
        "agent_actions": 3
    }
    
    # Get metrics
    metrics = mock_playbook_logger.get_playbook_execution_metrics("test_execution_id")
    
    # Verify get_metrics was called
    mock_playbook_logger.get_playbook_execution_metrics.assert_called_once_with("test_execution_id")
    
    # Check metrics
    assert metrics["total_duration_seconds"] == 10.5
    assert metrics["step_count"] == 2
    assert metrics["success_rate"] == 100.0
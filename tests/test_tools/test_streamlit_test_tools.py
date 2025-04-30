"""Tests for the Streamlit Testing Tools."""

import pytest
from datetime import datetime
from typing import Dict, Any

from core.tools.streamlit_test_tools import (
    TestMode,
    TestConfig,
    TestResult,
    StreamlitTestRunner,
    StreamlitTestCase
)
from core.tools.streamlit_tools import (
    ComponentType,
    ComponentConfig,
    streamlit_state
)

@pytest.fixture
def test_config():
    """Create a test configuration."""
    return TestConfig(
        mode=TestMode.UNIT,
        script_path="test_app.py",
        timeout=1.0,
        capture_logs=True
    )

@pytest.fixture
def test_runner(test_config):
    """Create a test runner instance."""
    return StreamlitTestRunner(test_config)

@pytest.fixture
def test_case():
    """Create a test case instance."""
    return StreamlitTestCase()

@pytest.fixture
def sample_component():
    """Create a sample component for testing."""
    config = ComponentConfig(
        type=ComponentType.BUTTON,
        key="test_button",
        value=False
    )
    streamlit_state.register_component(config)
    return config

@pytest.mark.asyncio
async def test_simulate_component_interaction(test_runner, sample_component):
    """Test simulating component interaction."""
    result = await test_runner.simulate_component_interaction("test_button", True)
    
    assert result.success
    assert result.data["previous_value"] is False
    assert result.data["new_value"] is True
    assert result.data["version"] == 2

@pytest.mark.asyncio
async def test_simulate_nonexistent_component(test_runner):
    """Test simulating interaction with nonexistent component."""
    result = await test_runner.simulate_component_interaction("nonexistent", True)
    
    assert not result.success
    assert "not found" in result.error

@pytest.mark.asyncio
async def test_verify_component_state(test_runner, sample_component):
    """Test verifying component state."""
    # First update component
    await test_runner.simulate_component_interaction("test_button", True)
    
    # Then verify state
    result = await test_runner.verify_component_state("test_button", True)
    
    assert result.success
    assert result.data["actual_value"] is True
    assert result.data["expected_value"] is True

@pytest.mark.asyncio
async def test_verify_component_state_type_mismatch(test_runner, sample_component):
    """Test verifying component state with type mismatch."""
    await test_runner.simulate_component_interaction("test_button", 1)
    
    result = await test_runner.verify_component_state("test_button", True, check_type=True)
    
    assert not result.success
    assert not result.data["type_match"]
    assert not result.data["value_match"]

@pytest.mark.asyncio
async def test_verify_session_state(test_runner):
    """Test verifying session state."""
    # Set session state
    streamlit_state.set_session_state("test_key", {"value": 42})
    
    # Verify state
    result = await test_runner.verify_session_state("test_key", {"value": 42})
    
    assert result.success
    assert result.data["actual_value"] == {"value": 42}
    assert result.data["expected_value"] == {"value": 42}

@pytest.mark.asyncio
async def test_verify_nonexistent_session_state(test_runner):
    """Test verifying nonexistent session state."""
    result = await test_runner.verify_session_state("nonexistent", 42)
    
    assert not result.success
    assert "not found" in result.error

def test_simulate_page_context(test_runner):
    """Test page context simulation."""
    original_page = test_runner.config.page_path
    
    with test_runner.simulate_page_context("new_page.py"):
        assert test_runner.config.page_path == "new_page.py"
    
    assert test_runner.config.page_path == original_page

@pytest.mark.asyncio
async def test_run_test_sequence(test_runner, sample_component):
    """Test running a sequence of test steps."""
    async def step1():
        return await test_runner.simulate_component_interaction("test_button", True)
        
    async def step2():
        return await test_runner.verify_component_state("test_button", True)
    
    results = await test_runner.run_test_sequence([step1, step2])
    
    assert len(results) == 2
    assert all(result.success for result in results)

@pytest.mark.asyncio
async def test_run_test_sequence_with_failure(test_runner):
    """Test running a sequence that includes a failing step."""
    async def failing_step():
        return TestResult(
            success=False,
            message="Step failed",
            error="Test error"
        )
        
    async def next_step():
        return TestResult(
            success=True,
            message="Step succeeded"
        )
    
    results = await test_runner.run_test_sequence([failing_step, next_step])
    
    assert len(results) == 1  # Should stop after failure in unit mode
    assert not results[0].success

@pytest.mark.asyncio
async def test_test_case_assertions(test_case, sample_component):
    """Test StreamlitTestCase assertion methods."""
    # Test component value assertion
    await test_case.simulateInteraction("test_button", True)
    await test_case.assertComponentValue("test_button", True)
    
    # Test session state assertion
    streamlit_state.set_session_state("test_key", 42)
    await test_case.assertSessionState("test_key", 42)

@pytest.mark.asyncio
async def test_test_case_lifecycle(test_case):
    """Test StreamlitTestCase lifecycle methods."""
    # Set up some state
    streamlit_state.set_session_state("test_key", 42)
    
    # Run tearDown
    await test_case.tearDown()
    
    # Verify state was cleared
    assert streamlit_state.get_session_state("test_key") is None

def test_test_config_defaults():
    """Test TestConfig default values."""
    config = TestConfig()
    
    assert config.mode == TestMode.UNIT
    assert config.timeout == 5.0
    assert config.capture_logs is True
    assert config.use_session_state is True

def test_test_result_creation():
    """Test TestResult creation and properties."""
    result = TestResult(
        success=True,
        message="Test passed",
        data={"value": 42}
    )
    
    assert result.success
    assert result.message == "Test passed"
    assert result.data["value"] == 42
    assert result.error is None
    assert isinstance(result.timestamp, datetime) 
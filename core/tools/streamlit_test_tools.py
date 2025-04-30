"""
Streamlit Testing Tools for automated testing of Streamlit applications.

This module provides tools for:
- Simulating Streamlit app execution
- Testing component interactions
- Verifying component states
- Testing session state management
- Testing multipage app functionality
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from contextlib import contextmanager

from .streamlit_tools import (
    ComponentType,
    ComponentConfig,
    ComponentState,
    LayoutConfig,
    streamlit_state
)

logger = logging.getLogger(__name__)

class TestMode(str, Enum):
    """Test execution modes."""
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"

class TestConfig(BaseModel):
    """Configuration for Streamlit app testing."""
    mode: TestMode = Field(TestMode.UNIT, description="Test execution mode")
    script_path: Optional[str] = Field(None, description="Path to Streamlit script")
    page_path: Optional[str] = Field(None, description="Path to page script for multipage apps")
    timeout: float = Field(5.0, description="Timeout for component interactions")
    capture_logs: bool = Field(True, description="Whether to capture Streamlit logs")
    use_session_state: bool = Field(True, description="Whether to use session state")

class TestResult(BaseModel):
    """Result of a Streamlit test operation."""
    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Result message")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional result data")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StreamlitTestRunner:
    """Test runner for Streamlit applications."""
    
    def __init__(self, config: TestConfig):
        """
        Initializes the StreamlitTestRunner with the given test configuration.
        
        Sets up the test environment and prepares to collect test results.
        """
        self.config = config
        self.results: List[TestResult] = []
        self._setup_test_environment()

    def _setup_test_environment(self):
        """
        Initializes the test environment by clearing Streamlit state and configuring logging if enabled in the configuration.
        """
        streamlit_state.clear_all()
        if self.config.capture_logs:
            # Configure logging capture
            self._setup_logging()

    def _setup_logging(self):
        """
        Configures a stream handler to capture log output at the INFO level during test execution.
        """
        self.log_handler = logging.StreamHandler()
        self.log_handler.setLevel(logging.INFO)
        logger.addHandler(self.log_handler)

    async def simulate_component_interaction(
        self,
        component_key: str,
        value: Any,
        wait_for_update: bool = True
    ) -> TestResult:
        """
        Simulates a user interaction by updating the value of a specified component.
        
        Attempts to set the given value for the component identified by `component_key`. If the component is found, its value is updated and the previous and new values are returned in the result. If `wait_for_update` is True, the method optionally waits for the component to reflect the change. Returns a TestResult indicating success or failure, including error details if the component is not found or an exception occurs.
        """
        try:
            # Get current component state
            current_state = streamlit_state.get_component(component_key)
            if not current_state:
                return TestResult(
                    success=False,
                    message=f"Component {component_key} not found",
                    error="Component not found"
                )

            # Update component value
            updated_state = streamlit_state.update_component(component_key, value)
            
            if wait_for_update:
                # Wait for component to update (implement actual wait logic here)
                pass

            return TestResult(
                success=True,
                message=f"Component {component_key} updated successfully",
                data={
                    "previous_value": current_state.value,
                    "new_value": updated_state.value,
                    "version": updated_state.version
                }
            )

        except Exception as e:
            logger.error(f"Error simulating component interaction: {str(e)}")
            return TestResult(
                success=False,
                message=f"Failed to simulate interaction with {component_key}",
                error=str(e)
            )

    async def verify_component_state(
        self,
        component_key: str,
        expected_value: Any,
        check_type: bool = True
    ) -> TestResult:
        """
        Verifies that a component's state matches the expected value and type.
        
        Checks if the specified component exists and whether its value and, optionally, its type match the expected value. Returns a TestResult indicating success or failure with relevant details.
        """
        try:
            state = streamlit_state.get_component(component_key)
            if not state:
                return TestResult(
                    success=False,
                    message=f"Component {component_key} not found",
                    error="Component not found"
                )

            value_matches = state.value == expected_value
            type_matches = True if not check_type else isinstance(state.value, type(expected_value))

            if value_matches and type_matches:
                return TestResult(
                    success=True,
                    message=f"Component {component_key} state verified successfully",
                    data={
                        "actual_value": state.value,
                        "expected_value": expected_value,
                        "version": state.version
                    }
                )
            else:
                return TestResult(
                    success=False,
                    message=f"Component {component_key} state verification failed",
                    data={
                        "actual_value": state.value,
                        "expected_value": expected_value,
                        "type_match": type_matches,
                        "value_match": value_matches
                    },
                    error="State verification failed"
                )

        except Exception as e:
            logger.error(f"Error verifying component state: {str(e)}")
            return TestResult(
                success=False,
                message=f"Failed to verify {component_key} state",
                error=str(e)
            )

    async def verify_session_state(
        self,
        key: str,
        expected_value: Any
    ) -> TestResult:
        """
        Verifies that a session state value matches the expected value.
        
        Args:
            key: The session state key to check.
            expected_value: The value expected for the given key.
        
        Returns:
            A TestResult indicating whether the actual session state value matches the expected value.
        """
        try:
            actual_value = streamlit_state.get_session_state(key)
            if actual_value == expected_value:
                return TestResult(
                    success=True,
                    message=f"Session state {key} verified successfully",
                    data={
                        "actual_value": actual_value,
                        "expected_value": expected_value
                    }
                )
            else:
                return TestResult(
                    success=False,
                    message=f"Session state {key} verification failed",
                    data={
                        "actual_value": actual_value,
                        "expected_value": expected_value
                    },
                    error="Session state verification failed"
                )

        except Exception as e:
            logger.error(f"Error verifying session state: {str(e)}")
            return TestResult(
                success=False,
                message=f"Failed to verify session state {key}",
                error=str(e)
            )

    @contextmanager
    def simulate_page_context(self, page_path: Optional[str] = None):
        """
        Temporarily sets the page context for simulating navigation in multipage Streamlit apps.
        
        When used as a context manager, this sets the current page path in the test configuration
        to the specified value for the duration of the context, then restores the previous page path
        on exit.
        
        Args:
            page_path: The path to the page script to simulate as the active page.
        """
        try:
            # Store current state
            previous_page = self.config.page_path
            
            # Set new page context
            self.config.page_path = page_path or self.config.page_path
            yield
            
        finally:
            # Restore previous state
            self.config.page_path = previous_page

    async def run_test_sequence(
        self,
        steps: List[Callable[[], Any]]
    ) -> List[TestResult]:
        """
        Executes a sequence of asynchronous test steps and collects their results.
        
        Each step is awaited in order. If a step fails and the test mode is UNIT, execution stops early. Exceptions during steps are caught and recorded as failed TestResults.
        
        Args:
            steps: A list of asynchronous test step callables to execute.
        
        Returns:
            A list of TestResult objects representing the outcome of each step.
        """
        results = []
        for step in steps:
            try:
                result = await step()
                results.append(result)
                
                # Stop sequence on failure if in unit test mode
                if not result.success and self.config.mode == TestMode.UNIT:
                    break
                    
            except Exception as e:
                logger.error(f"Error in test sequence: {str(e)}")
                results.append(TestResult(
                    success=False,
                    message="Test step failed with exception",
                    error=str(e)
                ))
                if self.config.mode == TestMode.UNIT:
                    break
                    
        return results

    def cleanup(self):
        """
        Cleans up the test environment by clearing Streamlit state and removing the log handler if log capture is enabled.
        """
        streamlit_state.clear_all()
        if self.config.capture_logs:
            logger.removeHandler(self.log_handler)

class StreamlitTestCase:
    """Base class for Streamlit test cases."""
    
    def __init__(self, config: Optional[TestConfig] = None):
        """
        Initializes a StreamlitTestCase with an optional test configuration.
        
        If no configuration is provided, a default TestConfig is used. Sets up a StreamlitTestRunner for executing test operations.
        """
        self.config = config or TestConfig()
        self.runner = StreamlitTestRunner(self.config)
        
    async def setUp(self):
        """
        Clears all Streamlit state before running a test case.
        """
        streamlit_state.clear_all()
        
    async def tearDown(self):
        """
        Cleans up the test environment after a test case by resetting Streamlit state and logging.
        """
        self.runner.cleanup()
        
    async def assertComponentValue(self, key: str, expected_value: Any):
        """
        Asserts that a Streamlit component has the expected value.
        
        Raises an AssertionError if the component's value does not match the expected value.
        """
        result = await self.runner.verify_component_state(key, expected_value)
        assert result.success, result.error or "Component value assertion failed"
        
    async def assertSessionState(self, key: str, expected_value: Any):
        """
        Asserts that the session state value for the given key matches the expected value.
        
        Raises an AssertionError if the actual value does not equal the expected value.
        """
        result = await self.runner.verify_session_state(key, expected_value)
        assert result.success, result.error or "Session state assertion failed"
        
    async def simulateInteraction(self, key: str, value: Any):
        """
        Simulates a user interaction by updating the value of a Streamlit component.
        
        Args:
            key: The unique key identifying the component.
            value: The value to set for the component.
        
        Raises:
            AssertionError: If the interaction simulation fails.
        """
        result = await self.runner.simulate_component_interaction(key, value)
        assert result.success, result.error or "Interaction simulation failed" 
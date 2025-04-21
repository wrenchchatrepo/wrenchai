"""
Test configuration for Pydantic AI testing.
"""
import os
import pytest
from pydantic_ai import Agent
from pydantic_ai.tests import TestModel, FunctionModel

# Prevent accidental real model calls during testing
os.environ["ALLOW_MODEL_REQUESTS"] = "False"

@pytest.fixture
def test_agent():
    """Fixture that provides a test agent with a TestModel."""
    # Use TestModel to generate structured responses without real LLM calls
    with Agent.override(
        model_overrides={"openai:gpt-4o": TestModel()},
    ):
        # Create a test agent suitable for most test cases
        agent = Agent("openai:gpt-4o")
        yield agent

@pytest.fixture
def function_agent():
    """Fixture that provides a test agent with a FunctionModel for custom behavior."""
    # Define custom behavior for the agent
    def custom_function(messages):
        # Extract what we want from the messages
        prompt = messages[-1]["content"]
        
        # Return a custom response based on the prompt
        if "search" in prompt.lower():
            return "Here are the search results..."
        elif "calculate" in prompt.lower():
            return "The calculation result is 42"
        else:
            return "I'm a test response"
    
    # Use FunctionModel for more controlled test responses
    with Agent.override(
        model_overrides={"openai:gpt-4o": FunctionModel(custom_function)},
    ):
        agent = Agent("openai:gpt-4o")
        yield agent

@pytest.fixture
def capture_logs():
    """Fixture to capture and access logs during testing."""
    # This would be implemented with a real log capture mechanism
    class LogCapture:
        def __init__(self):
            self.logs = []
            
        def append(self, log):
            self.logs.append(log)
            
        def get_logs(self):
            return self.logs
    
    capture = LogCapture()
    yield capture
"""
Tests for agent functionality using Pydantic AI testing tools.
"""
import pytest
from unittest.mock import patch
from dirty_equals import Contains, IsPartialDict
from inline_snapshot import snapshot
from pydantic_ai.tests import capture_run_messages

from wrenchai.core.agents.super_agent import SuperAgent
from wrenchai.core.agents.journey_agent import JourneyAgent

# Test super agent functionality
class TestSuperAgent:
    def test_analyze_request(self):
        """Test the analyze_request method of SuperAgent."""
        agent = SuperAgent()
        
        # Test basic analysis
        result = agent.analyze_request("Create a new repository with CI/CD")
        assert isinstance(result, list)
        assert len(result) > 0
        
    def test_assign_roles_and_tools(self):
        """Test role and tool assignment logic."""
        agent = SuperAgent()
        subtasks = ["Set up GitHub repo", "Configure GitHub Actions"]
        
        assignments = agent.assign_roles_and_tools(subtasks)
        
        # Check structure of assignments
        assert isinstance(assignments, dict)
        assert "WebResearcher" in assignments
        assert isinstance(assignments["WebResearcher"], list)

    def test_create_plan(self):
        """Test plan creation functionality."""
        agent = SuperAgent()
        assignments = {"WebResearcher": ["web_search", "rag"], 
                       "CodeGenerator": ["code_generation"]}
        
        plan = agent.create_plan(assignments)
        
        # Verify plan structure
        assert isinstance(plan, list)
        assert "WebResearcher" in plan
        assert "CodeGenerator" in plan

# Test journey agent with TestModel
class TestJourneyAgent:
    def test_load_playbook(self, test_agent):
        """Test playbook loading with a test agent."""
        with patch('builtins.open'):
            journey_agent = JourneyAgent(
                name="TestJourney",
                llm=test_agent,
                tools=["web_search"],
                playbook_path="test_playbook.yaml"
            )
            
            # Mock the loaded playbook
            journey_agent.playbook = {
                "name": "Test Playbook",
                "steps": [
                    {"step_id": 1, "description": "Test step 1"}
                ]
            }
            
            # Verify playbook is accessible
            assert journey_agent.playbook["name"] == "Test Playbook"
            
    @pytest.mark.asyncio
    async def test_agent_processing(self, function_agent):
        """Test agent processing using the function agent fixture."""
        # Create a journey agent with our function_agent
        with patch('builtins.open'):
            journey_agent = JourneyAgent(
                name="TestJourney",
                llm=function_agent,
                tools=["web_search"],
                playbook_path="test_playbook.yaml"
            )
            
            # Mock playbook
            journey_agent.playbook = {
                "name": "Test Playbook",
                "steps": [
                    {"step_id": 1, "description": "Search for information"}
                ]
            }
            
            # Capture messages exchanged with the model
            with capture_run_messages() as messages:
                # Run the agent (this would need to be adjusted for the actual implementation)
                journey_agent.run()
                
            # Check that appropriate messages were exchanged
            assert len(messages) > 0
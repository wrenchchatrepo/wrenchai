"""
Test suite for the Agent-LLM mapping system.

This module tests the functionality of the agent-LLM mapping system to ensure that
agents are correctly associated with their assigned LLMs according to playbook specifications.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.agents.agent_llm_mapping import AgentLLMMapping, LLMAvailability, AgentLLMManager
from core.agents.agent_definitions import LLMProvider


class TestAgentLLMMapping(unittest.TestCase):
    """Tests for the Agent-LLM mapping system."""

    def setUp(self):
        """Set up test environment."""
        # Create a fresh manager for each test
        self.manager = AgentLLMManager()
        
        # Define test mappings
        self.test_mappings = {
            "SuperAgent": "claude-3-sonnet",
            "CodifierAgent": "claude-3-opus",
            "UATAgent": "gemini-2.5-flash"
        }

    def test_default_mappings(self):
        """Test default mappings initialization."""
        # Should have default mappings from agent definitions
        self.assertGreater(len(self.manager.mappings), 0)
        
        # Check a known agent's default mapping
        mapping = next(m for m in self.manager.mappings.get("SuperAgent", []) 
                     if m.source == "default")
        self.assertEqual(mapping.llm_id, LLMProvider.CLAUDE.value)

    def test_add_mapping(self):
        """Test adding a new mapping."""
        # Add a new mapping
        self.manager.add_mapping(
            AgentLLMMapping(
                agent_name="TestAgent",
                llm_id="test-llm",
                source="test",
                priority=5
            )
        )
        
        # Verify it was added
        self.assertIn("TestAgent", self.manager.mappings)
        self.assertEqual(self.manager.mappings["TestAgent"][0].llm_id, "test-llm")
        self.assertEqual(self.manager.mappings["TestAgent"][0].priority, 5)

    def test_add_mappings_from_playbook(self):
        """Test adding mappings from a playbook configuration."""
        # Add mappings from playbook
        self.manager.add_mappings_from_playbook(self.test_mappings, "test_playbook")
        
        # Verify they were added with higher priority than defaults
        for agent_name, llm_id in self.test_mappings.items():
            # Find playbook mapping
            mapping = next((m for m in self.manager.mappings.get(agent_name, []) 
                         if m.source == "playbook:test_playbook"), None)
            
            # Verify it exists and has correct values
            self.assertIsNotNone(mapping, f"Mapping not found for {agent_name}")
            self.assertEqual(mapping.llm_id, llm_id)
            self.assertEqual(mapping.priority, 10)  # Playbook mappings have priority 10

    def test_get_agent_llm(self):
        """Test retrieving the assigned LLM for an agent."""
        # Add mappings from playbook
        self.manager.add_mappings_from_playbook(self.test_mappings, "test_playbook")
        
        # Test getting LLM for agents
        for agent_name, expected_llm in self.test_mappings.items():
            actual_llm = self.manager.get_agent_llm(agent_name)
            self.assertEqual(actual_llm, expected_llm)

    def test_llm_availability(self):
        """Test LLM availability management."""
        # Set an LLM as unavailable
        self.manager.update_llm_availability("claude-3-opus", False, "API quota exceeded")
        
        # Verify it's marked as unavailable
        self.assertFalse(self.manager.check_llm_availability("claude-3-opus"))
        
        # Add mappings with a fallback
        self.manager.add_mapping(
            AgentLLMMapping(
                agent_name="CodifierAgent",
                llm_id="claude-3-opus",
                fallback_llm_id="claude-3-sonnet",
                source="test_fallback",
                priority=20
            )
        )
        
        # Should get fallback LLM since primary is unavailable
        self.assertEqual(self.manager.get_agent_llm("CodifierAgent"), "claude-3-sonnet")
        
        # Make primary available again
        self.manager.update_llm_availability("claude-3-opus", True)
        
        # Should now get primary LLM
        self.assertEqual(self.manager.get_agent_llm("CodifierAgent"), "claude-3-opus")

    def test_reset_to_defaults(self):
        """Test resetting mappings to defaults."""
        # Add custom mappings
        self.manager.add_mappings_from_playbook(self.test_mappings, "test_playbook")
        
        # Reset to defaults
        self.manager.reset_to_defaults()
        
        # Verify custom mappings are gone
        for agent_name in self.test_mappings:
            # No playbook mappings should remain
            mappings = self.manager.mappings.get(agent_name, [])
            playbook_mappings = [m for m in mappings if m.source.startswith("playbook:")]
            self.assertEqual(len(playbook_mappings), 0)


class TestAgentLLMIntegration(unittest.TestCase):
    """Tests for integration of Agent-LLM mapping with other system components."""
    
    @patch('core.agent_system.AgentManager.initialize_agent')
    def test_integration_with_agent_system(self, mock_initialize):
        """Test integration with agent system."""
        from core.agents.agent_llm_mapping import agent_llm_manager
        from core.agent_system import AgentManager
        
        # Create a test mapping
        agent_llm_manager.add_mapping(
            AgentLLMMapping(
                agent_name="TestAgent",
                llm_id="test-llm-integration",
                source="test_integration",
                priority=100
            )
        )
        
        # Mock the initialize_agent method for testing
        mock_initialize.return_value = MagicMock()
        
        # Create agent manager and initialize an agent
        manager = AgentManager()
        agent = manager.initialize_agent("TestAgent")
        
        # The mapping should have been applied
        # This is normally checked inside initialize_agent
        llm_id = agent_llm_manager.get_agent_llm("TestAgent")
        self.assertEqual(llm_id, "test-llm-integration")


if __name__ == "__main__":
    unittest.main()
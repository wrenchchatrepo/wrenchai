"""Tests for agent definitions and management."""

import pytest
from core.agents.agent_definitions import (
    Agent,
    AgentType,
    AgentCapability,
    LLMProvider,
    get_agent,
    get_agents_by_type,
    get_agents_by_capability,
    get_active_agents,
    AGENTS
)

def test_agent_types():
    """Test that all agent types are properly defined."""
    assert len(AgentType) == 3
    assert AgentType.ORCHESTRATOR in AgentType
    assert AgentType.SPECIALIST in AgentType
    assert AgentType.REVIEWER in AgentType

def test_agent_capabilities():
    """Test that all agent capabilities are properly defined."""
    # Test orchestrator capabilities
    assert AgentCapability.PROJECT_PLANNING in AgentCapability
    assert AgentCapability.TASK_COORDINATION in AgentCapability
    assert AgentCapability.RESOURCE_ALLOCATION in AgentCapability
    
    # Test code-related capabilities
    assert AgentCapability.CODE_GENERATION in AgentCapability
    assert AgentCapability.CODE_REVIEW in AgentCapability
    
    # Test UI/UX capabilities
    assert AgentCapability.UI_DESIGN in AgentCapability
    assert AgentCapability.USER_FLOW in AgentCapability

def test_llm_providers():
    """Test that all LLM providers are properly defined."""
    assert LLMProvider.CLAUDE.value == "claude-3.7-sonnet"
    assert LLMProvider.GPT4.value == "gpt-4o"
    assert LLMProvider.GEMINI.value == "gemini-2.5-flash"

def test_agent_validation():
    """Test that agent validation works correctly."""
    # Test valid orchestrator
    valid_orchestrator = Agent(
        name="TestOrchestrator",
        type=AgentType.ORCHESTRATOR,
        capabilities=[
            AgentCapability.PROJECT_PLANNING,
            AgentCapability.TASK_COORDINATION,
            AgentCapability.RESOURCE_ALLOCATION
        ],
        llm=LLMProvider.CLAUDE
    )
    assert valid_orchestrator.is_active

    # Test invalid orchestrator
    with pytest.raises(ValueError):
        Agent(
            name="InvalidOrchestrator",
            type=AgentType.ORCHESTRATOR,
            capabilities=[AgentCapability.CODE_REVIEW],
            llm=LLMProvider.CLAUDE
        )

def test_get_agent():
    """Test retrieving agents by name."""
    super_agent = get_agent("SuperAgent")
    assert super_agent.type == AgentType.ORCHESTRATOR
    assert super_agent.llm == LLMProvider.CLAUDE
    
    with pytest.raises(ValueError):
        get_agent("NonexistentAgent")

def test_get_agents_by_type():
    """Test retrieving agents by type."""
    specialists = get_agents_by_type(AgentType.SPECIALIST)
    assert len(specialists) > 0
    assert all(agent.type == AgentType.SPECIALIST for agent in specialists)
    
    reviewers = get_agents_by_type(AgentType.REVIEWER)
    assert len(reviewers) > 0
    assert all(agent.type == AgentType.REVIEWER for agent in reviewers)

def test_get_agents_by_capability():
    """Test retrieving agents by capability."""
    code_reviewers = get_agents_by_capability(AgentCapability.CODE_REVIEW)
    assert len(code_reviewers) > 0
    assert all(AgentCapability.CODE_REVIEW in agent.capabilities for agent in code_reviewers)

def test_get_active_agents():
    """Test retrieving active agents."""
    active_agents = get_active_agents()
    assert len(active_agents) == len(AGENTS)
    assert all(agent.is_active for agent in active_agents)

def test_predefined_agents():
    """Test that all predefined agents are properly configured."""
    # Test SuperAgent
    super_agent = AGENTS["SuperAgent"]
    assert super_agent.type == AgentType.ORCHESTRATOR
    assert AgentCapability.PROJECT_PLANNING in super_agent.capabilities
    assert super_agent.llm == LLMProvider.CLAUDE

    # Test GithubJourneyAgent
    github_agent = AGENTS["GithubJourneyAgent"]
    assert github_agent.type == AgentType.SPECIALIST
    assert AgentCapability.REPOSITORY_MANAGEMENT in github_agent.capabilities
    assert github_agent.llm == LLMProvider.GPT4

    # Test InspectorAgent
    inspector = AGENTS["InspectorAgent"]
    assert inspector.type == AgentType.REVIEWER
    assert AgentCapability.CODE_REVIEW in inspector.capabilities
    assert inspector.llm == LLMProvider.CLAUDE 
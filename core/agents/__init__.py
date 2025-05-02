# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

"""Agent module initialization."""

from .agent_definitions import (
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

from .agent_factory import AgentFactory
from .agent_state import agent_state_manager
from .agent_state_enhanced import async_agent_state_manager
from .agent_state_migration import migrate_state_sync
from .agent_llm_mapping import agent_llm_manager

# Import specialized agent classes
from .codifier_agent import CodifierAgent, Codifier
from .ux_designer_agent import UXDesignerAgent, UXDesigner
from .uat_agent import UAT

__all__ = [
    # Agent definitions
    'Agent',
    'AgentType',
    'AgentCapability',
    'LLMProvider',
    'get_agent',
    'get_agents_by_type',
    'get_agents_by_capability',
    'get_active_agents',
    'AGENTS',
    
    # Factory and managers
    'AgentFactory',
    'agent_state_manager',
    'async_agent_state_manager',
    'migrate_state_sync',
    'agent_llm_manager',
    
    # Specialized agents
    'CodifierAgent',
    'Codifier',
    'UXDesignerAgent',
    'UXDesigner',
    'UAT'
]

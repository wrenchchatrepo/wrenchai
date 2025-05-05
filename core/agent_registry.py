#!/usr/bin/env python3
# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import logging
from typing import Dict, List, Any, Optional, Type, Callable, Tuple

from core.pydantic_integration import PydanticAIIntegration

logger = logging.getLogger("wrenchai.agent_registry")

class AgentRegistry:
    """Registry for agent types and initialization functions"""
    
    def __init__(self):
        """Initialize the agent registry"""
        self.agent_types: Dict[str, Tuple[Type, Callable]] = {}
        self.agents: Dict[str, Any] = {}
        self.pydantic_ai = PydanticAIIntegration()
    
    def register_agent_type(self, 
                         agent_type: str, 
                         agent_class: Type, 
                         init_function: Callable) -> None:
        """Register an agent type with initialization function
        
        Args:
            agent_type: Type name of the agent (e.g., "SuperAgent")
            agent_class: The agent class
            init_function: Function to initialize an instance of this agent
        """
        self.agent_types[agent_type] = (agent_class, init_function)
        logger.info(f"Registered agent type: {agent_type}")
    
    def initialize_agent(self, 
                       agent_type: str,
                       agent_id: Optional[str] = None,
                       model: Optional[str] = None,
                       **kwargs) -> Any:
        """Initialize an agent of the specified type
        
        Args:
            agent_type: Type of agent to initialize
            agent_id: Optional unique ID for this agent instance
            model: Optional LLM model to use
            **kwargs: Additional arguments for agent initialization
            
        Returns:
            Initialized agent instance
        
        Raises:
            ValueError: If the agent type is not registered
        """
        if agent_type not in self.agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Generate an ID if not provided
        if agent_id is None:
            agent_id = f"{agent_type.lower()}_{len(self.agents)}"
        
        # Get the agent class and initialization function
        agent_class, init_function = self.agent_types[agent_type]
        
        # Initialize the agent
        agent = init_function(agent_id=agent_id, model=model, **kwargs)
        
        # Store the agent instance
        self.agents[agent_id] = agent
        
        logger.info(f"Initialized agent: {agent_id} (type: {agent_type})")
        return agent
    
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get an agent by ID
        
        Args:
            agent_id: ID of the agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)
    
    def get_agent_by_type(self, agent_type: str) -> Optional[Any]:
        """Get the first agent of a specific type
        
        Args:
            agent_type: Type of agent to retrieve
            
        Returns:
            Agent instance or None if not found
        """
        for agent in self.agents.values():
            if isinstance(agent, self.agent_types.get(agent_type, (None, None))[0]):
                return agent
        return None

# Import standard agent types and their initialization functions
from core.super_agent import SuperAgent

# Import specialized agent types if available
try:
    from core.agents.github_journey_agent import GitHubJourneyAgent
    GITHUB_JOURNEY_AVAILABLE = True
except ImportError:
    GITHUB_JOURNEY_AVAILABLE = False
    # Create a placeholder class
    class GitHubJourneyAgent: pass

try:
    from core.agents.inspector_agent import InspectorAgent
    INSPECTOR_AVAILABLE = True
except ImportError:
    INSPECTOR_AVAILABLE = False
    # Create a placeholder class
    class InspectorAgent: pass

try:
    from core.agents.journey_agent import JourneyAgent
    JOURNEY_AVAILABLE = True
except ImportError:
    JOURNEY_AVAILABLE = False
    # Create a placeholder class
    class JourneyAgent: pass

# Singleton instance of the agent registry
_registry_instance = None

def get_agent_registry() -> AgentRegistry:
    """Get the singleton agent registry instance
    
    Returns:
        The AgentRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
        _initialize_standard_agents(_registry_instance)
    return _registry_instance

def _initialize_standard_agents(registry: AgentRegistry) -> None:
    """Initialize standard agent types in the registry
    
    Args:
        registry: The agent registry to initialize
    """
    # Register SuperAgent
    registry.register_agent_type(
        "SuperAgent",
        SuperAgent,
        lambda agent_id, model=None, **kwargs: SuperAgent(
            verbose=kwargs.get("verbose", False),
            model=model,
            mcp_config_path=kwargs.get("mcp_config_path", None)
        )
    )
    
    # Register other agent types if available
    if GITHUB_JOURNEY_AVAILABLE:
        registry.register_agent_type(
            "GithubJourneyAgent",
            GitHubJourneyAgent,
            lambda agent_id, model=None, **kwargs: GitHubJourneyAgent(
                name=agent_id, 
                config_path=kwargs.get("config_path", None)
            )
        )
    
    if INSPECTOR_AVAILABLE:
        registry.register_agent_type(
            "InspectorAgent",
            InspectorAgent,
            lambda agent_id, model=None, **kwargs: InspectorAgent(
                name=agent_id, 
                config_path=kwargs.get("config_path", None)
            )
        )
    
    if JOURNEY_AVAILABLE:
        registry.register_agent_type(
            "JourneyAgent",
            JourneyAgent,
            lambda agent_id, model=None, **kwargs: JourneyAgent(
                name=agent_id, 
                config_path=kwargs.get("config_path", None)
            )
        )
"""
Agent adapters for integrating specialized agents with the Wrenchai framework.

These adapters provide compatibility layers to ensure specialized agents work correctly
within the framework, especially for tool usage and state management.
"""

import logging
from typing import Dict, Any, List, Callable, Optional, Union

from .agent_state import agent_state_manager

logger = logging.getLogger(__name__)


class ToolAdapter:
    """Adapter for tool registry compatibility with specialized agents."""
    
    def __init__(self, tool_registry: Any):
        """Initialize the tool adapter.
        
        Args:
            tool_registry: The tool registry from the framework
        """
        self.tool_registry = tool_registry
    
    async def __call__(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool from the registry.
        
        Args:
            tool_name: Name of the tool to call
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Tool execution result
        """
        if not self.tool_registry:
            raise ValueError("Tool registry not available")
            
        try:
            tool_func = self.tool_registry.get_tool(tool_name)
            if not tool_func:
                raise ValueError(f"Tool {tool_name} not found in registry")
                
            result = await tool_func(**kwargs)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e)}


class AgentToolRegistry:
    """Tool registry adapter for specialized agents."""
    
    def __init__(self, tool_registry: Any):
        """Initialize the agent tool registry.
        
        Args:
            tool_registry: The tool registry from the framework
        """
        self.tool_registry = tool_registry
        self.tools: Dict[str, ToolAdapter] = {}
        
    def register_tools(self, tool_names: List[str]):
        """Register tools for the agent.
        
        Args:
            tool_names: List of tool names to register
        """
        for tool_name in tool_names:
            self.tools[tool_name] = ToolAdapter(self.tool_registry)
            
    def get_tool(self, tool_name: str) -> Optional[ToolAdapter]:
        """Get a tool by name.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool adapter or None if not found
        """
        return self.tools.get(tool_name)
        
    def list_tools(self) -> List[str]:
        """List all available tools.
        
        Returns:
            List of tool names
        """
        return list(self.tools.keys())
        

class AgentStateAdapter:
    """Adapter for integrating with agent state management."""
    
    def __init__(self, agent_id: str):
        """Initialize the state adapter.
        
        Args:
            agent_id: ID of the agent
        """
        self.agent_id = agent_id
        
    async def get_state(self, key: str, default: Any = None) -> Any:
        """Get state value.
        
        Args:
            key: State key
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        return agent_state_manager.get_state_entry(self.agent_id, key, default)
        
    async def set_state(self, key: str, value: Any, scope: str = "agent"):
        """Set state value.
        
        Args:
            key: State key
            value: State value
            scope: Scope of the state (agent, operation, workflow)
        """
        agent_state_manager.set_state_entry(
            self.agent_id,
            key,
            value,
            scope=scope
        )
        
    async def get_all_state(self) -> Dict[str, Any]:
        """Get all state entries.
        
        Returns:
            Dictionary of all state entries
        """
        return agent_state_manager.get_all_entries(self.agent_id)
"""Tool Registry Module.

This module provides a registry for tools used by agents in the system.
"""

from typing import Dict, List, Any, Optional, Type, Callable
import logging

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Registry for managing agent tools."""

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance._tools = {}
            cls._instance._tool_providers = {}
        return cls._instance

    def register_tool(self, tool_name: str, tool_provider: Callable, description: str = "") -> None:
        """Register a tool with the registry.
        
        Args:
            tool_name: Name of the tool
            tool_provider: Function that provides the tool implementation
            description: Description of the tool
        """
        logger.debug(f"Registering tool: {tool_name}")
        self._tools[tool_name] = {
            "provider": tool_provider,
            "description": description
        }

    def get_tool(self, tool_name: str) -> Optional[Callable]:
        """Get a tool by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            The tool implementation or None if not found
        """
        if tool_name not in self._tools:
            logger.warning(f"Tool not found: {tool_name}")
            return None
            
        return self._tools[tool_name]["provider"]
    
    def register_tool_provider(self, provider_name: str, provider_fn: Callable) -> None:
        """Register a tool provider.
        
        Args:
            provider_name: Name of the provider
            provider_fn: Provider function
        """
        self._tool_providers[provider_name] = provider_fn
        
    def get_tool_provider(self, provider_name: str) -> Optional[Callable]:
        """Get a tool provider by name.
        
        Args:
            provider_name: Name of the provider
            
        Returns:
            Provider function or None if not found
        """
        return self._tool_providers.get(provider_name)
    
    def list_tools(self) -> List[str]:
        """List all registered tools.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_tool_description(self, tool_name: str) -> str:
        """Get the description for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            Tool description or empty string if not found
        """
        if tool_name not in self._tools:
            return ""
        return self._tools[tool_name].get("description", "")
    
    def get_all_tool_descriptions(self) -> Dict[str, str]:
        """Get descriptions for all tools.
        
        Returns:
            Dictionary of tool names to descriptions
        """
        return {name: self._tools[name].get("description", "") for name in self._tools}
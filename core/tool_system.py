# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import importlib
import logging
from typing import Dict, Any, Callable, List
from core.config_loader import load_config

class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self, config_path: str = "core/configs/tools.yaml"):
        """Initialize the tool registry with configuration"""
        self.config_path = config_path
        self.tools = {}
        self.configs = load_config(config_path)
        self._load_tools()
        
    def _load_tools(self):
        """Load all tools from configuration"""
        for tool_config in self.configs.get('tools', []):
            try:
                # Dynamic import of tool implementation
                module_path, func_name = tool_config['implementation'].rsplit('.', 1)
                module = importlib.import_module(module_path)
                tool_func = getattr(module, func_name)
                
                self.tools[tool_config['name']] = {
                    'function': tool_func,
                    'config': tool_config
                }
                logging.info(f"Loaded tool: {tool_config['name']}")
            except Exception as e:
                logging.error(f"Error loading tool {tool_config['name']}: {e}")
                # For debugging purposes, we'll still register the tool but with a placeholder function
                self.tools[tool_config['name']] = {
                    'function': lambda **kwargs: {"error": f"Tool {tool_config['name']} is not available: {str(e)}"},
                    'config': tool_config
                }
    
    def get_tool(self, tool_name: str) -> Callable:
        """Get a tool by name"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tools[tool_name]['function']
    
    def get_tool_config(self, tool_name: str) -> Dict[str, Any]:
        """Get tool configuration by name"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool {tool_name} not found")
        return self.tools[tool_name]['config']
    
    def get_client(self, tool_name: str) -> Any:
        """Get client instance for a tool (if applicable)"""
        tool_func = self.get_tool(tool_name)
        if hasattr(tool_func, 'get_client'):
            return tool_func.get_client()
        return None
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all available tools"""
        return [
            {
                'name': name,
                'description': tool['config']['description'],
                'parameters': tool['config']['parameters']
            }
            for name, tool in self.tools.items()
        ]
    
    def find_tools_by_capability(self, capability: str) -> List[str]:
        """Find tools that provide a specific capability"""
        # This is a placeholder - in a real implementation, 
        # tools would be tagged with capabilities
        return [name for name, tool in self.tools.items() 
                if capability.lower() in tool['config']['description'].lower()]
    
    def get_tool_dependencies(self, tool_name: str) -> List[str]:
        """Get dependencies for a tool"""
        dependencies = []
        for dependency in self.configs.get('tool_dependencies', []):
            if dependency['primary'] == tool_name:
                dependencies.append(dependency['requires'])
        return dependencies
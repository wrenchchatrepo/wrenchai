# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import importlib
import logging
import time
from typing import Dict, Any, Callable, List, Optional, Tuple, Union
import inspect
from datetime import datetime

from core.config_loader import load_config
from core.tools.tool_response import format_success_response, format_error_response, standardize_legacy_response
from core.tools.tool_authorization import tool_authorization, ToolAuthorizationSystem
from core.tools.tool_dependency import tool_dependency_manager, ToolDependencyManager

class ToolRegistry:
    """Registry for all available tools"""
    
    def __init__(self, config_path: str = "core/configs/tools.yaml"):
        """
        Initializes the ToolRegistry with tool configurations, authorization, and dependency management.
        
        Loads tool definitions from the specified YAML configuration file, sets up internal registries, and integrates authorization and dependency management systems.
        """
        self.config_path = config_path
        self.tools = {}
        self.configs = load_config(config_path)
        self.authorization_system = tool_authorization
        self.dependency_manager = tool_dependency_manager
        self._load_tools()
        
    def _load_tools(self):
        """
        Dynamically loads and registers tool implementations from the configuration.
        
        Attempts to import each tool's implementation as specified in the configuration. On success, registers the tool with its function and configuration. If import fails, registers a placeholder function that returns an error response indicating the tool is unavailable.
        """
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
                    'function': lambda **kwargs: format_error_response(f"Tool {tool_config['name']} is not available: {str(e)}"),
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
        """
        Returns a list of tool names that the specified tool depends on.
        
        Args:
            tool_name: The name of the tool whose dependencies are to be retrieved.
        
        Returns:
            A list of tool names that are required by the specified tool.
        """
        dependencies = []
        for dependency in self.configs.get('tool_dependencies', []):
            if dependency['primary'] == tool_name:
                dependencies.append(dependency['requires'])
        return dependencies
        
    async def execute_tool(self, tool_name: str, agent_role: str, agent_id: str, **kwargs) -> Dict[str, Any]:
        """
        Executes a tool with authorization and dependency checks, returning a standardized response.
        
        Checks if the tool exists, verifies agent authorization, and ensures all dependencies are met before execution. Supports both synchronous and asynchronous tool functions. Records usage statistics and appends warnings if the tool operates with limited functionality due to missing dependencies.
        
        Args:
            tool_name: The name of the tool to execute.
            agent_role: The role of the agent requesting execution.
            agent_id: The identifier of the agent requesting execution.
            **kwargs: Additional parameters specific to the tool.
        
        Returns:
            A standardized dictionary containing the tool's response, including success status, data or error details, and metadata.
        """
        # Check if tool exists
        if tool_name not in self.tools:
            return format_error_response(f"Tool '{tool_name}' not found")
        
        # Check if agent is authorized to use this tool
        can_use, reason = self.authorization_system.can_agent_use_tool(agent_role, tool_name)
        if not can_use:
            return format_error_response(f"Authorization failed: {reason}")
        
        # Check if tool can run based on dependencies
        can_run, run_reason = self.dependency_manager.can_tool_run(tool_name)
        if not can_run:
            return format_error_response(f"Dependency check failed: {run_reason}")
        
        # Execute the tool with timing
        tool_func = self.get_tool(tool_name)
        start_time = time.time()
        success = True
        try:
            # Check if tool function is async
            if inspect.iscoroutinefunction(tool_func):
                result = await tool_func(**kwargs)
            else:
                result = tool_func(**kwargs)
            
            # Standardize the response format if needed
            if not (isinstance(result, dict) and \
                   ("success" in result and ("data" in result or "error" in result)) and \
                   "timestamp" in result):
                result = standardize_legacy_response(result)
        except Exception as e:
            success = False
            result = format_error_response(f"Tool execution error: {str(e)}")
        
        # Record tool usage
        execution_time = time.time() - start_time
        self.authorization_system.register_tool_usage(
            tool_id=tool_name,
            agent_id=agent_id,
            success=success,
            parameters=kwargs,
            execution_time=execution_time
        )
        
        # Add limited functionality warnings if applicable
        limited_functionality = self.dependency_manager.get_limited_functionality(tool_name)
        if limited_functionality and success:
            result.setdefault("meta", {})[
                "limited_functionality"] = f"Limited functionality due to missing dependencies: {', '.join(limited_functionality)}"
        
        return result
    
    def verify_tools_for_agent(self, agent_role: str, required_tools: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Checks whether an agent with the specified role is authorized and able to use all required tools.
        
        Args:
            agent_role: The role of the agent requesting tool access.
            required_tools: A list of tool names that the agent needs access to.
        
        Returns:
            A tuple where the first element is True if all tools are authorized and can run, False otherwise.
            The second element is a dictionary with authorization status, missing tools, and dependency check results for each tool.
        """
        # Check authorization
        auth_status, missing_tools = self.authorization_system.verify_tools_for_agent(
            agent_role, required_tools
        )
        
        # Check tool dependencies if authorization passes
        dependency_status = {}
        if auth_status:
            all_available = True
            for tool_name in required_tools:
                can_run, reason = self.dependency_manager.can_tool_run(tool_name)
                dependency_status[tool_name] = {
                    "can_run": can_run,
                    "reason": reason
                }
                if not can_run:
                    all_available = False
        else:
            all_available = False
        
        return all_available, {
            "authorization": {
                "authorized": auth_status,
                "missing_tools": missing_tools
            },
            "dependencies": dependency_status
        }
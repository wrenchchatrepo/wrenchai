"""Tool authorization system for WrenchAI.

This module provides functionality to:
- Verify tool availability and permissions
- Manage agent tool access
- Track tool usage and rate limits
"""

import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
from pathlib import Path
import os
import yaml

logger = logging.getLogger(__name__)

class ToolAccess(BaseModel):
    """Permission model for tool access."""
    tool_id: str = Field(..., description="Unique identifier for the tool")
    agent_roles: List[str] = Field(default_factory=list, description="Agent roles with access")
    permission_level: str = Field(default="standard", description="Permission level (standard, admin, restricted)")
    max_calls_per_minute: Optional[int] = Field(None, description="Rate limit for calls per minute")
    max_calls_per_hour: Optional[int] = Field(None, description="Rate limit for calls per hour")
    requires_approval: bool = Field(default=False, description="Whether tool usage requires approval")

class ToolUsage(BaseModel):
    """Record of tool usage."""
    tool_id: str = Field(..., description="Unique identifier for the tool")
    agent_id: str = Field(..., description="ID of the agent using the tool")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the tool was used")
    success: bool = Field(..., description="Whether the tool operation succeeded")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters used")
    execution_time: float = Field(..., description="Execution time in seconds")

class ToolAuthorizationSystem:
    """System for managing tool authorization and access control."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initializes the tool authorization system and loads configuration.
        
        If no configuration path is provided, uses the default path for the authorization config file. Sets up internal mappings for tool access, agent permissions, and usage history.
        """
        self.tool_access_map: Dict[str, ToolAccess] = {}
        self.agent_tool_map: Dict[str, Set[str]] = {}
        self.usage_history: List[ToolUsage] = []
        self.config_path = config_path or os.path.join("core", "configs", "tool_authorization.yaml")
        self._load_configuration()
        
    def _load_configuration(self):
        """
        Loads the tool authorization configuration from the specified YAML file.
        
        If the configuration file is missing or an error occurs during loading, creates and loads a default configuration. Parses tool access settings and updates internal mappings for tool permissions and agent roles.
        """
        try:
            config_path = Path(self.config_path)
            if not config_path.exists():
                logger.warning(f"Tool authorization config not found at {self.config_path}")
                self._create_default_config()
                return
                
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                
            # Parse tool access configuration
            for tool_config in config.get('tools', []):
                tool_id = tool_config.get('id')
                if not tool_id:
                    continue
                    
                self.tool_access_map[tool_id] = ToolAccess(
                    tool_id=tool_id,
                    agent_roles=tool_config.get('agent_roles', []),
                    permission_level=tool_config.get('permission_level', 'standard'),
                    max_calls_per_minute=tool_config.get('max_calls_per_minute'),
                    max_calls_per_hour=tool_config.get('max_calls_per_hour'),
                    requires_approval=tool_config.get('requires_approval', False)
                )
                
            # Build agent-to-tool mapping for faster lookups
            self._build_agent_tool_map()
                
            logger.info(f"Loaded tool authorization config with {len(self.tool_access_map)} tools")
        except Exception as e:
            logger.error(f"Error loading tool authorization config: {e}")
            self._create_default_config()
            
    def _create_default_config(self):
        """
        Creates and saves a default tool authorization configuration if none exists.
        
        Initializes the system with predefined tools and permissions, writes the configuration to disk, loads it into memory, and updates internal mappings.
        """
        default_config = {
            'tools': [
                {
                    'id': 'web_search',
                    'agent_roles': ['SuperAgent', 'ResearchAgent'],
                    'permission_level': 'standard',
                    'max_calls_per_minute': 10
                },
                {
                    'id': 'code_execution',
                    'agent_roles': ['CodeGeneratorAgent', 'TestEngineerAgent'],
                    'permission_level': 'restricted',
                    'requires_approval': True
                },
                {
                    'id': 'memory',
                    'agent_roles': ['*'],  # All agents can access memory
                    'permission_level': 'standard'
                }
            ]
        }
        
        try:
            config_path = Path(self.config_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                yaml.dump(default_config, f)
                
            logger.info(f"Created default tool authorization config at {self.config_path}")
            
            # Load the default config
            for tool_config in default_config.get('tools', []):
                tool_id = tool_config.get('id')
                if not tool_id:
                    continue
                    
                self.tool_access_map[tool_id] = ToolAccess(
                    tool_id=tool_id,
                    agent_roles=tool_config.get('agent_roles', []),
                    permission_level=tool_config.get('permission_level', 'standard'),
                    max_calls_per_minute=tool_config.get('max_calls_per_minute'),
                    max_calls_per_hour=tool_config.get('max_calls_per_hour'),
                    requires_approval=tool_config.get('requires_approval', False)
                )
                
            # Build agent-to-tool mapping
            self._build_agent_tool_map()
        except Exception as e:
            logger.error(f"Error creating default tool authorization config: {e}")
    
    def _build_agent_tool_map(self):
        """
        Constructs a mapping from agent roles to sets of tool IDs they are permitted to access.
        
        Agent roles with wildcard access ('*') are excluded from this mapping.
        """
        self.agent_tool_map.clear()
        
        for tool_id, access in self.tool_access_map.items():
            for role in access.agent_roles:
                if role == '*':  # Wildcard for all agents
                    continue
                    
                if role not in self.agent_tool_map:
                    self.agent_tool_map[role] = set()
                self.agent_tool_map[role].add(tool_id)
    
    def is_tool_available(self, tool_id: str) -> bool:
        """
        Checks whether a tool with the given ID exists in the authorization system.
        
        Args:
            tool_id: The unique identifier of the tool to check.
        
        Returns:
            True if the tool is registered and available; False otherwise.
        """
        return tool_id in self.tool_access_map
    
    def can_agent_use_tool(self, agent_role: str, tool_id: str) -> Tuple[bool, Optional[str]]:
        """
        Determines whether an agent role is permitted to use a specified tool.
        
        Checks if the tool exists, verifies the agent's permission (including wildcard access), and enforces any configured rate limits. Returns a tuple indicating whether access is allowed and, if denied, the reason.
        
        Args:
            agent_role: The role of the agent requesting access.
            tool_id: The identifier of the tool to check.
        
        Returns:
            A tuple (allowed, reason), where allowed is True if access is permitted, and reason provides the denial explanation if not.
        """
        # Check if tool exists
        if not self.is_tool_available(tool_id):
            return False, f"Tool '{tool_id}' not found"
        
        access = self.tool_access_map[tool_id]
        
        # Check if agent has permission via wildcard
        if '*' in access.agent_roles:
            # Still check rate limits
            rate_limited, reason = self._check_rate_limits(tool_id)
            if rate_limited:
                return False, reason
            return True, None
        
        # Check if agent has direct permission
        if agent_role in access.agent_roles:
            # Check rate limits
            rate_limited, reason = self._check_rate_limits(tool_id)
            if rate_limited:
                return False, reason
            return True, None
        
        return False, f"Agent '{agent_role}' does not have permission to use tool '{tool_id}'"
    
    def _check_rate_limits(self, tool_id: str) -> Tuple[bool, Optional[str]]:
        """
        Checks whether the specified tool has exceeded its configured rate limits.
        
        Args:
            tool_id: The unique identifier of the tool to check.
        
        Returns:
            A tuple (rate_limited, reason), where rate_limited is True if the tool's per-minute or per-hour call limit has been exceeded, and reason provides a descriptive message if rate limited; otherwise, (False, None).
        """
        access = self.tool_access_map[tool_id]
        
        now = datetime.utcnow()
        
        # Check per-minute limit
        if access.max_calls_per_minute is not None:
            one_minute_ago = now - timedelta(minutes=1)
            minute_count = sum(1 for usage in self.usage_history 
                              if usage.tool_id == tool_id and usage.timestamp >= one_minute_ago)
            
            if minute_count >= access.max_calls_per_minute:
                return True, f"Rate limit exceeded: {minute_count}/{access.max_calls_per_minute} calls per minute"
        
        # Check per-hour limit
        if access.max_calls_per_hour is not None:
            one_hour_ago = now - timedelta(hours=1)
            hour_count = sum(1 for usage in self.usage_history 
                            if usage.tool_id == tool_id and usage.timestamp >= one_hour_ago)
            
            if hour_count >= access.max_calls_per_hour:
                return True, f"Rate limit exceeded: {hour_count}/{access.max_calls_per_hour} calls per hour"
        
        return False, None
    
    def register_tool_usage(self, tool_id: str, agent_id: str, success: bool, 
                           parameters: Dict[str, Any], execution_time: float):
        """
                           Records a tool usage event with details such as agent, parameters, success status, and execution time.
                           
                           Adds the usage record to the internal history, maintaining a maximum of 10,000 recent entries.
                           """
        usage = ToolUsage(
            tool_id=tool_id,
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            success=success,
            parameters=parameters,
            execution_time=execution_time
        )
        
        self.usage_history.append(usage)
        
        # Maintain a reasonable history size
        if len(self.usage_history) > 10000:
            # Keep only the last 10,000 records
            self.usage_history = self.usage_history[-10000:]
    
    def get_agent_allowed_tools(self, agent_role: str) -> List[str]:
        """
        Returns a list of tool IDs that the specified agent role is permitted to use.
        
        Includes tools explicitly assigned to the agent role and those available to all roles via wildcard access.
        """
        # Tools explicitly assigned to this agent
        allowed_tools = set(self.agent_tool_map.get(agent_role, set()))
        
        # Add tools available to all agents
        for tool_id, access in self.tool_access_map.items():
            if '*' in access.agent_roles:
                allowed_tools.add(tool_id)
        
        return list(allowed_tools)
    
    def verify_tools_for_agent(self, agent_role: str, required_tools: List[str]) -> Tuple[bool, List[str]]:
        """
        Checks if an agent role has access to all specified tools.
        
        Args:
            agent_role: The role of the agent to check permissions for.
            required_tools: List of tool IDs that the agent needs access to.
        
        Returns:
            A tuple where the first element is True if the agent can access all required tools,
            and the second element is a list of tool IDs the agent cannot access.
        """
        allowed_tools = set(self.get_agent_allowed_tools(agent_role))
        missing_tools = [tool for tool in required_tools if tool not in allowed_tools]
        
        return len(missing_tools) == 0, missing_tools
    
    def get_tool_usage_stats(self, tool_id: Optional[str] = None, 
                            agent_id: Optional[str] = None,
                            start_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
                            Returns usage statistics for tools, optionally filtered by tool ID, agent ID, and start time.
                            
                            Args:
                                tool_id: If provided, only usage records for this tool are included.
                                agent_id: If provided, only usage records for this agent are included.
                                start_time: If provided, only usage records from this time onward are included.
                            
                            Returns:
                                A dictionary containing total calls, successful calls, success rate, and per-tool call counts.
                            """
        filtered_usage = self.usage_history
        
        if tool_id:
            filtered_usage = [usage for usage in filtered_usage if usage.tool_id == tool_id]
        
        if agent_id:
            filtered_usage = [usage for usage in filtered_usage if usage.agent_id == agent_id]
        
        if start_time:
            filtered_usage = [usage for usage in filtered_usage if usage.timestamp >= start_time]
        
        # Calculate statistics
        total_calls = len(filtered_usage)
        successful_calls = sum(1 for usage in filtered_usage if usage.success)
        
        tool_counts = {}
        for usage in filtered_usage:
            tool_counts[usage.tool_id] = tool_counts.get(usage.tool_id, 0) + 1
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls > 0 else 0,
            "tool_counts": tool_counts
        }

# Global instance for application-wide use
tool_authorization = ToolAuthorizationSystem()
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
        """Initialize the tool authorization system.
        
        Args:
            config_path: Path to authorization configuration file
        """
        self.tool_access_map: Dict[str, ToolAccess] = {}
        self.agent_tool_map: Dict[str, Set[str]] = {}
        self.usage_history: List[ToolUsage] = []
        self.config_path = config_path or os.path.join("core", "configs", "tool_authorization.yaml")
        self._load_configuration()
        
    def _load_configuration(self):
        """Load tool authorization configuration."""
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
        """Create a default configuration if none exists."""
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
        """Build a mapping of agents to their allowed tools."""
        self.agent_tool_map.clear()
        
        for tool_id, access in self.tool_access_map.items():
            for role in access.agent_roles:
                if role == '*':  # Wildcard for all agents
                    continue
                    
                if role not in self.agent_tool_map:
                    self.agent_tool_map[role] = set()
                self.agent_tool_map[role].add(tool_id)
    
    def is_tool_available(self, tool_id: str) -> bool:
        """Check if a tool is available in the system.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            True if tool is available, False otherwise
        """
        return tool_id in self.tool_access_map
    
    def can_agent_use_tool(self, agent_role: str, tool_id: str) -> Tuple[bool, Optional[str]]:
        """Check if an agent can use a specific tool.
        
        Args:
            agent_role: Role of the agent
            tool_id: Tool identifier
            
        Returns:
            Tuple of (allowed, reason)
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
        """Check if a tool has exceeded its rate limits.
        
        Args:
            tool_id: Tool identifier
            
        Returns:
            Tuple of (rate_limited, reason)
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
        """Register a tool usage event.
        
        Args:
            tool_id: Tool identifier
            agent_id: Agent identifier
            success: Whether the operation succeeded
            parameters: Tool parameters used
            execution_time: Execution time in seconds
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
        """Get a list of tools an agent is allowed to use.
        
        Args:
            agent_role: Role of the agent
            
        Returns:
            List of tool identifiers
        """
        # Tools explicitly assigned to this agent
        allowed_tools = set(self.agent_tool_map.get(agent_role, set()))
        
        # Add tools available to all agents
        for tool_id, access in self.tool_access_map.items():
            if '*' in access.agent_roles:
                allowed_tools.add(tool_id)
        
        return list(allowed_tools)
    
    def verify_tools_for_agent(self, agent_role: str, required_tools: List[str]) -> Tuple[bool, List[str]]:
        """Verify that an agent has access to all required tools.
        
        Args:
            agent_role: Role of the agent
            required_tools: List of required tool identifiers
            
        Returns:
            Tuple of (all_available, missing_tools)
        """
        allowed_tools = set(self.get_agent_allowed_tools(agent_role))
        missing_tools = [tool for tool in required_tools if tool not in allowed_tools]
        
        return len(missing_tools) == 0, missing_tools
    
    def get_tool_usage_stats(self, tool_id: Optional[str] = None, 
                            agent_id: Optional[str] = None,
                            start_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Get usage statistics for tools.
        
        Args:
            tool_id: Optional filter by tool ID
            agent_id: Optional filter by agent ID
            start_time: Optional filter from start time
            
        Returns:
            Dictionary with usage statistics
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
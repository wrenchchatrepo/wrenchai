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
    
    def __init__(self, agent_id: str, use_enhanced: bool = True):
        """Initialize the state adapter.
        
        Args:
            agent_id: ID of the agent
            use_enhanced: Whether to use the enhanced state manager
        """
        self.agent_id = agent_id
        self.use_enhanced = use_enhanced
        
        # Import the appropriate state manager
        if use_enhanced:
            from .agent_state_enhanced import async_agent_state_manager
            self.state_manager = async_agent_state_manager
        else:
            from .agent_state import agent_state_manager
            self.state_manager = agent_state_manager
        
    async def get_state(self, key: str, default: Any = None, workflow_id: Optional[str] = None) -> Any:
        """Get state value.
        
        Args:
            key: State key
            default: Default value if key not found
            workflow_id: Optional workflow ID for workflow-scoped entries
            
        Returns:
            State value or default
        """
        if self.use_enhanced:
            return await self.state_manager.get_state_entry(self.agent_id, key, default, workflow_id)
        else:
            return self.state_manager.get_state_entry(self.agent_id, key, default)
        
    async def set_state(self, key: str, value: Any, scope: str = "agent", 
                       visibility: str = "private", ttl: Optional[int] = None, 
                       tags: Optional[List[str]] = None, workflow_id: Optional[str] = None):
        """Set state value.
        
        Args:
            key: State key
            value: State value
            scope: Scope of the state (agent, operation, workflow)
            visibility: Visibility of the state (private, shared, global)
            ttl: Time-to-live in seconds (None for no expiration)
            tags: Tags for categorizing the entry
            workflow_id: Optional workflow ID for workflow-scoped entries
        """
        if self.use_enhanced:
            await self.state_manager.set_state_entry(
                self.agent_id,
                key,
                value,
                scope=scope,
                visibility=visibility,
                ttl=ttl,
                tags=tags,
                workflow_id=workflow_id
            )
        else:
            self.state_manager.set_state_entry(
                self.agent_id,
                key,
                value,
                scope=scope,
                visibility=visibility,
                ttl=ttl,
                tags=tags or []
            )
        
    async def get_all_state(self, visibility: Optional[str] = None,
                          scope: Optional[str] = None, 
                          tags: Optional[List[str]] = None,
                          workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all state entries.
        
        Args:
            visibility: Optional visibility filter
            scope: Optional scope filter
            tags: Optional tags filter
            workflow_id: Optional workflow ID for workflow-scoped entries
            
        Returns:
            Dictionary of all state entries
        """
        if self.use_enhanced:
            return await self.state_manager.get_all_entries(
                self.agent_id, 
                visibility=visibility,
                scope=scope,
                tags=tags,
                workflow_id=workflow_id
            )
        else:
            return self.state_manager.get_all_entries(
                self.agent_id,
                visibility=visibility,
                scope=scope,
                tags=tags
            )
            
    async def delete_state(self, key: str, visibility: Optional[str] = None,
                         workflow_id: Optional[str] = None) -> bool:
        """Delete a state entry.
        
        Args:
            key: State key
            visibility: Optional visibility to target specific storage
            workflow_id: Optional workflow ID for workflow-scoped entries
            
        Returns:
            Whether the entry was deleted
        """
        if self.use_enhanced:
            return await self.state_manager.delete_state_entry(
                self.agent_id,
                key,
                visibility=visibility,
                workflow_id=workflow_id
            )
        else:
            return self.state_manager.delete_state_entry(
                self.agent_id,
                key,
                visibility=visibility
            )
            
    async def register_operation(self, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """Register an operation in the agent's history.
        
        Args:
            operation: Operation name
            metadata: Additional metadata about the operation
        """
        if self.use_enhanced:
            await self.state_manager.register_operation(
                self.agent_id,
                operation,
                metadata=metadata
            )
        else:
            self.state_manager.register_operation(
                self.agent_id,
                operation
            )
            
    async def get_operations_history(self) -> Union[List[str], List[Dict[str, Any]]]:
        """Get the operation history for the agent.
        
        Returns:
            List of operations
        """
        if self.use_enhanced:
            return await self.state_manager.get_operations_history(self.agent_id)
        else:
            return self.state_manager.get_operations_history(self.agent_id)
            
    async def create_snapshot(self, scope: str = "agent") -> Optional[str]:
        """Create a snapshot of the current state.
        
        Args:
            scope: Scope of entries to include in the snapshot
            
        Returns:
            Snapshot ID or None if not supported
        """
        if self.use_enhanced:
            snapshot = await self.state_manager.create_context_snapshot(
                self.agent_id,
                scope=scope
            )
            return snapshot.snapshot_id
        else:
            return None
            
    async def restore_snapshot(self, snapshot_id: str, scope: str = "agent") -> bool:
        """Restore state from a snapshot.
        
        Args:
            snapshot_id: ID of the snapshot
            scope: Scope of entries to restore
            
        Returns:
            Whether the restore was successful
        """
        if self.use_enhanced:
            return await self.state_manager.restore_context_snapshot(
                self.agent_id,
                snapshot_id,
                scope=scope
            )
        else:
            return False
            
    async def start_transaction(self):
        """Start a transaction for batched state changes."""
        if self.use_enhanced:
            return await self.state_manager.transaction(self.agent_id).__aenter__()
        else:
            return None
            
    async def get_workflow_context(self, workflow_id: str) -> Dict[str, Any]:
        """Get the context for a specific workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow context or empty dict if not found
        """
        if self.use_enhanced:
            workflow_state = await self.state_manager.get_workflow_state(workflow_id)
            if workflow_state:
                return workflow_state.context
            return {}
        else:
            return {}
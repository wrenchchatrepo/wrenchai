"""Enhanced agent state management for WrenchAI.

This module provides improved functionality to:
- Maintain agent state across operations (async support)
- Persist context between operations with transactions
- Share state between agents with context isolation
- Manage workflow-level state
- Support serialization of complex types
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set, Union, Tuple
# Using Pydantic v2 validators according to Pydantic AI guidelines
# Reference: https://ai.pydantic.dev/agents/
from pydantic import BaseModel, Field, create_model, validator, model_validator
from datetime import datetime
import json
from pathlib import Path
import os
import threading
import uuid
import pickle
import base64
import hashlib
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class AgentStateEntry(BaseModel):
    """Enhanced model for a single state entry."""
    key: str = Field(..., description="State entry key")
    value: Any = Field(..., description="State entry value")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the entry was created/updated")
    scope: str = Field(default="agent", description="Scope of the entry (agent, operation, workflow)")
    visibility: str = Field(default="private", description="Visibility of the entry (private, shared, global)")
    ttl: Optional[int] = Field(None, description="Time-to-live in seconds (None for no expiration)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the entry")
    type_info: str = Field(default="", description="Type information for complex objects")
    version: int = Field(default=1, description="Entry version for conflict resolution")
    checksum: Optional[str] = Field(None, description="Content checksum for integrity verification")

    class Config:
        arbitrary_types_allowed = True
        
    @validator('value', pre=True)
    def serialize_complex_types(cls, v):
        """Serialize complex types that aren't JSON serializable."""
        # Try standard JSON serialization first
        try:
            json.dumps(v)
            return v
        except (TypeError, OverflowError):
            # For complex types, use pickle + base64
            serialized = base64.b64encode(pickle.dumps(v)).decode('utf-8')
            return {"__serialized__": True, "data": serialized, "format": "pickle"}
    
    # Using model_validator according to Pydantic AI guidelines for model-level validation
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @model_validator(mode='after')
    def compute_checksum(self) -> 'AgentStateEntry':
        """Compute checksum for integrity verification."""
        if self.checksum is None:
            # Create a checksum of the key and serialized value
            value_str = str(self.value or '')
            combined = f"{self.key or ''}{value_str}{self.version or 1}"
            self.checksum = hashlib.sha256(combined.encode()).hexdigest()
        return self
    
    def deserialize_value(self) -> Any:
        """Deserialize the value if it's a complex type."""
        if isinstance(self.value, dict) and self.value.get("__serialized__"):
            if self.value.get("format") == "pickle":
                try:
                    return pickle.loads(base64.b64decode(self.value["data"]))
                except Exception as e:
                    logger.error(f"Failed to deserialize value: {e}")
                    return None
        return self.value


class ContextSnapshot(BaseModel):
    """A snapshot of context at a point in time."""
    snapshot_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique snapshot ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the snapshot was created")
    entries: Dict[str, AgentStateEntry] = Field(default_factory=dict, description="State entries in the snapshot")
    parent_snapshot: Optional[str] = Field(None, description="Parent snapshot ID if this is an incremental snapshot")
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the snapshot."""
        if key in self.entries:
            entry = self.entries[key]
            return entry.deserialize_value()
        return default


class WorkflowState(BaseModel):
    """Model for workflow-level state."""
    workflow_id: str = Field(..., description="ID of the workflow")
    workflow_name: str = Field(..., description="Name of the workflow")
    status: str = Field(default="created", description="Workflow status")
    started_at: Optional[datetime] = Field(None, description="When the workflow started")
    completed_at: Optional[datetime] = Field(None, description="When the workflow completed")
    current_step: Optional[str] = Field(None, description="Current step ID")
    step_history: List[str] = Field(default_factory=list, description="History of steps executed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Workflow context")
    checkpoints: List[str] = Field(default_factory=list, description="List of checkpoint IDs")
    
    def create_checkpoint(self, context_snapshot: ContextSnapshot) -> str:
        """Create a checkpoint with the current context."""
        self.checkpoints.append(context_snapshot.snapshot_id)
        return context_snapshot.snapshot_id


class AgentState(BaseModel):
    """Enhanced model for agent state."""
    agent_id: str = Field(..., description="ID of the agent")
    agent_name: str = Field(..., description="Name of the agent")
    entries: Dict[str, AgentStateEntry] = Field(default_factory=dict, description="State entries")
    operation_history: List[Dict[str, Any]] = Field(default_factory=list, description="History of operations performed with metadata")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When the state was last updated")
    version: int = Field(default=1, description="State version counter")
    workflow_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Workflow-specific data indexed by workflow ID")
    tags: Dict[str, List[str]] = Field(default_factory=dict, description="Tags for categorizing state entries")
    
    def add_operation(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add an operation to the history with timestamp and metadata."""
        self.operation_history.append({
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.last_updated = datetime.utcnow()
        self.version += 1
    
    def add_to_workflow(self, workflow_id: str, data: Dict[str, Any]) -> None:
        """Add data to a specific workflow context."""
        if workflow_id not in self.workflow_data:
            self.workflow_data[workflow_id] = {}
        self.workflow_data[workflow_id].update(data)
        self.last_updated = datetime.utcnow()
        self.version += 1
    
    def tag_entry(self, key: str, tag: str) -> bool:
        """Tag a state entry for easier retrieval."""
        if key in self.entries:
            if tag not in self.entries[key].tags:
                self.entries[key].tags.append(tag)
            
            # Update the tag index
            if tag not in self.tags:
                self.tags[tag] = []
            if key not in self.tags[tag]:
                self.tags[tag].append(key)
            
            return True
        return False
    
    def get_entries_by_tag(self, tag: str) -> Dict[str, Any]:
        """Get all entries with a specific tag."""
        result = {}
        if tag in self.tags:
            for key in self.tags[tag]:
                if key in self.entries:
                    # Deserialize if needed
                    value = self.entries[key].deserialize_value()
                    result[key] = value
        return result


class TransactionLog(BaseModel):
    """Log for state transactions."""
    transaction_id: str = Field(..., description="Transaction ID")
    agent_id: str = Field(..., description="Agent ID")
    operations: List[Dict[str, Any]] = Field(default_factory=list, description="Operations in the transaction")
    status: str = Field(default="pending", description="Transaction status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When the transaction was created")
    completed_at: Optional[datetime] = Field(None, description="When the transaction was completed")
    
    def add_operation(self, operation: str, key: str, value: Any = None, previous_value: Any = None) -> None:
        """Add an operation to the transaction log."""
        self.operations.append({
            "operation": operation,
            "key": key,
            "value": value,
            "previous_value": previous_value,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def mark_complete(self) -> None:
        """Mark the transaction as complete."""
        self.status = "complete"
        self.completed_at = datetime.utcnow()
    
    def mark_rolled_back(self) -> None:
        """Mark the transaction as rolled back."""
        self.status = "rolled_back"
        self.completed_at = datetime.utcnow()


class StateTransaction:
    """Transaction class for state changes."""
    
    def __init__(self, agent_id: str, manager: 'AsyncAgentStateManager'):
        """Initialize a new transaction."""
        self.transaction_id = str(uuid.uuid4())
        self.agent_id = agent_id
        self.manager = manager
        self.log = TransactionLog(
            transaction_id=self.transaction_id,
            agent_id=agent_id
        )
        self.committed = False
        self.rolled_back = False
    
    async def set(self, key: str, value: Any, **kwargs) -> None:
        """Set a value in the transaction."""
        # Get current value for rollback
        current_value = await self.manager.get_state_entry(self.agent_id, key)
        self.log.add_operation("set", key, value, current_value)
        
        # Apply immediately but track for possible rollback
        await self.manager.set_state_entry(
            self.agent_id, key, value, **kwargs, _transaction_id=self.transaction_id
        )
    
    async def delete(self, key: str, **kwargs) -> None:
        """Delete a value in the transaction."""
        # Get current value for rollback
        current_value = await self.manager.get_state_entry(self.agent_id, key)
        self.log.add_operation("delete", key, None, current_value)
        
        # Apply immediately but track for possible rollback
        await self.manager.delete_state_entry(
            self.agent_id, key, **kwargs, _transaction_id=self.transaction_id
        )
    
    async def commit(self) -> bool:
        """Commit the transaction."""
        if self.rolled_back:
            return False
        
        self.log.mark_complete()
        await self.manager.commit_transaction(self.transaction_id)
        self.committed = True
        return True
    
    async def rollback(self) -> bool:
        """Roll back the transaction."""
        if self.committed:
            return False
        
        self.log.mark_rolled_back()
        await self.manager.rollback_transaction(self.transaction_id)
        self.rolled_back = True
        return True


class AsyncAgentStateManager:
    """Enhanced async manager for agent state."""
    
    def __init__(self, persistence_dir: Optional[str] = None):
        """Initialize the async agent state manager.
        
        Args:
            persistence_dir: Directory for state persistence (optional)
        """
        self.agent_states: Dict[str, AgentState] = {}
        self.shared_state: Dict[str, AgentStateEntry] = {}
        self.global_state: Dict[str, AgentStateEntry] = {}
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.context_snapshots: Dict[str, ContextSnapshot] = {}
        self.persistence_dir = persistence_dir or os.path.join("data", "agent_states")
        self.transaction_logs: Dict[str, TransactionLog] = {}
        self._lock = asyncio.Lock()
        
        # Create persistence directory if it doesn't exist
        if self.persistence_dir:
            os.makedirs(self.persistence_dir, exist_ok=True)
            os.makedirs(os.path.join(self.persistence_dir, "workflows"), exist_ok=True)
            os.makedirs(os.path.join(self.persistence_dir, "snapshots"), exist_ok=True)
            os.makedirs(os.path.join(self.persistence_dir, "transactions"), exist_ok=True)
    
    async def get_agent_state(self, agent_id: str) -> AgentState:
        """Get the state for an agent, creating it if it doesn't exist.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent state
        """
        async with self._lock:
            if agent_id not in self.agent_states:
                # Try to load from persistence
                state = await self._load_state(agent_id)
                if not state:
                    # Create new state
                    state = AgentState(agent_id=agent_id, agent_name=agent_id)
                self.agent_states[agent_id] = state
                
            return self.agent_states[agent_id]
    
    async def _load_state(self, agent_id: str) -> Optional[AgentState]:
        """Load agent state from persistence.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent state or None if not found
        """
        if not self.persistence_dir:
            return None
            
        state_path = os.path.join(self.persistence_dir, f"{agent_id}.json")
        if not os.path.exists(state_path):
            return None
            
        try:
            with open(state_path, 'r') as f:
                state_dict = json.load(f)
                return AgentState.parse_obj(state_dict)
        except Exception as e:
            logger.error(f"Error loading state for agent {agent_id}: {e}")
            return None
    
    async def _save_state(self, agent_id: str):
        """Save agent state to persistence.
        
        Args:
            agent_id: ID of the agent
        """
        if not self.persistence_dir:
            return
            
        state = self.agent_states.get(agent_id)
        if not state:
            return
            
        state_path = os.path.join(self.persistence_dir, f"{agent_id}.json")
        try:
            with open(state_path, 'w') as f:
                json.dump(state.dict(), f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error saving state for agent {agent_id}: {e}")
    
    async def set_state_entry(self, agent_id: str, key: str, value: Any, 
                         scope: str = "agent", visibility: str = "private",
                         ttl: Optional[int] = None, tags: Optional[List[str]] = None,
                         workflow_id: Optional[str] = None,
                         _transaction_id: Optional[str] = None):
        """Set a state entry for an agent.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            value: Entry value
            scope: Scope of the entry (agent, operation, workflow)
            visibility: Visibility of the entry (private, shared, global)
            ttl: Time-to-live in seconds (None for no expiration)
            tags: Tags for categorizing the entry
            workflow_id: Optional workflow ID for workflow-scoped entries
            _transaction_id: Internal parameter for transaction tracking
        """
        async with self._lock:
            # Add type info to support better serialization/deserialization
            type_info = type(value).__name__ if value is not None else "None"
            
            entry = AgentStateEntry(
                key=key,
                value=value,
                timestamp=datetime.utcnow(),
                scope=scope,
                visibility=visibility,
                ttl=ttl,
                tags=tags or []
            )
            
            # Determine where to store based on visibility
            if visibility == "global":
                self.global_state[key] = entry
            elif visibility == "shared":
                self.shared_state[key] = entry
            else:
                # Private to the agent
                state = await self.get_agent_state(agent_id)
                
                # Add to agent state
                state.entries[key] = entry
                state.last_updated = datetime.utcnow()
                state.version += 1
                
                # Tag the entry if tags provided
                if tags:
                    for tag in tags:
                        state.tag_entry(key, tag)
                
                # Add to workflow context if workflow_id provided
                if workflow_id and scope == "workflow":
                    if workflow_id not in state.workflow_data:
                        state.workflow_data[workflow_id] = {}
                    state.workflow_data[workflow_id][key] = value
                
                # Save to persistence
                await self._save_state(agent_id)
    
    async def get_state_entry(self, agent_id: str, key: str, default: Any = None,
                        workflow_id: Optional[str] = None) -> Any:
        """Get a state entry for an agent.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            default: Default value if entry not found
            workflow_id: Optional workflow ID for workflow-scoped entries
            
        Returns:
            Entry value or default if not found
        """
        async with self._lock:
            # Check if we want a workflow-specific entry
            if workflow_id:
                state = await self.get_agent_state(agent_id)
                if workflow_id in state.workflow_data and key in state.workflow_data[workflow_id]:
                    return state.workflow_data[workflow_id][key]
            
            # Check in order: agent state, shared state, global state
            state = await self.get_agent_state(agent_id)
            
            # First check agent's private state
            if key in state.entries:
                entry = state.entries[key]
                # Check TTL
                if entry.ttl is not None:
                    age = (datetime.utcnow() - entry.timestamp).total_seconds()
                    if age > entry.ttl:
                        # Entry expired
                        del state.entries[key]
                        await self._save_state(agent_id)
                        return default
                return entry.deserialize_value()
            
            # Check shared state
            if key in self.shared_state:
                entry = self.shared_state[key]
                # Check TTL
                if entry.ttl is not None:
                    age = (datetime.utcnow() - entry.timestamp).total_seconds()
                    if age > entry.ttl:
                        # Entry expired
                        del self.shared_state[key]
                        return default
                return entry.deserialize_value()
            
            # Check global state
            if key in self.global_state:
                entry = self.global_state[key]
                # Check TTL
                if entry.ttl is not None:
                    age = (datetime.utcnow() - entry.timestamp).total_seconds()
                    if age > entry.ttl:
                        # Entry expired
                        del self.global_state[key]
                        return default
                return entry.deserialize_value()
            
            return default
    
    async def delete_state_entry(self, agent_id: str, key: str, visibility: Optional[str] = None,
                           workflow_id: Optional[str] = None,
                           _transaction_id: Optional[str] = None) -> bool:
        """Delete a state entry.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            visibility: Optional visibility to target specific storage
            workflow_id: Optional workflow ID for workflow-scoped entries
            _transaction_id: Internal parameter for transaction tracking
            
        Returns:
            Whether the entry was deleted
        """
        async with self._lock:
            deleted = False
            
            # Handle workflow-specific deletion
            if workflow_id:
                state = await self.get_agent_state(agent_id)
                if workflow_id in state.workflow_data and key in state.workflow_data[workflow_id]:
                    del state.workflow_data[workflow_id][key]
                    deleted = True
                    await self._save_state(agent_id)
            
            # Check based on visibility
            if visibility in [None, "private"]:
                state = await self.get_agent_state(agent_id)
                if key in state.entries:
                    del state.entries[key]
                    state.last_updated = datetime.utcnow()
                    state.version += 1
                    deleted = True
                    # Save to persistence
                    await self._save_state(agent_id)
            
            if visibility in [None, "shared"] and key in self.shared_state:
                del self.shared_state[key]
                deleted = True
            
            if visibility in [None, "global"] and key in self.global_state:
                del self.global_state[key]
                deleted = True
                
            return deleted
    
    async def register_operation(self, agent_id: str, operation: str, metadata: Optional[Dict[str, Any]] = None):
        """Register an operation in the agent's history.
        
        Args:
            agent_id: ID of the agent
            operation: Operation name
            metadata: Additional metadata about the operation
        """
        async with self._lock:
            state = await self.get_agent_state(agent_id)
            state.add_operation(operation, metadata)
            
            # Save to persistence
            await self._save_state(agent_id)
    
    async def get_operations_history(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get the operation history for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of operation details
        """
        async with self._lock:
            state = await self.get_agent_state(agent_id)
            return state.operation_history.copy()
    
    async def get_all_entries(self, agent_id: str, visibility: Optional[str] = None,
                        scope: Optional[str] = None, tags: Optional[List[str]] = None,
                        workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get all state entries for an agent, filtered by criteria.
        
        Args:
            agent_id: ID of the agent
            visibility: Optional visibility filter
            scope: Optional scope filter
            tags: Optional tags filter (entries must have ALL specified tags)
            workflow_id: Optional workflow ID for workflow-scoped entries
            
        Returns:
            Dictionary of key-value pairs
        """
        async with self._lock:
            # Check if we want workflow-specific entries
            if workflow_id:
                state = await self.get_agent_state(agent_id)
                if workflow_id in state.workflow_data:
                    return state.workflow_data[workflow_id].copy()
                return {}
            
            result = {}
            
            def add_matching_entries(entries):
                for key, entry in entries.items():
                    # Check filters
                    if scope and entry.scope != scope:
                        continue
                    if tags and not all(tag in entry.tags for tag in tags):
                        continue
                    
                    # Check TTL
                    if entry.ttl is not None:
                        age = (datetime.utcnow() - entry.timestamp).total_seconds()
                        if age > entry.ttl:
                            # Entry expired, skip
                            continue
                    
                    result[key] = entry.deserialize_value()
            
            # Add entries from appropriate sources based on visibility
            if visibility in [None, "private"]:
                state = await self.get_agent_state(agent_id)
                add_matching_entries(state.entries)
            
            if visibility in [None, "shared"]:
                add_matching_entries(self.shared_state)
            
            if visibility in [None, "global"]:
                add_matching_entries(self.global_state)
                
            return result
    
    async def get_entries_by_tag(self, agent_id: str, tag: str) -> Dict[str, Any]:
        """Get all entries with a specific tag.
        
        Args:
            agent_id: ID of the agent
            tag: Tag to filter by
            
        Returns:
            Dictionary of key-value pairs
        """
        async with self._lock:
            state = await self.get_agent_state(agent_id)
            return state.get_entries_by_tag(tag)
    
    async def clear_agent_state(self, agent_id: str):
        """Clear all state for an agent.
        
        Args:
            agent_id: ID of the agent
        """
        async with self._lock:
            if agent_id in self.agent_states:
                # Create a fresh state
                agent_name = self.agent_states[agent_id].agent_name
                self.agent_states[agent_id] = AgentState(agent_id=agent_id, agent_name=agent_name)
                
                # Save to persistence
                await self._save_state(agent_id)
    
    async def clear_all_states(self):
        """Clear all agent states."""
        async with self._lock:
            self.agent_states.clear()
            self.shared_state.clear()
            self.global_state.clear()
            self.workflow_states.clear()
            self.context_snapshots.clear()
            
            # Clear persistence files
            if self.persistence_dir:
                for file in os.listdir(self.persistence_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.persistence_dir, file))
    
    # Workflow state management
    
    async def create_workflow(self, workflow_id: str, workflow_name: str) -> WorkflowState:
        """Create a new workflow state.
        
        Args:
            workflow_id: ID of the workflow
            workflow_name: Name of the workflow
            
        Returns:
            New workflow state
        """
        async with self._lock:
            workflow_state = WorkflowState(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                started_at=datetime.utcnow()
            )
            self.workflow_states[workflow_id] = workflow_state
            
            # Save to persistence
            await self._save_workflow_state(workflow_id)
            
            return workflow_state
    
    async def _save_workflow_state(self, workflow_id: str):
        """Save workflow state to persistence.
        
        Args:
            workflow_id: ID of the workflow
        """
        if not self.persistence_dir:
            return
            
        workflow_state = self.workflow_states.get(workflow_id)
        if not workflow_state:
            return
            
        workflow_path = os.path.join(self.persistence_dir, "workflows", f"{workflow_id}.json")
        try:
            with open(workflow_path, 'w') as f:
                json.dump(workflow_state.dict(), f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error saving workflow state {workflow_id}: {e}")
    
    async def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """Get a workflow state.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Workflow state or None if not found
        """
        async with self._lock:
            if workflow_id not in self.workflow_states:
                # Try to load from persistence
                workflow_path = os.path.join(self.persistence_dir, "workflows", f"{workflow_id}.json")
                if os.path.exists(workflow_path):
                    try:
                        with open(workflow_path, 'r') as f:
                            workflow_dict = json.load(f)
                            self.workflow_states[workflow_id] = WorkflowState.parse_obj(workflow_dict)
                    except Exception as e:
                        logger.error(f"Error loading workflow state {workflow_id}: {e}")
                        return None
                else:
                    return None
            
            return self.workflow_states[workflow_id]
    
    async def update_workflow_state(self, workflow_id: str, 
                             status: Optional[str] = None,
                             current_step: Optional[str] = None,
                             context_update: Optional[Dict[str, Any]] = None):
        """Update a workflow state.
        
        Args:
            workflow_id: ID of the workflow
            status: Optional new status
            current_step: Optional current step
            context_update: Optional context updates
            
        Returns:
            Updated workflow state or None if not found
        """
        async with self._lock:
            workflow_state = await self.get_workflow_state(workflow_id)
            if not workflow_state:
                return None
            
            if status:
                workflow_state.status = status
                if status == "completed":
                    workflow_state.completed_at = datetime.utcnow()
            
            if current_step:
                workflow_state.current_step = current_step
                workflow_state.step_history.append(current_step)
            
            if context_update:
                workflow_state.context.update(context_update)
            
            # Save to persistence
            await self._save_workflow_state(workflow_id)
            
            return workflow_state
    
    # Context snapshots for point-in-time recovery
    
    async def create_context_snapshot(self, agent_id: str, 
                               scope: str = "agent",
                               parent_snapshot: Optional[str] = None) -> ContextSnapshot:
        """Create a snapshot of the current context.
        
        Args:
            agent_id: ID of the agent
            scope: Scope of entries to include in the snapshot
            parent_snapshot: Optional parent snapshot ID for incremental snapshots
            
        Returns:
            New context snapshot
        """
        async with self._lock:
            # Get entries based on scope
            entries = {}
            
            if scope == "agent":
                state = await self.get_agent_state(agent_id)
                entries = state.entries
            elif scope == "shared":
                entries = self.shared_state
            elif scope == "global":
                entries = self.global_state
            elif scope == "all":
                state = await self.get_agent_state(agent_id)
                entries = {**state.entries, **self.shared_state, **self.global_state}
            
            # Create snapshot
            snapshot = ContextSnapshot(
                entries=entries.copy(),
                parent_snapshot=parent_snapshot
            )
            
            self.context_snapshots[snapshot.snapshot_id] = snapshot
            
            # Save to persistence
            await self._save_context_snapshot(snapshot.snapshot_id)
            
            return snapshot
    
    async def _save_context_snapshot(self, snapshot_id: str):
        """Save context snapshot to persistence.
        
        Args:
            snapshot_id: ID of the snapshot
        """
        if not self.persistence_dir:
            return
            
        snapshot = self.context_snapshots.get(snapshot_id)
        if not snapshot:
            return
            
        snapshot_path = os.path.join(self.persistence_dir, "snapshots", f"{snapshot_id}.json")
        try:
            with open(snapshot_path, 'w') as f:
                json.dump(snapshot.dict(), f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error saving context snapshot {snapshot_id}: {e}")
    
    async def get_context_snapshot(self, snapshot_id: str) -> Optional[ContextSnapshot]:
        """Get a context snapshot.
        
        Args:
            snapshot_id: ID of the snapshot
            
        Returns:
            Context snapshot or None if not found
        """
        async with self._lock:
            if snapshot_id not in self.context_snapshots:
                # Try to load from persistence
                snapshot_path = os.path.join(self.persistence_dir, "snapshots", f"{snapshot_id}.json")
                if os.path.exists(snapshot_path):
                    try:
                        with open(snapshot_path, 'r') as f:
                            snapshot_dict = json.load(f)
                            self.context_snapshots[snapshot_id] = ContextSnapshot.parse_obj(snapshot_dict)
                    except Exception as e:
                        logger.error(f"Error loading context snapshot {snapshot_id}: {e}")
                        return None
                else:
                    return None
            
            return self.context_snapshots[snapshot_id]
    
    async def restore_context_snapshot(self, agent_id: str, snapshot_id: str,
                                scope: str = "agent") -> bool:
        """Restore context from a snapshot.
        
        Args:
            agent_id: ID of the agent
            snapshot_id: ID of the snapshot
            scope: Scope of entries to restore
            
        Returns:
            Whether the restore was successful
        """
        async with self._lock:
            snapshot = await self.get_context_snapshot(snapshot_id)
            if not snapshot:
                return False
            
            # Restore entries based on scope
            if scope == "agent":
                state = await self.get_agent_state(agent_id)
                state.entries = {k: v for k, v in snapshot.entries.items() if v.visibility == "private"}
                await self._save_state(agent_id)
            elif scope == "shared":
                self.shared_state = {k: v for k, v in snapshot.entries.items() if v.visibility == "shared"}
            elif scope == "global":
                self.global_state = {k: v for k, v in snapshot.entries.items() if v.visibility == "global"}
            elif scope == "all":
                state = await self.get_agent_state(agent_id)
                
                # Split entries by visibility
                private_entries = {k: v for k, v in snapshot.entries.items() if v.visibility == "private"}
                shared_entries = {k: v for k, v in snapshot.entries.items() if v.visibility == "shared"}
                global_entries = {k: v for k, v in snapshot.entries.items() if v.visibility == "global"}
                
                # Restore
                state.entries = private_entries
                self.shared_state = shared_entries
                self.global_state = global_entries
                
                await self._save_state(agent_id)
            
            return True
    
    # Transaction management
    
    @asynccontextmanager
    async def transaction(self, agent_id: str):
        """Create a transaction for batched state changes.
        
        Args:
            agent_id: ID of the agent
            
        Yields:
            Transaction object
        """
        transaction = StateTransaction(agent_id, self)
        try:
            yield transaction
            # Auto-commit if not explicitly committed or rolled back
            if not transaction.committed and not transaction.rolled_back:
                await transaction.commit()
        except Exception as e:
            # Auto-rollback on exception
            if not transaction.committed and not transaction.rolled_back:
                await transaction.rollback()
            raise e
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            Whether the commit was successful
        """
        async with self._lock:
            if transaction_id not in self.transaction_logs:
                return False
            
            transaction = self.transaction_logs[transaction_id]
            transaction.mark_complete()
            
            # Save transaction log
            await self._save_transaction_log(transaction_id)
            
            return True
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """Roll back a transaction.
        
        Args:
            transaction_id: ID of the transaction
            
        Returns:
            Whether the rollback was successful
        """
        async with self._lock:
            if transaction_id not in self.transaction_logs:
                return False
            
            transaction = self.transaction_logs[transaction_id]
            
            # Perform rollback operations in reverse order
            for op in reversed(transaction.operations):
                if op["operation"] == "set":
                    # Restore previous value
                    await self.set_state_entry(
                        transaction.agent_id,
                        op["key"],
                        op["previous_value"],
                        _transaction_id=None
                    )
                elif op["operation"] == "delete" and op["previous_value"] is not None:
                    # Restore deleted value
                    await self.set_state_entry(
                        transaction.agent_id,
                        op["key"],
                        op["previous_value"],
                        _transaction_id=None
                    )
            
            transaction.mark_rolled_back()
            
            # Save transaction log
            await self._save_transaction_log(transaction_id)
            
            return True
    
    async def _save_transaction_log(self, transaction_id: str):
        """Save transaction log to persistence.
        
        Args:
            transaction_id: ID of the transaction
        """
        if not self.persistence_dir:
            return
            
        transaction = self.transaction_logs.get(transaction_id)
        if not transaction:
            return
            
        transaction_path = os.path.join(self.persistence_dir, "transactions", f"{transaction_id}.json")
        try:
            with open(transaction_path, 'w') as f:
                json.dump(transaction.dict(), f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error saving transaction log {transaction_id}: {e}")


# Global instance
async_agent_state_manager = AsyncAgentStateManager()
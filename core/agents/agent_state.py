"""Agent state management for WrenchAI.

This module provides functionality to:
- Maintain agent state across operations
- Persist context between operations
- Share state between agents
"""

import logging
from typing import Dict, Any, Optional, List, Set
from pydantic import BaseModel, Field
from datetime import datetime
import json
from pathlib import Path
import os
import threading

logger = logging.getLogger(__name__)

class AgentStateEntry(BaseModel):
    """Model for a single state entry."""
    key: str = Field(..., description="State entry key")
    value: Any = Field(..., description="State entry value")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the entry was created/updated")
    scope: str = Field(default="agent", description="Scope of the entry (agent, operation, workflow)")
    visibility: str = Field(default="private", description="Visibility of the entry (private, shared, global)")
    ttl: Optional[int] = Field(None, description="Time-to-live in seconds (None for no expiration)")
    tags: List[str] = Field(default_factory=list, description="Tags for categorizing the entry")

class AgentState(BaseModel):
    """Model for agent state."""
    agent_id: str = Field(..., description="ID of the agent")
    agent_name: str = Field(..., description="Name of the agent")
    entries: Dict[str, AgentStateEntry] = Field(default_factory=dict, description="State entries")
    operation_history: List[str] = Field(default_factory=list, description="History of operations performed")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="When the state was last updated")
    version: int = Field(default=1, description="State version counter")

class AgentStateManager:
    """Manager for agent state."""
    
    def __init__(self, persistence_dir: Optional[str] = None):
        """
        Initializes the AgentStateManager with optional state persistence.
        
        If a persistence directory is provided, agent states will be saved and loaded from that location; otherwise, a default directory is used. Sets up in-memory structures for agent, shared, and global states, and ensures thread safety.
        """
        self.agent_states: Dict[str, AgentState] = {}
        self.shared_state: Dict[str, AgentStateEntry] = {}
        self.global_state: Dict[str, AgentStateEntry] = {}
        self.persistence_dir = persistence_dir or os.path.join("data", "agent_states")
        self._lock = threading.RLock()
        
        # Create persistence directory if it doesn't exist
        if self.persistence_dir:
            os.makedirs(self.persistence_dir, exist_ok=True)
    
    def get_agent_state(self, agent_id: str) -> AgentState:
        """
        Retrieves the state object for the specified agent, loading from persistence or creating a new state if necessary.
        
        Args:
            agent_id: Unique identifier of the agent.
        
        Returns:
            The AgentState instance associated with the given agent ID.
        """
        with self._lock:
            if agent_id not in self.agent_states:
                # Try to load from persistence
                state = self._load_state(agent_id)
                if not state:
                    # Create new state
                    state = AgentState(agent_id=agent_id, agent_name=agent_id)
                self.agent_states[agent_id] = state
                
            return self.agent_states[agent_id]
    
    def _load_state(self, agent_id: str) -> Optional[AgentState]:
        """
        Loads the persisted state for the specified agent from disk.
        
        Attempts to read the agent's state from a JSON file in the persistence directory. Returns None if the file does not exist or if an error occurs during loading.
        
        Args:
            agent_id: The unique identifier of the agent.
        
        Returns:
            The loaded AgentState object, or None if not found or on error.
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
    
    def _save_state(self, agent_id: str):
        """
        Persists the specified agent's state to a JSON file in the persistence directory.
        
        If the persistence directory is not set or the agent state does not exist, the function does nothing. Errors during saving are logged.
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
    
    def set_state_entry(self, agent_id: str, key: str, value: Any, 
                       scope: str = "agent", visibility: str = "private",
                       ttl: Optional[int] = None, tags: Optional[List[str]] = None):
        """
                       Creates or updates a state entry for an agent with specified scope, visibility, TTL, and tags.
                       
                       Depending on the visibility, the entry is stored as private (per-agent), shared (across agents), or global (system-wide). Private entries update the agent's state and are persisted to disk. Shared and global entries are stored in memory.
                       
                       Args:
                           agent_id: Unique identifier of the agent.
                           key: Key for the state entry.
                           value: Value to associate with the key.
                           scope: Logical scope of the entry ("agent", "operation", or "workflow").
                           visibility: Determines entry accessibility ("private", "shared", or "global").
                           ttl: Optional time-to-live in seconds; if set, entry expires after this duration.
                           tags: Optional list of tags for categorizing the entry.
                       """
        with self._lock:
            entry = AgentStateEntry(
                key=key,
                value=value,
                timestamp=datetime.utcnow(),
                scope=scope,
                visibility=visibility,
                ttl=ttl,
                tags=tags or []
            )
            
            # Store in appropriate location based on visibility
            if visibility == "global":
                self.global_state[key] = entry
            elif visibility == "shared":
                self.shared_state[key] = entry
            else:
                # Private to the agent
                state = self.get_agent_state(agent_id)
                state.entries[key] = entry
                state.last_updated = datetime.utcnow()
                state.version += 1
                
                # Save to persistence
                self._save_state(agent_id)
    
    def get_state_entry(self, agent_id: str, key: str, default: Any = None) -> Any:
        """
        Retrieves the value of a state entry for an agent by key, checking private, shared, and global scopes.
        
        If the entry exists and has not expired (based on TTL), its value is returned. If the entry is missing or expired, the provided default value is returned.
        """
        with self._lock:
            # Check in order: agent state, shared state, global state
            state = self.get_agent_state(agent_id)
            
            # First check agent's private state
            if key in state.entries:
                entry = state.entries[key]
                # Check TTL
                if entry.ttl is not None:
                    age = (datetime.utcnow() - entry.timestamp).total_seconds()
                    if age > entry.ttl:
                        # Entry expired
                        del state.entries[key]
                        return default
                return entry.value
            
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
                return entry.value
            
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
                return entry.value
            
            return default
    
    def delete_state_entry(self, agent_id: str, key: str, visibility: Optional[str] = None) -> bool:
        """
        Deletes a state entry for an agent by key and optional visibility.
        
        If visibility is not specified, attempts to delete the entry from private, shared, and global states. Updates agent state metadata and persists changes for private entries.
        
        Args:
            agent_id: The ID of the agent whose state entry should be deleted.
            key: The key of the state entry to delete.
            visibility: Optional visibility filter ("private", "shared", or "global") to restrict deletion scope.
        
        Returns:
            True if the entry was deleted from any state; False otherwise.
        """
        with self._lock:
            deleted = False
            
            # Check based on visibility
            if visibility in [None, "private"]:
                state = self.get_agent_state(agent_id)
                if key in state.entries:
                    del state.entries[key]
                    state.last_updated = datetime.utcnow()
                    state.version += 1
                    deleted = True
                    # Save to persistence
                    self._save_state(agent_id)
            
            if visibility in [None, "shared"] and key in self.shared_state:
                del self.shared_state[key]
                deleted = True
            
            if visibility in [None, "global"] and key in self.global_state:
                del self.global_state[key]
                deleted = True
                
            return deleted
    
    def register_operation(self, agent_id: str, operation: str):
        """
        Appends an operation to the specified agent's operation history.
        
        Updates the agent's last updated timestamp and persists the state.
        """
        with self._lock:
            state = self.get_agent_state(agent_id)
            state.operation_history.append(operation)
            state.last_updated = datetime.utcnow()
            
            # Save to persistence
            self._save_state(agent_id)
    
    def get_operations_history(self, agent_id: str) -> List[str]:
        """
        Returns a copy of the operation history for the specified agent.
        
        Args:
            agent_id: The unique identifier of the agent.
        
        Returns:
            A list of operation names performed by the agent, in chronological order.
        """
        with self._lock:
            state = self.get_agent_state(agent_id)
            return state.operation_history.copy()
    
    def get_all_entries(self, agent_id: str, visibility: Optional[str] = None,
                       scope: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
                       Retrieves all state entries for an agent matching the specified visibility, scope, and tags.
                       
                       Entries are filtered to include only those that match all provided tags and the specified scope. Expired entries (based on TTL) are excluded. Returns a dictionary mapping entry keys to their values from private, shared, and global state as determined by the visibility filter.
                       
                       Args:
                           agent_id: The unique identifier of the agent.
                           visibility: If provided, limits results to entries with this visibility ("private", "shared", or "global").
                           scope: If provided, limits results to entries with this scope.
                           tags: If provided, only entries containing all specified tags are included.
                       
                       Returns:
                           A dictionary of entry keys to their corresponding values for all matching state entries.
                       """
        with self._lock:
            result = {}
            
            def add_matching_entries(entries):
                """
                Adds entries to the result dictionary if they match the specified scope, tags, and TTL filters.
                
                Entries are included only if their scope matches the given scope (if specified), contain all required tags (if specified), and have not expired based on their TTL.
                """
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
                    
                    result[key] = entry.value
            
            # Add entries from appropriate sources based on visibility
            if visibility in [None, "private"]:
                state = self.get_agent_state(agent_id)
                add_matching_entries(state.entries)
            
            if visibility in [None, "shared"]:
                add_matching_entries(self.shared_state)
            
            if visibility in [None, "global"]:
                add_matching_entries(self.global_state)
                
            return result
    
    def clear_agent_state(self, agent_id: str):
        """
        Resets the specified agent's state to an empty state, preserving the agent's name.
        
        All existing state entries and operation history for the agent are removed. The cleared state is saved to persistent storage.
        """
        with self._lock:
            if agent_id in self.agent_states:
                # Create a fresh state
                agent_name = self.agent_states[agent_id].agent_name
                self.agent_states[agent_id] = AgentState(agent_id=agent_id, agent_name=agent_name)
                
                # Save to persistence
                self._save_state(agent_id)
    
    def clear_all_states(self):
        """
        Removes all agent, shared, and global state entries from memory and deletes all persisted state files.
        
        This operation resets the entire state management system, clearing both in-memory data and all JSON files in the persistence directory if set.
        """
        with self._lock:
            self.agent_states.clear()
            self.shared_state.clear()
            self.global_state.clear()
            
            # Clear persistence files
            if self.persistence_dir:
                for file in os.listdir(self.persistence_dir):
                    if file.endswith('.json'):
                        os.remove(os.path.join(self.persistence_dir, file))

# Global instance
agent_state_manager = AgentStateManager()
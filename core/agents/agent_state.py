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
        """Initialize the agent state manager.
        
        Args:
            persistence_dir: Directory for state persistence (optional)
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
        """Get the state for an agent, creating it if it doesn't exist.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent state
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
    
    def _save_state(self, agent_id: str):
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
    
    def set_state_entry(self, agent_id: str, key: str, value: Any, 
                       scope: str = "agent", visibility: str = "private",
                       ttl: Optional[int] = None, tags: Optional[List[str]] = None):
        """Set a state entry for an agent.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            value: Entry value
            scope: Scope of the entry (agent, operation, workflow)
            visibility: Visibility of the entry (private, shared, global)
            ttl: Time-to-live in seconds (None for no expiration)
            tags: Tags for categorizing the entry
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
        """Get a state entry for an agent.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            default: Default value if entry not found
            
        Returns:
            Entry value or default if not found
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
        """Delete a state entry.
        
        Args:
            agent_id: ID of the agent
            key: Entry key
            visibility: Optional visibility to target specific storage
            
        Returns:
            Whether the entry was deleted
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
        """Register an operation in the agent's history.
        
        Args:
            agent_id: ID of the agent
            operation: Operation name
        """
        with self._lock:
            state = self.get_agent_state(agent_id)
            state.operation_history.append(operation)
            state.last_updated = datetime.utcnow()
            
            # Save to persistence
            self._save_state(agent_id)
    
    def get_operations_history(self, agent_id: str) -> List[str]:
        """Get the operation history for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            List of operation names
        """
        with self._lock:
            state = self.get_agent_state(agent_id)
            return state.operation_history.copy()
    
    def get_all_entries(self, agent_id: str, visibility: Optional[str] = None,
                       scope: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get all state entries for an agent, filtered by criteria.
        
        Args:
            agent_id: ID of the agent
            visibility: Optional visibility filter
            scope: Optional scope filter
            tags: Optional tags filter (entries must have ALL specified tags)
            
        Returns:
            Dictionary of key-value pairs
        """
        with self._lock:
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
        """Clear all state for an agent.
        
        Args:
            agent_id: ID of the agent
        """
        with self._lock:
            if agent_id in self.agent_states:
                # Create a fresh state
                agent_name = self.agent_states[agent_id].agent_name
                self.agent_states[agent_id] = AgentState(agent_id=agent_id, agent_name=agent_name)
                
                # Save to persistence
                self._save_state(agent_id)
    
    def clear_all_states(self):
        """Clear all agent states."""
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
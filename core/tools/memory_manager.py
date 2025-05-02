"""Memory Manager Module.

This module provides memory management functionality for agents.
"""

from typing import Dict, List, Any, Optional, Type, Callable
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class MemoryManager:
    """Memory manager for agents to store and retrieve information."""

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MemoryManager, cls).__new__(cls)
            cls._instance._memories = {}
            cls._instance._memory_dir = os.path.join(os.path.dirname(__file__), "memory_store")
            os.makedirs(cls._instance._memory_dir, exist_ok=True)
        return cls._instance

    def store_memory(self, agent_id: str, memory_type: str, data: Dict[str, Any]) -> str:
        """Store a memory for an agent.
        
        Args:
            agent_id: ID of the agent
            memory_type: Type of memory (e.g., 'conversation', 'task')
            data: Memory data to store
            
        Returns:
            Memory ID
        """
        if agent_id not in self._memories:
            self._memories[agent_id] = {}
            
        if memory_type not in self._memories[agent_id]:
            self._memories[agent_id][memory_type] = []
        
        # Add timestamp and generate ID
        memory_data = {
            "timestamp": datetime.now().isoformat(),
            "data": data,
            "id": f"{agent_id}_{memory_type}_{len(self._memories[agent_id][memory_type])}"
        }
        
        self._memories[agent_id][memory_type].append(memory_data)
        
        # Persist to disk
        self._save_memory(agent_id, memory_type, memory_data)
        
        return memory_data["id"]
        
    def get_memories(self, agent_id: str, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve memories for an agent.
        
        Args:
            agent_id: ID of the agent
            memory_type: Type of memory to retrieve, or None for all types
            
        Returns:
            List of memories
        """
        if agent_id not in self._memories:
            return []
            
        if memory_type is None:
            # Flatten all memory types
            all_memories = []
            for m_type in self._memories[agent_id]:
                all_memories.extend(self._memories[agent_id][m_type])
            return all_memories
            
        if memory_type not in self._memories[agent_id]:
            return []
            
        return self._memories[agent_id][memory_type]
        
    def get_memory_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory by ID.
        
        Args:
            memory_id: ID of the memory
            
        Returns:
            Memory data or None if not found
        """
        # Parse agent_id and memory_type from memory_id
        try:
            agent_id, memory_type, _ = memory_id.split('_', 2)
        except ValueError:
            logger.error(f"Invalid memory_id format: {memory_id}")
            return None
            
        memories = self.get_memories(agent_id, memory_type)
        for memory in memories:
            if memory.get("id") == memory_id:
                return memory
                
        return None
        
    def clear_memories(self, agent_id: str, memory_type: Optional[str] = None) -> None:
        """Clear memories for an agent.
        
        Args:
            agent_id: ID of the agent
            memory_type: Type of memory to clear, or None for all types
        """
        if agent_id not in self._memories:
            return
            
        if memory_type is None:
            self._memories[agent_id] = {}
        elif memory_type in self._memories[agent_id]:
            self._memories[agent_id][memory_type] = []
            
    def _save_memory(self, agent_id: str, memory_type: str, memory_data: Dict[str, Any]) -> None:
        """Save memory to disk.
        
        Args:
            agent_id: ID of the agent
            memory_type: Type of memory
            memory_data: Memory data to save
        """
        try:
            agent_dir = os.path.join(self._memory_dir, agent_id)
            os.makedirs(agent_dir, exist_ok=True)
            
            memory_file = os.path.join(agent_dir, f"{memory_type}.json")
            
            existing_data = []
            if os.path.exists(memory_file):
                try:
                    with open(memory_file, 'r') as f:
                        existing_data = json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    logger.error(f"Error reading memory file {memory_file}: {e}")
            
            existing_data.append(memory_data)
            
            with open(memory_file, 'w') as f:
                json.dump(existing_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
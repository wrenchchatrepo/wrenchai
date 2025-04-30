"""
Memory Manager for WrenchAI.

This module provides persistent memory storage for agents, allowing them to maintain
context across sessions and store important information.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, UTC
from pathlib import Path
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class MemoryEntry(BaseModel):
    """Model for memory entries."""
    key: str
    data: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MemoryManager:
    """
    Manages persistent memory for agents.
    
    This class provides both in-memory caching and file-based persistence
    for storing agent memory entries.
    """
    
    def __init__(self, storage_dir: str = None):
        """
        Initialize MemoryManager.
        
        Args:
            storage_dir: Directory for persistent storage.
                       Defaults to './memory_store'
        """
        self.storage_dir = storage_dir or os.path.join(os.path.dirname(__file__), 'memory_store')
        self.cache: Dict[str, MemoryEntry] = {}
        self._setup_storage()
        
    def _setup_storage(self) -> None:
        """Create storage directory if it doesn't exist."""
        os.makedirs(self.storage_dir, exist_ok=True)
        
    def _get_storage_path(self, key: str) -> str:
        """Get storage path for a memory key."""
        return os.path.join(self.storage_dir, f"{key}.json")
        
    async def store(self, key: str, data: Any, metadata: Dict[str, Any] = None) -> bool:
        """
        Store data in memory.
        
        Args:
            key: Unique identifier for the memory entry
            data: Data to store
            metadata: Optional metadata about the memory entry
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If key is None or empty
        """
        if not key:
            raise ValueError("Key cannot be None or empty")
            
        try:
            entry = MemoryEntry(
                key=key,
                data=data,
                metadata=metadata or {}
            )
            
            # Update cache
            self.cache[key] = entry
            
            # Persist to file
            path = self._get_storage_path(key)
            async with asyncio.Lock():
                with open(path, 'w') as f:
                    json.dump(entry.model_dump(), f, default=str)
                    
            logger.info(f"Stored memory entry: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory entry {key}: {str(e)}")
            return False
            
    async def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve data from memory.
        
        Args:
            key: Unique identifier for the memory entry
            
        Returns:
            The stored data if found, None otherwise
            
        Raises:
            ValueError: If key is None or empty
        """
        if not key:
            raise ValueError("Key cannot be None or empty")
            
        try:
            # Check cache first
            if key in self.cache:
                return self.cache[key].data
                
            # Check persistent storage
            path = self._get_storage_path(key)
            if not os.path.exists(path):
                return None
                
            async with asyncio.Lock():
                with open(path, 'r') as f:
                    entry = MemoryEntry(**json.load(f))
                    self.cache[key] = entry
                    return entry.data
                    
        except Exception as e:
            logger.error(f"Failed to retrieve memory entry {key}: {str(e)}")
            return None
            
    async def delete(self, key: str) -> bool:
        """
        Delete data from memory.
        
        Args:
            key: Unique identifier for the memory entry
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If key is None or empty
        """
        if not key:
            raise ValueError("Key cannot be None or empty")
            
        try:
            # Remove from cache
            self.cache.pop(key, None)
            
            # Remove from persistent storage
            path = self._get_storage_path(key)
            if os.path.exists(path):
                async with asyncio.Lock():
                    os.remove(path)
                    
            logger.info(f"Deleted memory entry: {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory entry {key}: {str(e)}")
            return False
            
    async def list_entries(self) -> List[str]:
        """
        List all memory entry keys.
        
        Returns:
            List of memory entry keys
        """
        try:
            # Get all JSON files in storage directory
            files = Path(self.storage_dir).glob("*.json")
            return [f.stem for f in files]
            
        except Exception as e:
            logger.error(f"Failed to list memory entries: {str(e)}")
            return []
            
    async def clear(self) -> bool:
        """
        Clear all memory entries.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Clear cache
            self.cache.clear()
            
            # Clear persistent storage
            async with asyncio.Lock():
                for file in Path(self.storage_dir).glob("*.json"):
                    os.remove(file)
                    
            logger.info("Cleared all memory entries")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear memory entries: {str(e)}")
            return False

# Create global instance
memory_manager = MemoryManager()

async def manage_memory(action: str, key: str = None, data: Any = None) -> Dict[str, Any]:
    """
    Manage persistent memory for agents.
    
    Args:
        action: Action to perform ('store', 'retrieve', 'delete', 'list', 'clear')
        key: Memory entry key (required for store/retrieve/delete)
        data: Data to store (required for store action)
        
    Returns:
        Dict containing operation result
    """
    try:
        if action == "store":
            if not key or data is None:
                raise ValueError("Key and data required for store action")
            success = await memory_manager.store(key, data)
            return {
                "success": success,
                "message": "Memory entry stored successfully" if success else "Failed to store memory entry"
            }
            
        elif action == "retrieve":
            if not key:
                raise ValueError("Key required for retrieve action")
            data = await memory_manager.retrieve(key)
            return {
                "success": True,
                "data": data
            } if data is not None else {
                "success": False,
                "error": f"Memory entry not found: {key}"
            }
            
        elif action == "delete":
            if not key:
                raise ValueError("Key required for delete action")
            success = await memory_manager.delete(key)
            return {
                "success": success,
                "message": "Memory entry deleted successfully" if success else "Failed to delete memory entry"
            }
            
        elif action == "list":
            entries = await memory_manager.list_entries()
            return {
                "success": True,
                "entries": entries
            }
            
        elif action == "clear":
            success = await memory_manager.clear()
            return {
                "success": success,
                "message": "Memory cleared successfully" if success else "Failed to clear memory"
            }
            
        else:
            raise ValueError(f"Invalid action: {action}")
            
    except Exception as e:
        logger.error(f"Memory operation failed: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        } 
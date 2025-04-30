"""
Tests for the Memory Manager implementation.

This module contains tests for all core functionality of the memory manager,
including storage, retrieval, deletion, and error handling.
"""

import os
import pytest
import tempfile
import shutil
import asyncio
from datetime import datetime
from typing import Dict, Any

from core.tools.memory import MemoryManager, MemoryEntry, manage_memory

@pytest.fixture
async def memory_manager():
    """Fixture that provides a MemoryManager instance with temporary storage."""
    # Create temporary directory for test storage
    temp_dir = tempfile.mkdtemp()
    manager = MemoryManager(storage_dir=temp_dir)
    
    yield manager
    
    # Cleanup after tests
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_store_and_retrieve(memory_manager: MemoryManager):
    """Test storing and retrieving memory entries."""
    test_data = {"key": "value", "nested": {"data": 123}}
    test_key = "test_entry"
    
    # Store data
    success = await memory_manager.store(test_key, test_data)
    assert success is True
    
    # Retrieve data
    retrieved_data = await memory_manager.retrieve(test_key)
    assert retrieved_data == test_data
    
    # Check cache
    assert test_key in memory_manager.cache
    assert memory_manager.cache[test_key].data == test_data

@pytest.mark.asyncio
async def test_store_with_metadata(memory_manager: MemoryManager):
    """Test storing memory entries with metadata."""
    test_data = {"value": 42}
    test_key = "test_with_metadata"
    test_metadata = {"category": "test", "priority": "high"}
    
    # Store with metadata
    success = await memory_manager.store(test_key, test_data, metadata=test_metadata)
    assert success is True
    
    # Verify metadata in cache
    assert test_key in memory_manager.cache
    assert memory_manager.cache[test_key].metadata == test_metadata

@pytest.mark.asyncio
async def test_delete(memory_manager: MemoryManager):
    """Test deleting memory entries."""
    test_key = "test_delete"
    test_data = {"delete_me": True}
    
    # Store then delete
    await memory_manager.store(test_key, test_data)
    success = await memory_manager.delete(test_key)
    assert success is True
    
    # Verify deletion
    retrieved_data = await memory_manager.retrieve(test_key)
    assert retrieved_data is None
    assert test_key not in memory_manager.cache

@pytest.mark.asyncio
async def test_list_entries(memory_manager: MemoryManager):
    """Test listing memory entries."""
    test_entries = {
        "entry1": {"data": 1},
        "entry2": {"data": 2},
        "entry3": {"data": 3}
    }
    
    # Store multiple entries
    for key, data in test_entries.items():
        await memory_manager.store(key, data)
    
    # List entries
    entries = await memory_manager.list_entries()
    assert len(entries) == len(test_entries)
    for key in test_entries:
        assert key in entries

@pytest.mark.asyncio
async def test_clear(memory_manager: MemoryManager):
    """Test clearing all memory entries."""
    # Store some entries
    await memory_manager.store("key1", "value1")
    await memory_manager.store("key2", "value2")
    
    # Clear all entries
    success = await memory_manager.clear()
    assert success is True
    
    # Verify everything is cleared
    entries = await memory_manager.list_entries()
    assert len(entries) == 0
    assert len(memory_manager.cache) == 0

@pytest.mark.asyncio
async def test_manage_memory_interface():
    """Test the high-level manage_memory interface."""
    test_key = "interface_test"
    test_data = {"interface": "testing"}
    
    # Test store
    store_result = await manage_memory("store", test_key, test_data)
    assert store_result["success"] is True
    
    # Test retrieve
    retrieve_result = await manage_memory("retrieve", test_key)
    assert retrieve_result["success"] is True
    assert retrieve_result["data"] == test_data
    
    # Test list
    list_result = await manage_memory("list")
    assert list_result["success"] is True
    assert test_key in list_result["entries"]
    
    # Test delete
    delete_result = await manage_memory("delete", test_key)
    assert delete_result["success"] is True
    
    # Test clear
    clear_result = await manage_memory("clear")
    assert clear_result["success"] is True

@pytest.mark.asyncio
async def test_error_handling(memory_manager: MemoryManager):
    """Test error handling scenarios."""
    # Test invalid key type
    with pytest.raises(ValueError, match="Key cannot be None or empty"):
        await memory_manager.store(None, "data")
    
    with pytest.raises(ValueError, match="Key cannot be None or empty"):
        await memory_manager.store("", "data")
    
    # Test retrieving non-existent key
    result = await memory_manager.retrieve("non_existent")
    assert result is None
    
    # Test deleting non-existent key
    success = await memory_manager.delete("non_existent")
    assert success is True  # Should succeed silently
    
    # Test invalid manage_memory action
    result = await manage_memory("invalid_action")
    assert result["success"] is False
    assert "error" in result

@pytest.mark.asyncio
async def test_concurrent_access(memory_manager: MemoryManager):
    """Test concurrent access to memory manager."""
    test_key = "concurrent_test"
    test_data = {"concurrent": "data"}
    
    # Simulate concurrent operations
    async def concurrent_ops():
        await memory_manager.store(test_key, test_data)
        await memory_manager.retrieve(test_key)
        await memory_manager.delete(test_key)
    
    # Run multiple concurrent operations
    await asyncio.gather(
        concurrent_ops(),
        concurrent_ops(),
        concurrent_ops()
    )
    
    # Verify final state
    result = await memory_manager.retrieve(test_key)
    assert result is None  # Should be deleted

@pytest.mark.asyncio
async def test_persistence(memory_manager: MemoryManager):
    """Test data persistence across manager instances."""
    test_key = "persistence_test"
    test_data = {"persistent": "data"}
    
    # Store data with first instance
    await memory_manager.store(test_key, test_data)
    
    # Create new instance with same storage directory
    new_manager = MemoryManager(storage_dir=memory_manager.storage_dir)
    
    # Verify data persists
    retrieved_data = await new_manager.retrieve(test_key)
    assert retrieved_data == test_data 
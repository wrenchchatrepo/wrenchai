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
    """
    Asynchronous pytest fixture that yields a MemoryManager instance using a temporary storage directory.
    
    The temporary directory is created for each test and cleaned up after use, ensuring test isolation and no persistent side effects.
    """
    # Create temporary directory for test storage
    temp_dir = tempfile.mkdtemp()
    manager = MemoryManager(storage_dir=temp_dir)
    
    yield manager
    
    # Cleanup after tests
    shutil.rmtree(temp_dir)

@pytest.mark.asyncio
async def test_store_and_retrieve(memory_manager: MemoryManager):
    """
    Tests that a memory entry can be stored and retrieved correctly.
    
    Verifies that data stored with a key can be retrieved accurately and that the entry is present in the cache.
    """
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
    """
    Tests that a memory entry can be deleted and is no longer retrievable or present in the cache.
    
    Stores a memory entry, deletes it, and verifies that deletion is successful, the entry cannot be retrieved, and it is removed from the cache.
    """
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
    """
    Tests that multiple stored entries are correctly listed by the MemoryManager.
    
    Stores several entries and verifies that all their keys appear in the list of entries returned by the manager.
    """
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
    """
    Tests that all memory entries are removed when the clear method is called.
    
    Stores multiple entries, clears them, and verifies both storage and cache are empty.
    """
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
    """
    Tests the manage_memory interface for storing, retrieving, listing, deleting, and clearing entries.
    
    Verifies that each action returns a success flag and that data is correctly stored, retrieved, listed, deleted, and cleared using the high-level interface.
    """
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
    """
    Tests error handling for invalid keys, non-existent entries, and invalid actions in the MemoryManager and manage_memory interface.
    
    Verifies that storing with invalid keys raises ValueError, retrieving and deleting non-existent keys behave as expected, and invalid actions return appropriate error responses.
    """
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
    """
    Tests concurrent store, retrieve, and delete operations on the same key to ensure the
    MemoryManager handles simultaneous access correctly and the entry is deleted as expected.
    """
    test_key = "concurrent_test"
    test_data = {"concurrent": "data"}
    
    # Simulate concurrent operations
    async def concurrent_ops():
        """
        Performs a sequence of store, retrieve, and delete operations on a memory entry asynchronously.
        """
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
    """
    Tests that data stored by one MemoryManager instance can be retrieved by a new instance using the same storage directory, verifying persistence across instances.
    """
    test_key = "persistence_test"
    test_data = {"persistent": "data"}
    
    # Store data with first instance
    await memory_manager.store(test_key, test_data)
    
    # Create new instance with same storage directory
    new_manager = MemoryManager(storage_dir=memory_manager.storage_dir)
    
    # Verify data persists
    retrieved_data = await new_manager.retrieve(test_key)
    assert retrieved_data == test_data 
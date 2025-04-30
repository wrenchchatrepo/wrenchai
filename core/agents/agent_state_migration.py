"""Migration utility for converting from the old agent state system to the enhanced version.

This module provides utility functions to migrate state data from the original
agent_state.py implementation to the new async_agent_state_manager in agent_state_enhanced.py.
"""

import logging
import asyncio
import os
import json
import shutil
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from .agent_state import agent_state_manager, AgentState, AgentStateEntry
from .agent_state_enhanced import async_agent_state_manager, WorkflowState

logger = logging.getLogger(__name__)


async def migrate_agent_state(agent_id: str) -> Tuple[bool, Optional[str]]:
    """Migrate a single agent's state from the old system to the new one.
    
    Args:
        agent_id: ID of the agent to migrate
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Get the agent state from the old manager
        old_state = agent_state_manager.get_agent_state(agent_id)
        
        # Create new state in the async manager
        async with async_agent_state_manager._lock:
            # Migrate entries
            for key, entry in old_state.entries.items():
                await async_agent_state_manager.set_state_entry(
                    agent_id=agent_id,
                    key=key,
                    value=entry.value,
                    scope=entry.scope,
                    visibility=entry.visibility,
                    ttl=entry.ttl,
                    tags=entry.tags
                )
            
            # Migrate operation history
            new_state = await async_agent_state_manager.get_agent_state(agent_id)
            for operation in old_state.operation_history:
                new_state.add_operation(operation, {})
            
            # Set agent name
            new_state.agent_name = old_state.agent_name
            
            # Save the migrated state
            await async_agent_state_manager._save_state(agent_id)
            
        return True, None
    except Exception as e:
        error_msg = f"Failed to migrate agent state for {agent_id}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def migrate_shared_state() -> Tuple[bool, Optional[str]]:
    """Migrate shared state from the old system to the new one.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        async with async_agent_state_manager._lock:
            # Migrate shared state entries
            for key, entry in agent_state_manager.shared_state.items():
                async_agent_state_manager.shared_state[key] = entry
        
        return True, None
    except Exception as e:
        error_msg = f"Failed to migrate shared state: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def migrate_global_state() -> Tuple[bool, Optional[str]]:
    """Migrate global state from the old system to the new one.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        async with async_agent_state_manager._lock:
            # Migrate global state entries
            for key, entry in agent_state_manager.global_state.items():
                async_agent_state_manager.global_state[key] = entry
        
        return True, None
    except Exception as e:
        error_msg = f"Failed to migrate global state: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def migrate_persistence_directory() -> Tuple[bool, Optional[str]]:
    """Migrate the persistence directory structure.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Check if old persistence directory exists
        old_dir = agent_state_manager.persistence_dir
        new_dir = async_agent_state_manager.persistence_dir
        
        if not old_dir or not os.path.exists(old_dir):
            return True, None  # Nothing to migrate
        
        # Create new directory structure if it doesn't exist
        os.makedirs(new_dir, exist_ok=True)
        os.makedirs(os.path.join(new_dir, "workflows"), exist_ok=True)
        os.makedirs(os.path.join(new_dir, "snapshots"), exist_ok=True)
        os.makedirs(os.path.join(new_dir, "transactions"), exist_ok=True)
        
        # Back up the old directory
        backup_dir = f"{old_dir}_backup_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        shutil.copytree(old_dir, backup_dir)
        
        # Copy state files to the new directory
        for filename in os.listdir(old_dir):
            if filename.endswith('.json'):
                old_path = os.path.join(old_dir, filename)
                new_path = os.path.join(new_dir, filename)
                shutil.copy2(old_path, new_path)
        
        return True, None
    except Exception as e:
        error_msg = f"Failed to migrate persistence directory: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


async def migrate_all_state() -> Tuple[bool, List[str]]:
    """Migrate all state from the old system to the new one.
    
    Returns:
        Tuple of (success, list_of_errors)
    """
    errors = []
    
    # Migrate all agent states
    for agent_id in list(agent_state_manager.agent_states.keys()):
        success, error = await migrate_agent_state(agent_id)
        if not success:
            errors.append(error)
    
    # Migrate shared and global state
    shared_success, shared_error = await migrate_shared_state()
    if not shared_success:
        errors.append(shared_error)
    
    global_success, global_error = await migrate_global_state()
    if not global_success:
        errors.append(global_error)
    
    # Migrate persistence directory
    persist_success, persist_error = await migrate_persistence_directory()
    if not persist_success:
        errors.append(persist_error)
    
    # Return success flag (True if no errors) and list of errors
    return len(errors) == 0, errors


def migrate_state_sync() -> Tuple[bool, List[str]]:
    """Synchronous wrapper for migrate_all_state.
    
    Returns:
        Tuple of (success, list_of_errors)
    """
    loop = asyncio.get_event_loop()
    try:
        return loop.run_until_complete(migrate_all_state())
    except RuntimeError:
        # Create a new event loop if one isn't available
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(migrate_all_state())
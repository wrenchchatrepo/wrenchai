"""Utility functions for working with the state manager.

This module provides helper functions to integrate the state manager with existing components
and workflows in the WrenchAI system, including recovery capabilities.
"""

import logging
import asyncio
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime

from core.state_manager import (
    StateManager,
    StateVariable,
    StateGroup,
    StateScope,
    StatePermission,
    state_manager
)

# Import recovery system
from core.recovery_system import (
    init_recovery_manager, 
    RecoveryManager,
    with_recovery,
    CheckpointType,
    recovery_manager as global_recovery_manager
)

# Import agent state for compatibility functions
from core.agents.agent_state import AgentStateManager, agent_state_manager

logger = logging.getLogger(__name__)

def initialize_workflow_state(workflow_id: str, user_query: str = "", additional_context: Dict[str, Any] = None) -> str:
    """Initialize state variables for a new workflow execution.
    
    Args:
        workflow_id: Unique identifier for the workflow
        user_query: The initial user query
        additional_context: Any additional context information
        
    Returns:
        The workflow ID
    """
    # Create a workflow state group
    group_name = f"workflow_{workflow_id}"
    try:
        workflow_group = state_manager.create_group(
            name=group_name,
            description=f"State for workflow {workflow_id}"
        )
    except ValueError:
        # Group already exists, retrieve it
        workflow_group = state_manager.get_group(group_name)
    
    # Create the core workflow variables
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_id",
        value=workflow_id,
        description="Workflow identifier",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "metadata"]
    )
    
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_start_time",
        value=datetime.utcnow().isoformat(),
        description="Workflow start time",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "timing"]
    )
    
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_status",
        value="initialized",
        description="Current workflow status",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "status"]
    )
    
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_current_step",
        value="initialization",
        description="Current workflow step",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "progress"]
    )
    
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_user_query",
        value=user_query,
        description="User query for this workflow",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "input"]
    )
    
    state_manager.create_variable(
        name=f"workflow_{workflow_id}_context",
        value=additional_context or {},
        description="Contextual information for the workflow",
        scope=StateScope.WORKFLOW,
        tags=["workflow", "context"]
    )
    
    # Associate all variables with the workflow group
    for var_name in [
        f"workflow_{workflow_id}_id",
        f"workflow_{workflow_id}_start_time",
        f"workflow_{workflow_id}_status",
        f"workflow_{workflow_id}_current_step",
        f"workflow_{workflow_id}_user_query",
        f"workflow_{workflow_id}_context",
    ]:
        state_manager.add_variable_to_group(var_name, group_name)
    
    return workflow_id

def update_workflow_step(workflow_id: str, step: str, status: str = None) -> bool:
    """Update the current step of a workflow.
    
    Args:
        workflow_id: The workflow identifier
        step: The new step name
        status: Optional updated status
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Update the step
        state_manager.set_variable_value(
            f"workflow_{workflow_id}_current_step",
            step
        )
        
        # Update status if provided
        if status:
            state_manager.set_variable_value(
                f"workflow_{workflow_id}_status",
                status
            )
        
        return True
    except Exception as e:
        logger.error(f"Error updating workflow step: {e}")
        return False

def get_workflow_context(workflow_id: str) -> Dict[str, Any]:
    """Get the full context for a workflow.
    
    Args:
        workflow_id: The workflow identifier
        
    Returns:
        The workflow context dictionary
    """
    try:
        return state_manager.get_variable_value(
            f"workflow_{workflow_id}_context",
            default={}
        )
    except Exception as e:
        logger.error(f"Error getting workflow context: {e}")
        return {}

def update_workflow_context(workflow_id: str, updates: Dict[str, Any]) -> bool:
    """Update the context for a workflow.
    
    Args:
        workflow_id: The workflow identifier
        updates: The context updates to apply
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get current context
        context = get_workflow_context(workflow_id)
        
        # Apply updates
        context.update(updates)
        
        # Save updated context
        state_manager.set_variable_value(
            f"workflow_{workflow_id}_context",
            context
        )
        
        return True
    except Exception as e:
        logger.error(f"Error updating workflow context: {e}")
        return False

def finalize_workflow(workflow_id: str, status: str = "completed") -> Dict[str, Any]:
    """Finalize a workflow execution and gather summary information.
    
    Args:
        workflow_id: The workflow identifier
        status: Final status of the workflow
        
    Returns:
        Summary dictionary of workflow execution
    """
    try:
        # Update status and end time
        state_manager.set_variable_value(
            f"workflow_{workflow_id}_status",
            status
        )
        
        state_manager.create_variable(
            name=f"workflow_{workflow_id}_end_time",
            value=datetime.utcnow().isoformat(),
            description="Workflow end time",
            scope=StateScope.WORKFLOW,
            tags=["workflow", "timing"]
        )
        
        # Add end time to the workflow group
        group_name = f"workflow_{workflow_id}"
        try:
            state_manager.add_variable_to_group(
                f"workflow_{workflow_id}_end_time",
                group_name
            )
        except:
            pass
        
        # Gather all related variables
        workflow_vars = {}
        for var in state_manager.get_variables_by_tag("workflow"):
            if var.name.startswith(f"workflow_{workflow_id}"):
                workflow_vars[var.name.replace(f"workflow_{workflow_id}_", "")] = var.value
        
        return workflow_vars
    except Exception as e:
        logger.error(f"Error finalizing workflow: {e}")
        return {"error": str(e), "status": "error"}

def bridge_agent_state_to_new_state(agent_id: str, keys: Optional[List[str]] = None) -> Dict[str, Any]:
    """Import agent state from the old state management system.
    
    Args:
        agent_id: The agent identifier
        keys: Optional specific keys to import (None for all)
        
    Returns:
        Dictionary of imported states
    """
    try:
        # Get agent state from the old system
        if keys:
            entries = {}
            for key in keys:
                entries[key] = agent_state_manager.get_state_entry(agent_id, key)
        else:
            entries = agent_state_manager.get_all_entries(agent_id)
        
        # Import to the new system
        imported = {}
        for key, value in entries.items():
            if value is not None:  # Only import non-None values
                var_name = f"agent_{agent_id}_{key}"
                try:
                    # Check if variable exists
                    state_manager.get_variable(var_name)
                    # Update existing variable
                    state_manager.set_variable_value(var_name, value)
                except:
                    # Create new variable
                    state_manager.create_variable(
                        name=var_name,
                        value=value,
                        description=f"Agent state for {agent_id}",
                        scope=StateScope.WORKFLOW,
                        permission=StatePermission.SHARED,
                        owner=agent_id,
                        tags=["agent", agent_id]
                    )
                imported[key] = value
        
        return imported
    except Exception as e:
        logger.error(f"Error bridging agent state: {e}")
        return {}

def setup_state_synchronization():
    """Set up bidirectional synchronization between old and new state systems.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Sync from new state to old state
        def sync_to_agent_state(name, old_value, new_value, requestor):
            """Sync state changes to the agent state manager."""
            if name.startswith("agent_"):
                # Extract agent ID and key from variable name
                parts = name.split("_", 2)
                if len(parts) >= 3:
                    agent_id = parts[1]
                    key = parts[2]
                    # Store in agent state
                    agent_state_manager.set_state_entry(
                        agent_id=agent_id,
                        key=key,
                        value=new_value,
                        scope="agent",
                        visibility="shared"
                    )
        
        # Register the sync hook
        state_manager.add_hook("post_change", sync_to_agent_state)
        
        logger.info("State synchronization set up successfully")
        return True
    except Exception as e:
        logger.error(f"Error setting up state synchronization: {e}")
        return False

def export_workflow_state_snapshot(workflow_id: str) -> Dict[str, Any]:
    """Export a complete snapshot of a workflow's state.
    
    Args:
        workflow_id: The workflow identifier
        
    Returns:
        Dictionary containing all workflow state
    """
    try:
        # Get all variables for this workflow
        workflow_state = {}
        for var in state_manager.get_variables_by_tag("workflow"):
            if var.name.startswith(f"workflow_{workflow_id}"):
                # Strip the workflow prefix for cleaner export
                key = var.name.replace(f"workflow_{workflow_id}_", "")
                workflow_state[key] = var.value
        
        # Get all agent state related to this workflow
        agent_state = {}
        context = get_workflow_context(workflow_id)
        if "agents" in context:
            for agent_id in context.get("agents", []):
                agent_vars = {}
                for var in state_manager.get_variables_by_tag(agent_id):
                    # Extract just the key part
                    key = var.name.replace(f"agent_{agent_id}_", "")
                    agent_vars[key] = var.value
                
                if agent_vars:
                    agent_state[agent_id] = agent_vars
        
        return {
            "workflow": workflow_state,
            "agents": agent_state,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Error exporting workflow state: {e}")
        return {"error": str(e)}

def register_state_validation_hook(validation_function: Callable[[str, Any, str], bool]) -> bool:
    """Register a validation hook for state changes.
    
    Args:
        validation_function: Function that takes (variable_name, new_value, requestor)
                            and returns True if valid, False otherwise
                            
    Returns:
        True if registration was successful
    """
    return state_manager.add_hook("validation", validation_function)


# Recovery system integration functions

async def with_workflow_recovery(workflow_id: str, step_id: str, func, *args, **kwargs):
    """Execute a function with workflow recovery.
    
    Args:
        workflow_id: The workflow identifier
        step_id: The step identifier
        func: The function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function execution
    """
    # Ensure recovery manager is initialized
    rm = init_recovery_manager()
    
    # Update workflow step
    update_workflow_step(workflow_id, step_id, "in_progress")
    
    try:
        # Execute with recovery
        result = await with_recovery(rm, workflow_id, step_id, func, *args, **kwargs)
        
        # Update workflow step on success
        update_workflow_step(workflow_id, step_id, "completed")
        
        return result
    except Exception as e:
        # Update workflow step on failure
        update_workflow_step(workflow_id, step_id, "failed")
        
        # Update context with error information
        update_workflow_context(workflow_id, {
            "errors": get_workflow_context(workflow_id).get("errors", []) + [
                {
                    "step": step_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        })
        
        # Re-raise the exception
        raise


async def create_workflow_checkpoint(workflow_id: str, step_id: str, metadata: Dict[str, Any] = None):
    """Create a checkpoint for a workflow.
    
    Args:
        workflow_id: The workflow identifier
        step_id: The step identifier
        metadata: Additional metadata for the checkpoint
        
    Returns:
        The created checkpoint
    """
    # Ensure recovery manager is initialized
    rm = init_recovery_manager()
    
    # Create checkpoint
    checkpoint = await rm.checkpoint_workflow(
        workflow_id, step_id, metadata=metadata
    )
    
    # Update context with checkpoint information
    update_workflow_context(workflow_id, {
        "checkpoints": get_workflow_context(workflow_id).get("checkpoints", []) + [
            {
                "id": checkpoint.id,
                "step": step_id,
                "timestamp": checkpoint.timestamp.isoformat()
            }
        ]
    })
    
    return checkpoint


async def restore_workflow_checkpoint(workflow_id: str, checkpoint_id: str):
    """Restore a workflow from a checkpoint.
    
    Args:
        workflow_id: The workflow identifier
        checkpoint_id: The checkpoint identifier
        
    Returns:
        True if successful, False otherwise
    """
    # Ensure recovery manager is initialized
    rm = init_recovery_manager()
    
    # Restore checkpoint
    success = await rm.restore_to_checkpoint(checkpoint_id)
    
    if success:
        # Update workflow status
        update_workflow_step(
            workflow_id, 
            "restored_from_checkpoint", 
            "recovered"
        )
        
        # Add recovery event to context
        update_workflow_context(workflow_id, {
            "recovery_events": get_workflow_context(workflow_id).get("recovery_events", []) + [
                {
                    "type": "checkpoint_restore",
                    "checkpoint_id": checkpoint_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ]
        })
    
    return success


async def execute_workflow_transaction(workflow_id: str, step_id: str, func, *args, **kwargs):
    """Execute a function as a workflow transaction.
    
    Args:
        workflow_id: The workflow identifier
        step_id: The step identifier
        func: The function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        Result of the function execution
    """
    # Ensure recovery manager is initialized
    rm = init_recovery_manager()
    
    # Execute as transaction
    async with rm.transaction_manager.transaction(workflow_id, step_id):
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)


def get_workflow_recovery_history(workflow_id: str) -> List[Dict[str, Any]]:
    """Get the recovery history for a workflow.
    
    Args:
        workflow_id: The workflow identifier
        
    Returns:
        List of recovery events
    """
    # Ensure recovery manager is initialized
    rm = init_recovery_manager()
    
    # Get recovery history
    return rm.get_recovery_history(workflow_id)
# Agent State Management Enhancement Migration Guide

This guide provides instructions for migrating from the original `agent_state.py` implementation to the enhanced async-based state management system in `agent_state_enhanced.py`.

## Overview of Enhancements

The enhanced agent state management system provides several key improvements:

1. **Async Support**: Full async/await support for state operations
2. **Workflow State**: Dedicated workflow-level state management
3. **Context Snapshots**: Point-in-time snapshots for state recovery
4. **Transactions**: Support for batched state changes with rollback capability
5. **Improved Serialization**: Better handling of complex data types
6. **Tagging System**: Tag-based organization of state entries
7. **Operation Metadata**: Rich metadata for operation history

## Migration Path

### Option 1: Direct Adoption (Recommended)

For new agent implementations, directly use the `async_agent_state_manager` and the `AgentStateAdapter` with `use_enhanced=True`:

```python
from core.agents import async_agent_state_manager
from core.agents.agent_adapters import AgentStateAdapter

# In your agent class:
def __init__(self, agent_id, ...):
    self.state_adapter = AgentStateAdapter(agent_id, use_enhanced=True)

async def some_method(self):
    # Get state
    value = await self.state_adapter.get_state("some-key")
    
    # Set state
    await self.state_adapter.set_state("some-key", "new-value")
    
    # Advanced features
    workflow_state = await self.state_adapter.get_workflow_context("workflow-id")
    snapshot_id = await self.state_adapter.create_snapshot()
    # ...
```

### Option 2: Gradual Migration

For existing agents using the original state manager, you can adopt a gradual approach:

1. Initialize `AgentStateAdapter` with `use_enhanced=False`
2. Run the migration utility to copy existing state
3. Switch to `use_enhanced=True` when ready

```python
from core.agents import migrate_state_sync, agent_state_manager

# Run the migration once during system initialization
success, errors = migrate_state_sync()
if not success:
    print(f"Migration errors: {errors}")

# In your agent class:
def __init__(self, agent_id, ...):
    # Start with the old system
    self.state_adapter = AgentStateAdapter(agent_id, use_enhanced=False)
    
    # Later, switch to the enhanced system
    self.state_adapter = AgentStateAdapter(agent_id, use_enhanced=True)
```

### Option 3: Parallel Operation

For a more conservative approach, you can run both systems in parallel during a transition period:

```python
from core.agents import agent_state_manager, async_agent_state_manager

# In your agent class:
def __init__(self, agent_id, ...):
    self.agent_id = agent_id
    
async def some_method(self):
    # Write to both systems
    agent_state_manager.set_state_entry(self.agent_id, "key", "value")
    await async_agent_state_manager.set_state_entry(self.agent_id, "key", "value")
    
    # Read from the enhanced system if available, fall back to original
    try:
        value = await async_agent_state_manager.get_state_entry(self.agent_id, "key")
    except:
        value = agent_state_manager.get_state_entry(self.agent_id, "key")
```

## Advanced Features Usage

### Workflow State Management

```python
# Create a workflow
workflow_id = "my-workflow-1"
workflow = await async_agent_state_manager.create_workflow(
    workflow_id=workflow_id,
    workflow_name="My Workflow"
)

# Update workflow state
await async_agent_state_manager.update_workflow_state(
    workflow_id=workflow_id,
    status="running",
    current_step="step-1",
    context_update={"param1": "value1"}
)

# Get workflow-scoped state
await async_agent_state_manager.set_state_entry(
    agent_id="my-agent",
    key="workflow-data",
    value={"result": "success"},
    scope="workflow",
    workflow_id=workflow_id
)

# Get workflow state
workflow = await async_agent_state_manager.get_workflow_state(workflow_id)
print(f"Status: {workflow.status}")
print(f"Current step: {workflow.current_step}")
print(f"Context: {workflow.context}")
```

### Transactions

```python
# Using context manager (auto-commits at the end)
async with async_agent_state_manager.transaction(agent_id) as transaction:
    await transaction.set("key1", "value1")
    await transaction.set("key2", "value2")
    # Changes are visible immediately within the transaction

# Manual transaction management
transaction = await async_agent_state_manager.transaction(agent_id).__aenter__()
try:
    await transaction.set("key3", "value3")
    await transaction.set("key4", "value4")
    
    # Decide whether to commit or rollback
    if some_condition:
        await transaction.commit()
    else:
        await transaction.rollback()
except Exception:
    # Always rollback on exception
    await transaction.rollback()
    raise
```

### Context Snapshots

```python
# Create a snapshot
snapshot_id = await state_adapter.create_snapshot(scope="agent")

# Make changes
await state_adapter.set_state("key1", "changed-value")
await state_adapter.delete_state("key2")

# Restore from snapshot
success = await state_adapter.restore_snapshot(snapshot_id)
```

## Best Practices

1. **Always Use Async**: Consistently use `await` with all state operations
2. **Use Transactions**: Group related state changes in transactions
3. **Create Snapshots**: Take snapshots before making significant changes
4. **Tag Your Entries**: Use tags to organize related state entries
5. **Add Metadata**: Include rich metadata with operation registration
6. **Workflow Scope**: Use workflow-scoped entries for workflow-specific data
7. **Error Handling**: Always handle potential exceptions from state operations

## Testing Your Migration

A comprehensive test suite is provided in `tests/test_agent_state_enhanced.py`. You can run these tests to verify the functionality of the enhanced state system:

```bash
python -m unittest tests/test_agent_state_enhanced.py
```
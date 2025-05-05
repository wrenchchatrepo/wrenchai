# WrenchAI Recovery System

The Recovery System provides a comprehensive framework for handling errors and implementing resilient workflows in WrenchAI.

## Overview

The recovery system is designed to handle various types of errors that can occur during workflow execution, providing different recovery strategies based on the error type and context. It offers features like:

- **Error categorization**: Automatic classification of errors into categories (transient, logical, resource, etc.)
- **Configurable recovery strategies**: Multiple recovery approaches including retry, rollback, and alternate paths
- **Checkpointing**: State preservation for reliable rollback
- **Transaction-like semantics**: For atomic operations that either fully succeed or fully roll back
- **Recovery callbacks**: Hooks for custom actions during recovery 
- **Monitoring and history**: Tracking of recovery events for analysis

## Key Components

### RecoveryManager

The central component that orchestrates error handling and recovery:

```python
from core.recovery_system import init_recovery_manager
from core.state_manager import state_manager

# Initialize the global recovery manager
recovery_manager = init_recovery_manager(state_manager)

# Use in workflows
async with recovery_manager.recovery_context(workflow_id, step_id):
    # Code that might fail...
```

### Recovery Strategies

Various strategies for recovering from errors:

1. **RetryStrategy**: Automatically retries failed operations with configurable backoff
2. **RollbackStrategy**: Restores system state to a previous checkpoint 
3. **AlternatePathStrategy**: Executes alternative code paths when primary path fails

### CheckpointManager

Handles creating and restoring checkpoints of workflow state:

```python
# Create a manual checkpoint
checkpoint = await recovery_manager.checkpoint_workflow(workflow_id, step_id)

# Restore from a checkpoint
success = await recovery_manager.restore_to_checkpoint(checkpoint.id)
```

### TransactionManager

Provides transaction-like semantics for workflow steps:

```python
# Execute a step as a transaction (automatically rolls back on error)
async with recovery_manager.step_transaction(workflow_id, step_id):
    # Operations that should be atomic...
```

### Recovery Callbacks

Customize recovery behavior with callbacks:

```python
class MyCallback(RecoveryCallback):
    async def pre_recovery(self, context):
        # Called before recovery
        
    async def post_recovery(self, context, action, success):
        # Called after recovery attempt
        
    async def on_abort(self, context):
        # Called when workflow is aborted

recovery_manager.register_callback(MyCallback())
```

## Error Categories

Errors are automatically categorized into:

- **TRANSIENT**: Temporary errors like network timeouts
- **STATE_INVALID**: State validation errors
- **RESOURCE**: Resource-related errors (memory, disk)
- **DEPENDENCY**: External dependency errors
- **LOGICAL**: Logical errors in workflow
- **SECURITY**: Security-related errors
- **PERMISSION**: Permission-related errors
- **TIMEOUT**: Timeout errors
- **UNKNOWN**: Unclassified errors

## Integration with Workflows

The recovery system integrates with the workflow engine:

```python
from core.recovery_system import with_recovery

# Run a function with recovery
result = await with_recovery(
    recovery_manager,
    workflow_id,
    step_id,
    my_function,
    *args,
    **kwargs
)
```

For graph-based workflows, the system integrates directly with the `GraphWorkflow` class to provide recovery capabilities for each node in the workflow graph.

## Example Use Cases

1. **Handling network errors**: RetryStrategy with backoff for API calls
2. **Recovering from state corruption**: RollbackStrategy to restore from a checkpoint
3. **Graceful degradation**: AlternatePathStrategy to provide fallback functionality
4. **Monitoring failure patterns**: Recovery callbacks to log errors and track trends
5. **Transactional workflows**: Step transactions to maintain data consistency

## Best Practices

1. **Categorize errors appropriately**: Register custom matchers for domain-specific errors
2. **Use checkpoints strategically**: Create checkpoints at major state transitions
3. **Implement alternate paths**: Provide fallback functionality for critical steps
4. **Monitor recovery patterns**: Analyze recovery history to identify recurring issues
5. **Use transactions for atomic operations**: Wrap related state changes in transactions

## Configuration

The recovery system can be configured through:

- **RetryPolicy**: Configure retry behavior (attempts, delays, backoff)
- **CheckpointManager**: Configure automatic checkpoint intervals
- **AlternatePathStrategy**: Register alternate paths for specific steps 
- **ErrorCategorizer**: Register custom patterns for error classification

For more information on using the recovery system, see the examples in the `examples/` directory.
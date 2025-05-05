# WrenchAI Recovery System Implementation

## Overview

The Recovery System implementation provides a comprehensive framework for error handling and recovery in workflows. It offers:

- **Error recovery strategies**: Including retry, rollback, and alternate execution paths
- **State checkpointing**: For preserving and restoring workflow state
- **Transaction-like semantics**: For atomic operations
- **Error categorization**: For applying appropriate recovery strategies
- **Flexible recovery callbacks**: For customizing recovery behavior

## System Architecture

The recovery system implementation includes:

1. **RecoveryManager**: Central component managing recovery strategies and orchestrating recovery processes
2. **CheckpointManager**: Handles creating, storing, and restoring state checkpoints
3. **TransactionManager**: Provides transaction-like semantics for atomic operations
4. **Error Categorizer**: Identifies error types to determine appropriate recovery strategies
5. **Recovery Strategies**: Implementations of different approaches to error recovery
6. **Recovery Context**: Contextual information for recovery operations
7. **Callbacks**: Hooks for custom recovery actions

## Integration Paths

The recovery system is integrated with:

1. **GraphWorkflow**: For graph-based workflow execution with automatic step recovery
2. **StateManager**: For state operations with recovery capabilities
3. **State Utils**: With helper functions for workflow state management with recovery

## Key Features

### Checkpointing

```python
# Create a checkpoint
checkpoint = await recovery_manager.checkpoint_workflow(workflow_id, step_id)

# Restore from a checkpoint
success = await recovery_manager.restore_to_checkpoint(checkpoint_id)
```

### Retry Policies

```python
# Configure a retry policy
policy = RetryPolicy(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    jitter=True
)

# Create a retry strategy
retry_strategy = RetryStrategy(policy)
```

### Transaction-like Execution

```python
# Execute a step as a transaction
async with recovery_manager.step_transaction(workflow_id, step_id):
    # Operations that should succeed or roll back as a unit
    result = await risky_operation()
```

### Alternate Execution Paths

```python
# Register an alternate path
alternate_path_strategy = AlternatePathStrategy()
alternate_path_strategy.register_alternate_path(
    "critical_step", 
    alternate_function
)

# Recovery manager will use it when needed
recovery_manager.register_strategy(alternate_path_strategy)
```

### Integration with Workflows

```python
# Run a function with recovery
result = await with_recovery(
    recovery_manager,
    workflow_id,
    step_id,
    function_to_execute,
    *args, **kwargs
)

# Or using the workflow helper
result = await with_workflow_recovery(
    workflow_id, 
    step_id,
    function_to_execute,
    *args, **kwargs
)
```

## Examples

The implementation includes examples:

1. `examples/recovery_example.py`: Basic usage of the recovery system
2. `examples/graph_recovery_example.py`: Integration with graph workflows

## Testing

The implementation includes comprehensive tests in:

- `tests/test_recovery_system.py`

## Documentation

Detailed documentation is available in:

- `core/docs/recovery_system.md`

## Usage Guidelines

1. **Recovery Strategies**: Configure appropriate strategies for different error types
2. **Checkpointing**: Create checkpoints at critical points in workflow execution
3. **Error Categorization**: Register custom error categorization patterns for domain-specific errors
4. **Recovery Monitoring**: Use the recovery history for monitoring and debugging
5. **Transactions**: Use transactions for operations that need atomic semantics

## Integration with Existing Code

To use recovery in existing code:

1. Initialize the recovery manager
2. Use the `with_recovery` function or context managers
3. Register domain-specific error handling strategies
4. Create checkpoints at appropriate points
5. Configure retry policies for specific operations
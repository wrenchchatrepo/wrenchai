"""Tests for the recovery system."""

import pytest
import asyncio
import os
import json
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from core.recovery_system import (
    RecoveryManager, CheckpointManager, RecoveryAction, ErrorCategory,
    RecoveryContext, Checkpoint, CheckpointType, RetryPolicy, 
    RetryStrategy, RollbackStrategy, ErrorCategorizer, TransactionManager,
    RecoveryCallback, with_recovery
)
from core.state_manager import StateManager, StateScope, StatePermission, StateVariable


@pytest.fixture
def state_manager():
    """Create a state manager for testing."""
    return StateManager()


@pytest.fixture
def recovery_manager(state_manager, tmp_path):
    """Create a recovery manager for testing."""
    persistence_dir = os.path.join(tmp_path, "recovery")
    return RecoveryManager(state_manager, persistence_dir)


@pytest.fixture
def checkpoint_manager(state_manager, tmp_path):
    """Create a checkpoint manager for testing."""
    persistence_dir = os.path.join(tmp_path, "checkpoints")
    return CheckpointManager(state_manager, persistence_dir)


@pytest.fixture
def recovery_context():
    """Create a recovery context for testing."""
    return RecoveryContext(
        error=ValueError("Test error"),
        error_category=ErrorCategory.LOGICAL,
        step_id="test_step",
        workflow_id="test_workflow"
    )


@pytest.fixture
def transaction_manager(checkpoint_manager):
    """Create a transaction manager for testing."""
    return TransactionManager(checkpoint_manager)


@pytest.mark.asyncio
async def test_error_categorizer():
    """Test error categorization."""
    categorizer = ErrorCategorizer()
    
    # Test various error types
    assert categorizer.categorize(ValueError("Invalid value")) == ErrorCategory.LOGICAL
    assert categorizer.categorize(TimeoutError("Request timed out")) == ErrorCategory.TIMEOUT
    assert categorizer.categorize(ConnectionError("Connection refused")) == ErrorCategory.TRANSIENT
    assert categorizer.categorize(MemoryError("Out of memory")) == ErrorCategory.RESOURCE
    assert categorizer.categorize(PermissionError("Permission denied")) == ErrorCategory.SECURITY
    assert categorizer.categorize(Exception("Unknown error")) == ErrorCategory.UNKNOWN
    
    # Test custom matcher registration
    categorizer.register_matcher(
        ErrorCategory.CUSTOM,
        patterns=["custom error"],
        exception_types=[KeyError]
    )
    assert categorizer.categorize(KeyError("Key not found")) == ErrorCategory.CUSTOM
    assert categorizer.categorize(Exception("A custom error occurred")) == ErrorCategory.CUSTOM


@pytest.mark.asyncio
async def test_checkpoint_creation_and_restoration(checkpoint_manager, state_manager):
    """Test checkpoint creation and restoration."""
    # Create some test state
    state_manager.create_variable("test_var", "test_value", scope=StateScope.WORKFLOW)
    
    # Create a checkpoint
    checkpoint = await checkpoint_manager.create_checkpoint(
        workflow_id="test_workflow",
        step_id="test_step",
        checkpoint_type=CheckpointType.MANUAL
    )
    
    # Modify state
    state_manager.set_variable_value("test_var", "modified_value")
    assert state_manager.get_variable_value("test_var") == "modified_value"
    
    # Restore the checkpoint
    success = await checkpoint_manager.restore_checkpoint(checkpoint.id)
    assert success
    
    # Verify state was restored
    assert state_manager.get_variable_value("test_var") == "test_value"


@pytest.mark.asyncio
async def test_recovery_strategy_selection(recovery_manager):
    """Test recovery strategy selection based on error category."""
    # Test retry strategy for transient error
    action = await recovery_manager.handle_error(
        TimeoutError("Connection timed out"),
        workflow_id="test_workflow",
        step_id="test_step"
    )
    assert action == RecoveryAction.RETRY
    
    # Test rollback strategy for logical error
    action = await recovery_manager.handle_error(
        ValueError("Invalid state"),
        workflow_id="test_workflow",
        step_id="test_step"
    )
    assert action == RecoveryAction.ROLLBACK


@pytest.mark.asyncio
async def test_retry_policy():
    """Test retry policy behavior."""
    policy = RetryPolicy(
        max_retries=3,
        initial_delay=0.1,
        max_delay=1.0,
        backoff_factor=2.0,
        jitter=False
    )
    
    # Test should_retry
    context = RecoveryContext(
        error=TimeoutError("Timed out"),
        error_category=ErrorCategory.TIMEOUT,
        step_id="test_step",
        workflow_id="test_workflow",
        retry_count=0
    )
    assert policy.should_retry(context)
    
    # Test retry count limit
    context.retry_count = 3
    assert not policy.should_retry(context)
    
    # Test error category filtering
    context.retry_count = 0
    context.error_category = ErrorCategory.LOGICAL
    assert not policy.should_retry(context)
    
    # Test delay calculation
    assert policy.get_delay(0) == 0.1
    assert policy.get_delay(1) == 0.2
    assert policy.get_delay(2) == 0.4
    assert policy.get_delay(3) == 0.8
    assert policy.get_delay(4) == 1.0  # Max delay reached


@pytest.mark.asyncio
async def test_transaction_manager(transaction_manager, state_manager):
    """Test transaction manager behavior."""
    # Set up some state
    state_manager.create_variable("transaction_test", "initial", scope=StateScope.WORKFLOW)
    
    # Test successful transaction
    async with transaction_manager.transaction("test_workflow", "test_step"):
        state_manager.set_variable_value("transaction_test", "modified")
    
    assert state_manager.get_variable_value("transaction_test") == "modified"
    
    # Test failed transaction
    try:
        async with transaction_manager.transaction("test_workflow", "test_step"):
            state_manager.set_variable_value("transaction_test", "will_rollback")
            raise ValueError("Test error")
    except ValueError:
        pass
    
    # State should be rolled back
    assert state_manager.get_variable_value("transaction_test") == "modified"


@pytest.mark.asyncio
async def test_recovery_context_manager(recovery_manager, state_manager):
    """Test recovery context manager."""
    state_manager.create_variable("recovery_test", "initial", scope=StateScope.WORKFLOW)
    
    # Test successful execution
    async with recovery_manager.recovery_context("test_workflow", "success_step"):
        state_manager.set_variable_value("recovery_test", "success")
    
    assert state_manager.get_variable_value("recovery_test") == "success"
    
    # Test retry action (should re-raise for caller to handle)
    with patch.object(recovery_manager, 'handle_error', return_value=RecoveryAction.RETRY):
        with pytest.raises(ValueError):
            async with recovery_manager.recovery_context("test_workflow", "retry_step"):
                raise ValueError("Test error")
    
    # Test abort action (should re-raise)
    with patch.object(recovery_manager, 'handle_error', return_value=RecoveryAction.ABORT):
        with pytest.raises(ValueError):
            async with recovery_manager.recovery_context("test_workflow", "abort_step"):
                raise ValueError("Test error")


@pytest.mark.asyncio
async def test_recovery_callbacks(recovery_manager, recovery_context):
    """Test recovery callbacks."""
    # Create a mock callback
    callback = MagicMock(spec=RecoveryCallback)
    callback.pre_recovery = AsyncMock()
    callback.post_recovery = AsyncMock()
    callback.on_abort = AsyncMock()
    
    # Register the callback
    recovery_manager.register_callback(callback)
    
    # Test callback invocation
    with patch.object(recovery_manager, '_strategies', []):
        action = await recovery_manager.handle_error(
            ValueError("Test error"),
            workflow_id="test_workflow",
            step_id="test_step"
        )
    
    # Verify callbacks were called
    callback.pre_recovery.assert_called_once()
    callback.post_recovery.assert_called_once()
    callback.on_abort.assert_called_once()


@pytest.mark.asyncio
async def test_with_recovery_wrapper(recovery_manager):
    """Test the with_recovery convenience function."""
    # Test successful function execution
    async def success_func():
        return "success"
    
    result = await with_recovery(
        recovery_manager,
        "test_workflow",
        "success_step",
        success_func
    )
    assert result == "success"
    
    # Test function with retries
    retried_func = AsyncMock(side_effect=[ValueError("Retry 1"), ValueError("Retry 2"), "success"])
    
    with patch.object(recovery_manager, 'recovery_context'):
        result = await with_recovery(
            recovery_manager,
            "test_workflow",
            "retry_step",
            retried_func
        )
        assert result == "success"
        assert retried_func.call_count == 3
    
    # Test max retries exceeded
    failing_func = AsyncMock(side_effect=ValueError("Always fails"))
    
    with patch.object(recovery_manager, 'recovery_context'):
        with pytest.raises(ValueError):
            await with_recovery(
                recovery_manager,
                "test_workflow",
                "failing_step",
                failing_func
            )
        assert failing_func.call_count == 4  # Initial + 3 retries


@pytest.mark.asyncio
async def test_global_recovery_manager_initialization(state_manager, tmp_path):
    """Test global recovery manager initialization."""
    from core.recovery_system import init_recovery_manager, recovery_manager as global_rm
    
    # Initialize the global instance
    persistence_dir = os.path.join(tmp_path, "global_recovery")
    rm = init_recovery_manager(state_manager, persistence_dir)
    
    # Verify it's the same instance
    assert rm is global_rm
    assert os.path.exists(persistence_dir)
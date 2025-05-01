"""Recovery system for workflow execution error handling.

This module provides a framework for error recovery in workflows, including 
strategies for recovering from different error types, checkpointing, and 
automatic retry mechanisms.

Key components:
- RecoveryManager: Manages different recovery strategies
- RecoveryStrategy: Base class for implementing different recovery approaches
- CheckpointManager: Handles workflow state checkpointing
- ErrorCategorizer: Categorizes errors for appropriate recovery strategies
- RetryPolicy: Configurable retry logic for failed operations
"""

import logging
import time
import json
import os
import copy
import asyncio
import inspect
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, TypeVar, Generic
from dataclasses import dataclass, field
from contextlib import contextmanager

from .state_manager import StateManager, StateScope, StatePermission, StateVariable, state_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ErrorCategory(str, Enum):
    """Categories of errors that can occur during workflow execution."""
    TRANSIENT = "transient"        # Temporary errors (e.g., network timeout)
    STATE_INVALID = "state_invalid"  # State validation errors
    RESOURCE = "resource"          # Resource-related errors (e.g., out of memory)
    DEPENDENCY = "dependency"      # External dependency errors
    LOGICAL = "logical"            # Logical errors in workflow
    SECURITY = "security"          # Security-related errors
    PERMISSION = "permission"      # Permission-related errors
    TIMEOUT = "timeout"            # Timeout errors
    UNKNOWN = "unknown"            # Unknown errors


class RecoveryAction(str, Enum):
    """Actions that can be taken to recover from an error."""
    RETRY = "retry"                # Retry the failed operation
    SKIP = "skip"                  # Skip the failed step
    ROLLBACK = "rollback"          # Rollback to a previous checkpoint
    ALTERNATE_PATH = "alternate"   # Use an alternate execution path
    NOTIFY = "notify"              # Notify administrator/user
    ABORT = "abort"                # Abort the workflow
    CUSTOM = "custom"              # Custom recovery action


class CheckpointType(str, Enum):
    """Types of checkpoints that can be created."""
    AUTO = "auto"                  # Automatically created checkpoints
    MANUAL = "manual"              # Manually created checkpoints
    TRANSACTIONAL = "transactional"  # Checkpoints at transaction boundaries
    INCREMENTAL = "incremental"    # Incremental checkpoints


@dataclass
class RecoveryContext:
    """Context for recovery operations."""
    error: Exception                   # The error that occurred
    error_category: ErrorCategory      # Categorized error type
    step_id: str                       # ID of the step that failed
    workflow_id: str                   # ID of the workflow
    timestamp: datetime = field(default_factory=datetime.utcnow)
    retry_count: int = 0               # Number of retries attempted
    state_snapshot: Optional[Dict[str, Any]] = None  # Snapshot of relevant state
    additional_info: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    def with_retry_count(self, count: int) -> 'RecoveryContext':
        """Create a new context with an updated retry count."""
        new_context = copy.deepcopy(self)
        new_context.retry_count = count
        return new_context


@dataclass
class Checkpoint:
    """Represents a workflow state checkpoint."""
    id: str                                         # Unique identifier for the checkpoint
    workflow_id: str                                # ID of the workflow
    step_id: str                                    # ID of the step
    checkpoint_type: CheckpointType                 # Type of checkpoint
    timestamp: datetime = field(default_factory=datetime.utcnow)
    state: Dict[str, Any] = field(default_factory=dict)  # State snapshot
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to a dictionary for persistence."""
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "checkpoint_type": self.checkpoint_type.value,
            "timestamp": self.timestamp.isoformat(),
            "state": self.state,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Checkpoint':
        """Create a checkpoint from a dictionary."""
        checkpoint_data = copy.deepcopy(data)
        
        # Parse timestamp if it's a string
        if isinstance(checkpoint_data.get("timestamp"), str):
            checkpoint_data["timestamp"] = datetime.fromisoformat(checkpoint_data["timestamp"])
            
        # Convert checkpoint_type to enum if it's a string
        if isinstance(checkpoint_data.get("checkpoint_type"), str):
            checkpoint_data["checkpoint_type"] = CheckpointType(checkpoint_data["checkpoint_type"])
            
        return cls(**checkpoint_data)


class RetryPolicy:
    """Configurable policy for retry operations."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_on: Set[ErrorCategory] = None,
        timeout: Optional[float] = None
    ):
        """Initialize a retry policy.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            backoff_factor: Factor to increase delay with each retry
            jitter: Whether to add random jitter to delay
            retry_on: Set of error categories to retry on (None for all)
            timeout: Overall timeout for all retries in seconds
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on = retry_on or {
            ErrorCategory.TRANSIENT,
            ErrorCategory.RESOURCE,
            ErrorCategory.DEPENDENCY,
            ErrorCategory.TIMEOUT
        }
        self.timeout = timeout
        
    def should_retry(self, context: RecoveryContext) -> bool:
        """Determine if a retry should be attempted.
        
        Args:
            context: The recovery context
            
        Returns:
            True if retry should be attempted, False otherwise
        """
        # Check retry count
        if context.retry_count >= self.max_retries:
            return False
            
        # Check error category
        if context.error_category not in self.retry_on:
            return False
            
        return True
        
    def get_delay(self, retry_count: int) -> float:
        """Calculate the delay for the next retry.
        
        Args:
            retry_count: Current retry attempt count
            
        Returns:
            Delay in seconds
        """
        delay = min(
            self.max_delay, 
            self.initial_delay * (self.backoff_factor ** retry_count)
        )
        
        # Add jitter if enabled (±20% variation)
        if self.jitter:
            import random
            jitter_factor = 1.0 + (random.random() * 0.4 - 0.2)
            delay *= jitter_factor
            
        return delay


class RecoveryStrategy:
    """Base class for recovery strategies."""
    
    def __init__(self, name: str):
        """Initialize a recovery strategy.
        
        Args:
            name: Name of the strategy
        """
        self.name = name
        
    async def recover(self, context: RecoveryContext) -> RecoveryAction:
        """Attempt to recover from an error.
        
        Args:
            context: The recovery context
            
        Returns:
            The recovery action to take
        """
        raise NotImplementedError("Subclasses must implement recover()")
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Determine if this strategy can handle the given error.
        
        Args:
            context: The recovery context
            
        Returns:
            True if this strategy can handle the error, False otherwise
        """
        raise NotImplementedError("Subclasses must implement can_handle()")


class RetryStrategy(RecoveryStrategy):
    """Strategy for recovering by retrying the failed operation."""
    
    def __init__(self, retry_policy: RetryPolicy = None):
        """Initialize a retry strategy.
        
        Args:
            retry_policy: The retry policy to use
        """
        super().__init__("retry")
        self.retry_policy = retry_policy or RetryPolicy()
        
    async def recover(self, context: RecoveryContext) -> RecoveryAction:
        """Attempt to recover by retrying the operation.
        
        Args:
            context: The recovery context
            
        Returns:
            The recovery action to take
        """
        if not self.retry_policy.should_retry(context):
            logger.info(f"Retry limit reached for step {context.step_id} in workflow {context.workflow_id}")
            return RecoveryAction.ABORT
            
        # Calculate delay
        delay = self.retry_policy.get_delay(context.retry_count)
        
        logger.info(f"Retrying step {context.step_id} in workflow {context.workflow_id} "
                   f"after {delay:.2f}s (attempt {context.retry_count + 1})")
        
        # Wait for delay
        await asyncio.sleep(delay)
        
        return RecoveryAction.RETRY
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Determine if retry strategy can handle the given error.
        
        Args:
            context: The recovery context
            
        Returns:
            True if retry strategy can handle the error, False otherwise
        """
        return context.error_category in self.retry_policy.retry_on


class RollbackStrategy(RecoveryStrategy):
    """Strategy for recovering by rolling back to a previous checkpoint."""
    
    def __init__(self, checkpoint_manager: 'CheckpointManager'):
        """Initialize a rollback strategy.
        
        Args:
            checkpoint_manager: Manager for checkpoint operations
        """
        super().__init__("rollback")
        self.checkpoint_manager = checkpoint_manager
        
    async def recover(self, context: RecoveryContext) -> RecoveryAction:
        """Attempt to recover by rolling back to a checkpoint.
        
        Args:
            context: The recovery context
            
        Returns:
            The recovery action to take
        """
        # Look for the most recent checkpoint for this workflow
        checkpoint = await self.checkpoint_manager.get_latest_checkpoint(
            context.workflow_id, 
            before_step=context.step_id
        )
        
        if checkpoint is None:
            logger.warning(f"No checkpoint found for rollback in workflow {context.workflow_id}")
            return RecoveryAction.ABORT
            
        logger.info(f"Rolling back to checkpoint {checkpoint.id} at step {checkpoint.step_id}")
        
        # Restore the checkpoint state
        await self.checkpoint_manager.restore_checkpoint(checkpoint.id)
        
        return RecoveryAction.ROLLBACK
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Determine if rollback strategy can handle the given error.
        
        Args:
            context: The recovery context
            
        Returns:
            True if rollback strategy can handle the error, False otherwise
        """
        # Can handle logical, state, and some dependency errors
        return context.error_category in {
            ErrorCategory.LOGICAL, 
            ErrorCategory.STATE_INVALID,
            ErrorCategory.DEPENDENCY
        }


class AlternatePathStrategy(RecoveryStrategy):
    """Strategy for recovering by taking an alternate execution path."""
    
    def __init__(self, alternate_paths: Dict[str, Callable] = None):
        """Initialize an alternate path strategy.
        
        Args:
            alternate_paths: Dictionary mapping step IDs to alternate path functions
        """
        super().__init__("alternate_path")
        self.alternate_paths = alternate_paths or {}
        
    async def recover(self, context: RecoveryContext) -> RecoveryAction:
        """Attempt to recover by using an alternate execution path.
        
        Args:
            context: The recovery context
            
        Returns:
            The recovery action to take
        """
        step_id = context.step_id
        
        # Check if we have an alternate path for this step
        if step_id in self.alternate_paths:
            alternate_func = self.alternate_paths[step_id]
            
            logger.info(f"Using alternate path for step {step_id} in workflow {context.workflow_id}")
            
            try:
                # Execute the alternate path
                if inspect.iscoroutinefunction(alternate_func):
                    await alternate_func(context)
                else:
                    alternate_func(context)
                    
                return RecoveryAction.ALTERNATE_PATH
            except Exception as e:
                logger.warning(f"Alternate path for {step_id} failed: {e}")
        
        # No alternate path or alternate path failed
        logger.warning(f"No alternate path available for step {step_id}")
        return RecoveryAction.SKIP
        
    def can_handle(self, context: RecoveryContext) -> bool:
        """Determine if this strategy can handle the given error.
        
        Args:
            context: The recovery context
            
        Returns:
            True if this strategy can handle the error, False otherwise
        """
        # Can handle if we have an alternate path for this step
        return context.step_id in self.alternate_paths
        
    def register_alternate_path(self, step_id: str, alternate_func: Callable):
        """Register an alternate path for a step.
        
        Args:
            step_id: ID of the step
            alternate_func: Function to execute as the alternate path
        """
        self.alternate_paths[step_id] = alternate_func


class ErrorCategorizer:
    """Categorizes errors for appropriate recovery strategies."""
    
    def __init__(self):
        """Initialize the error categorizer."""
        self.error_matchers: List[Dict[str, Any]] = [
            # Transient errors
            {
                "patterns": [
                    "timeout", "timed out", "temporarily unavailable", 
                    "connection reset", "connection refused", "too many requests",
                    "service unavailable", "retry", "throttled"
                ],
                "exception_types": [
                    TimeoutError, ConnectionError, ConnectionRefusedError, 
                    ConnectionResetError, BrokenPipeError
                ],
                "category": ErrorCategory.TRANSIENT
            },
            
            # Resource errors
            {
                "patterns": [
                    "resource", "memory", "disk", "space", "quota", 
                    "limit exceeded", "out of", "insufficient"
                ],
                "exception_types": [MemoryError, OSError],
                "category": ErrorCategory.RESOURCE
            },
            
            # State validation errors
            {
                "patterns": [
                    "validation", "invalid state", "invalid value", 
                    "not valid", "schema", "constraint"
                ],
                "exception_types": [ValueError, TypeError, AssertionError],
                "category": ErrorCategory.STATE_INVALID
            },
            
            # Dependency errors
            {
                "patterns": [
                    "dependency", "import", "module", "not found", 
                    "missing", "required", "depends on"
                ],
                "exception_types": [ImportError, ModuleNotFoundError],
                "category": ErrorCategory.DEPENDENCY
            },
            
            # Security errors
            {
                "patterns": [
                    "security", "permission denied", "unauthorized", 
                    "forbidden", "not allowed", "access denied"
                ],
                "exception_types": [PermissionError],
                "category": ErrorCategory.SECURITY
            },
            
            # Timeout errors
            {
                "patterns": ["timeout", "timed out", "deadline exceeded"],
                "exception_types": [TimeoutError, asyncio.TimeoutError],
                "category": ErrorCategory.TIMEOUT
            }
        ]
        
    def categorize(self, error: Exception) -> ErrorCategory:
        """Categorize an error.
        
        Args:
            error: The error to categorize
            
        Returns:
            The error category
        """
        error_str = str(error).lower()
        error_type = type(error)
        
        # Check for exact exception type matches
        for matcher in self.error_matchers:
            if error_type in matcher.get("exception_types", []):
                return matcher["category"]
                
        # Check for pattern matches in the error message
        for matcher in self.error_matchers:
            for pattern in matcher.get("patterns", []):
                if pattern.lower() in error_str:
                    return matcher["category"]
                    
        # Fallback to logical or unknown error categories
        if isinstance(error, (ValueError, TypeError, AssertionError)):
            return ErrorCategory.LOGICAL
            
        return ErrorCategory.UNKNOWN
        
    def register_matcher(
        self, 
        category: ErrorCategory, 
        patterns: List[str] = None, 
        exception_types: List[Type[Exception]] = None
    ):
        """Register a new error matcher.
        
        Args:
            category: The error category
            patterns: List of string patterns to match in error messages
            exception_types: List of exception types to match
        """
        if patterns is None and exception_types is None:
            raise ValueError("Must provide either patterns or exception_types")
            
        self.error_matchers.append({
            "patterns": patterns or [],
            "exception_types": exception_types or [],
            "category": category
        })


class CheckpointManager:
    """Manages workflow state checkpoints."""
    
    def __init__(
        self, 
        state_manager: StateManager,
        persistence_dir: Optional[str] = None,
        auto_checkpoint_interval: Optional[int] = None
    ):
        """Initialize the checkpoint manager.
        
        Args:
            state_manager: The state manager to checkpoint
            persistence_dir: Directory for checkpoint persistence
            auto_checkpoint_interval: Interval for automatic checkpoints in seconds
        """
        self.state_manager = state_manager
        self._persistence_dir = persistence_dir or os.path.join("data", "checkpoints")
        self.auto_checkpoint_interval = auto_checkpoint_interval
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._last_auto_checkpoint: Dict[str, datetime] = {}
        
        # Ensure persistence directory exists
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)
        
    async def create_checkpoint(
        self,
        workflow_id: str,
        step_id: str,
        checkpoint_type: CheckpointType = CheckpointType.MANUAL,
        metadata: Dict[str, Any] = None
    ) -> Checkpoint:
        """Create a new checkpoint.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            checkpoint_type: Type of checkpoint
            metadata: Additional metadata
            
        Returns:
            The created checkpoint
        """
        checkpoint_id = f"{workflow_id}_{step_id}_{datetime.utcnow().isoformat()}"
        
        # Get current state
        state_snapshot = self.state_manager.export_state_to_dict()
        
        # Create checkpoint
        checkpoint = Checkpoint(
            id=checkpoint_id,
            workflow_id=workflow_id,
            step_id=step_id,
            checkpoint_type=checkpoint_type,
            state=state_snapshot,
            metadata=metadata or {}
        )
        
        # Store checkpoint
        self._checkpoints[checkpoint_id] = checkpoint
        
        # Persist checkpoint
        await self._persist_checkpoint(checkpoint)
        
        # Update last auto checkpoint time if relevant
        if checkpoint_type == CheckpointType.AUTO:
            self._last_auto_checkpoint[workflow_id] = checkpoint.timestamp
            
        return checkpoint
        
    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore state from a checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to restore
            
        Returns:
            True if successful, False otherwise
        """
        # Get checkpoint
        checkpoint = self._checkpoints.get(checkpoint_id)
        
        if checkpoint is None:
            # Try to load from disk
            try:
                checkpoint = await self._load_checkpoint(checkpoint_id)
            except Exception as e:
                logger.error(f"Error loading checkpoint {checkpoint_id}: {e}")
                return False
                
        if checkpoint is None:
            logger.warning(f"Checkpoint {checkpoint_id} not found")
            return False
            
        # Restore state
        try:
            # Clear existing variables that are in the checkpoint
            for var_name in checkpoint.state:
                try:
                    self.state_manager.delete_variable(var_name)
                except:
                    pass
                    
            # Restore variables from checkpoint
            for var_name, var_value in checkpoint.state.items():
                try:
                    # If variable exists, update it, otherwise create it
                    try:
                        existing_var = self.state_manager.get_variable(var_name)
                        self.state_manager.set_variable_value(var_name, var_value)
                    except:
                        self.state_manager.create_variable(
                            name=var_name,
                            value=var_value,
                            scope=StateScope.WORKFLOW
                        )
                except Exception as e:
                    logger.warning(f"Error restoring variable {var_name}: {e}")
                    
            logger.info(f"Restored checkpoint {checkpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring checkpoint {checkpoint_id}: {e}")
            return False
            
    async def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Get a checkpoint by ID.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            The checkpoint, or None if not found
        """
        checkpoint = self._checkpoints.get(checkpoint_id)
        
        if checkpoint is None:
            # Try to load from disk
            try:
                checkpoint = await self._load_checkpoint(checkpoint_id)
            except:
                pass
                
        return checkpoint
        
    async def get_latest_checkpoint(
        self, 
        workflow_id: str, 
        checkpoint_type: Optional[CheckpointType] = None,
        before_step: Optional[str] = None
    ) -> Optional[Checkpoint]:
        """Get the latest checkpoint for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            checkpoint_type: Optional filter by checkpoint type
            before_step: Optional step ID to get checkpoints before
            
        Returns:
            The latest checkpoint, or None if not found
        """
        # Filter checkpoints
        checkpoints = [
            cp for cp in self._checkpoints.values()
            if cp.workflow_id == workflow_id
            and (checkpoint_type is None or cp.checkpoint_type == checkpoint_type)
        ]
        
        if before_step:
            checkpoints = [cp for cp in checkpoints if cp.step_id != before_step]
            
        if not checkpoints:
            return None
            
        # Return the most recent checkpoint
        return max(checkpoints, key=lambda cp: cp.timestamp)
        
    async def check_auto_checkpoint(self, workflow_id: str, step_id: str) -> Optional[Checkpoint]:
        """Check if an automatic checkpoint should be created.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the current step
            
        Returns:
            The created checkpoint if one was made, None otherwise
        """
        if self.auto_checkpoint_interval is None:
            return None
            
        last_time = self._last_auto_checkpoint.get(workflow_id)
        now = datetime.utcnow()
        
        if last_time is None or (now - last_time).total_seconds() >= self.auto_checkpoint_interval:
            return await self.create_checkpoint(
                workflow_id,
                step_id,
                checkpoint_type=CheckpointType.AUTO,
                metadata={"reason": "auto_interval"}
            )
            
        return None
        
    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint to delete
            
        Returns:
            True if successful, False otherwise
        """
        if checkpoint_id in self._checkpoints:
            del self._checkpoints[checkpoint_id]
            
        # Delete from disk if it exists
        if self._persistence_dir:
            filepath = os.path.join(self._persistence_dir, f"{checkpoint_id}.json")
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    return True
                except Exception as e:
                    logger.error(f"Error deleting checkpoint file {filepath}: {e}")
                    return False
                    
        return True
        
    async def _persist_checkpoint(self, checkpoint: Checkpoint):
        """Persist a checkpoint to disk.
        
        Args:
            checkpoint: The checkpoint to persist
        """
        if not self._persistence_dir:
            return
            
        filepath = os.path.join(self._persistence_dir, f"{checkpoint.id}.json")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(checkpoint.to_dict(), f, default=str, indent=2)
            logger.debug(f"Checkpoint saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving checkpoint to {filepath}: {e}")
            
    async def _load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load a checkpoint from disk.
        
        Args:
            checkpoint_id: ID of the checkpoint to load
            
        Returns:
            The loaded checkpoint, or None if not found
        """
        if not self._persistence_dir:
            return None
            
        filepath = os.path.join(self._persistence_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(filepath):
            return None
            
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            checkpoint = Checkpoint.from_dict(data)
            
            # Cache the loaded checkpoint
            self._checkpoints[checkpoint_id] = checkpoint
            
            return checkpoint
        except Exception as e:
            logger.error(f"Error loading checkpoint from {filepath}: {e}")
            return None


class RecoveryCallback:
    """Callback interface for recovery actions."""
    
    async def pre_recovery(self, context: RecoveryContext) -> None:
        """Called before recovery attempt.
        
        Args:
            context: Recovery context
        """
        pass
        
    async def post_recovery(
        self, 
        context: RecoveryContext, 
        action: RecoveryAction, 
        success: bool
    ) -> None:
        """Called after recovery attempt.
        
        Args:
            context: Recovery context
            action: Recovery action taken
            success: Whether the recovery was successful
        """
        pass
        
    async def on_abort(self, context: RecoveryContext) -> None:
        """Called when workflow is aborted.
        
        Args:
            context: Recovery context
        """
        pass


class TransactionManager:
    """Manages transaction-like semantics for workflow steps."""
    
    def __init__(self, checkpoint_manager: CheckpointManager):
        """Initialize the transaction manager.
        
        Args:
            checkpoint_manager: Manager for checkpoint operations
        """
        self.checkpoint_manager = checkpoint_manager
        self._active_transactions: Dict[str, Dict[str, Any]] = {}
        
    @contextmanager
    async def transaction(self, workflow_id: str, step_id: str):
        """Context manager for a transaction-like operation.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            
        Yields:
            None
        """
        # Create a transaction context
        transaction_id = f"{workflow_id}_{step_id}_{datetime.utcnow().isoformat()}"
        
        # Create a checkpoint
        checkpoint = await self.checkpoint_manager.create_checkpoint(
            workflow_id,
            step_id,
            checkpoint_type=CheckpointType.TRANSACTIONAL,
            metadata={"transaction_id": transaction_id}
        )
        
        self._active_transactions[transaction_id] = {
            "workflow_id": workflow_id,
            "step_id": step_id,
            "checkpoint_id": checkpoint.id,
            "start_time": datetime.utcnow()
        }
        
        try:
            # Execute the transaction body
            yield
            
            # Transaction completed successfully
            self._active_transactions[transaction_id]["status"] = "committed"
            
        except Exception as e:
            # Transaction failed, roll back to checkpoint
            logger.warning(f"Transaction {transaction_id} failed, rolling back: {e}")
            await self.checkpoint_manager.restore_checkpoint(checkpoint.id)
            self._active_transactions[transaction_id]["status"] = "rolled_back"
            self._active_transactions[transaction_id]["error"] = str(e)
            
            # Re-raise the exception
            raise
            
        finally:
            # Clean up transaction
            self._active_transactions[transaction_id]["end_time"] = datetime.utcnow()


class RecoveryManager:
    """Manages error recovery strategies for workflows."""
    
    def __init__(
        self, 
        state_manager: StateManager,
        persistence_dir: Optional[str] = None
    ):
        """Initialize the recovery manager.
        
        Args:
            state_manager: The state manager for workflow state
            persistence_dir: Directory for persistence
        """
        self.state_manager = state_manager
        self._persistence_dir = persistence_dir or os.path.join("data", "recovery")
        
        # Ensure persistence directory exists
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)
            
        # Initialize components
        self.error_categorizer = ErrorCategorizer()
        self.checkpoint_manager = CheckpointManager(
            state_manager=state_manager,
            persistence_dir=os.path.join(self._persistence_dir, "checkpoints"),
            auto_checkpoint_interval=300  # 5 minutes default
        )
        self.transaction_manager = TransactionManager(self.checkpoint_manager)
        
        # Initialize recovery strategies
        self._strategies: List[RecoveryStrategy] = [
            RetryStrategy(RetryPolicy()),
            RollbackStrategy(self.checkpoint_manager),
            AlternatePathStrategy()
        ]
        
        # Initialize callbacks
        self._callbacks: List[RecoveryCallback] = []
        
        # Recovery state
        self._recovery_history: List[Dict[str, Any]] = []
        
    def register_strategy(self, strategy: RecoveryStrategy):
        """Register a recovery strategy.
        
        Args:
            strategy: The strategy to register
        """
        self._strategies.append(strategy)
        
    def register_callback(self, callback: RecoveryCallback):
        """Register a recovery callback.
        
        Args:
            callback: The callback to register
        """
        self._callbacks.append(callback)
        
    async def handle_error(
        self, 
        error: Exception, 
        workflow_id: str, 
        step_id: str,
        additional_info: Dict[str, Any] = None
    ) -> RecoveryAction:
        """Handle an error in a workflow step.
        
        Args:
            error: The error that occurred
            workflow_id: ID of the workflow
            step_id: ID of the step that failed
            additional_info: Additional context information
            
        Returns:
            The recovery action taken
        """
        # Categorize the error
        error_category = self.error_categorizer.categorize(error)
        
        # Create recovery context
        context = RecoveryContext(
            error=error,
            error_category=error_category,
            step_id=step_id,
            workflow_id=workflow_id,
            state_snapshot=self.state_manager.export_state_to_dict(),
            additional_info=additional_info or {}
        )
        
        # Store error details
        recovery_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id,
            "step_id": step_id,
            "error": str(error),
            "error_type": type(error).__name__,
            "error_category": error_category.value,
            "traceback": traceback.format_exc(),
            "context": additional_info or {}
        }
        self._recovery_history.append(recovery_record)
        
        # Call pre-recovery callbacks
        for callback in self._callbacks:
            try:
                await callback.pre_recovery(context)
            except Exception as e:
                logger.warning(f"Error in pre-recovery callback: {e}")
                
        # Find applicable recovery strategy
        strategy = None
        for s in self._strategies:
            if s.can_handle(context):
                strategy = s
                break
                
        if strategy is None:
            logger.warning(f"No recovery strategy found for {error_category} error in step {step_id}")
            recovery_action = RecoveryAction.ABORT
        else:
            # Apply recovery strategy
            logger.info(f"Applying {strategy.name} strategy for {error_category} error in step {step_id}")
            try:
                recovery_action = await strategy.recover(context)
            except Exception as e:
                logger.error(f"Error applying recovery strategy: {e}")
                recovery_action = RecoveryAction.ABORT
                
        # Update recovery record
        recovery_record["recovery_strategy"] = strategy.name if strategy else None
        recovery_record["recovery_action"] = recovery_action.value
        
        # Call post-recovery callbacks
        success = recovery_action != RecoveryAction.ABORT
        for callback in self._callbacks:
            try:
                await callback.post_recovery(context, recovery_action, success)
                if not success:
                    await callback.on_abort(context)
            except Exception as e:
                logger.warning(f"Error in post-recovery callback: {e}")
                
        return recovery_action
        
    @contextmanager
    async def recovery_context(self, workflow_id: str, step_id: str):
        """Context manager for error recovery.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            
        Yields:
            None
        """
        try:
            # Create auto checkpoint if needed
            await self.checkpoint_manager.check_auto_checkpoint(workflow_id, step_id)
            
            # Execute the protected code
            yield
            
        except Exception as e:
            # Handle the error
            recovery_action = await self.handle_error(e, workflow_id, step_id)
            
            # Re-raise if abort
            if recovery_action == RecoveryAction.ABORT:
                raise
                
            # Re-raise if we should retry (caller will handle retry logic)
            if recovery_action == RecoveryAction.RETRY:
                raise
                
            # Skip step if specified
            if recovery_action == RecoveryAction.SKIP:
                logger.info(f"Skipping step {step_id} after error")
                pass
                
    @contextmanager
    async def step_transaction(self, workflow_id: str, step_id: str):
        """Context manager for a transactional step execution.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            
        Yields:
            None
        """
        async with self.transaction_manager.transaction(workflow_id, step_id):
            yield
            
    async def checkpoint_workflow(
        self, 
        workflow_id: str, 
        step_id: str, 
        metadata: Dict[str, Any] = None
    ) -> Checkpoint:
        """Create a manual checkpoint for a workflow.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the current step
            metadata: Additional metadata
            
        Returns:
            The created checkpoint
        """
        return await self.checkpoint_manager.create_checkpoint(
            workflow_id,
            step_id,
            checkpoint_type=CheckpointType.MANUAL,
            metadata=metadata
        )
        
    async def restore_to_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore workflow state to a checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint
            
        Returns:
            True if successful, False otherwise
        """
        return await self.checkpoint_manager.restore_checkpoint(checkpoint_id)
        
    def get_recovery_history(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recovery event history.
        
        Args:
            workflow_id: Optional workflow ID to filter by
            
        Returns:
            List of recovery history records
        """
        if workflow_id:
            return [r for r in self._recovery_history if r["workflow_id"] == workflow_id]
        return self._recovery_history
        
    def clear_history(self):
        """Clear the recovery history."""
        self._recovery_history.clear()


# Create convenience function for use in workflows
async def with_recovery(recovery_manager: RecoveryManager, workflow_id: str, step_id: str, func, *args, **kwargs):
    """Execute a function with error recovery.
    
    Args:
        recovery_manager: The recovery manager
        workflow_id: ID of the workflow
        step_id: ID of the step
        func: The function to execute
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function
    """
    max_retries = 3
    retry_count = 0
    
    while retry_count <= max_retries:
        try:
            async with recovery_manager.recovery_context(workflow_id, step_id):
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result
                
        except Exception as e:
            retry_count += 1
            
            if retry_count > max_retries:
                logger.error(f"Maximum retries exceeded for step {step_id} in workflow {workflow_id}")
                raise
                
            logger.info(f"Retrying {step_id} in workflow {workflow_id} (attempt {retry_count})")
            # Continue to next retry attempt
            
    # Should not reach here due to raised exception above
    raise RuntimeError("Unexpected execution path in with_recovery")


# Create a global recovery_manager instance for convenience
recovery_manager = None

def init_recovery_manager(state_manager_instance=None, persistence_dir=None):
    """Initialize the global recovery manager.
    
    Args:
        state_manager_instance: The state manager to use, defaults to global state_manager
        persistence_dir: Directory for persistence
        
    Returns:
        The initialized recovery manager
    """
    global recovery_manager
    
    # Use the provided state manager or the global instance
    sm = state_manager_instance if state_manager_instance is not None else state_manager
    
    # Create recovery manager if not already initialized
    if recovery_manager is None:
        recovery_manager = RecoveryManager(sm, persistence_dir)
        
    return recovery_manager
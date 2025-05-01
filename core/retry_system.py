"""Retry system for step execution failures in workflows.

This module provides a framework for retrying failed steps with configurable policies
and strategies. It builds on the error categorization from the recovery system but
focuses specifically on retry logic that can be configured on a per-step basis.

Key components:
- RetryPolicy: Configurable policy for retry operations
- RetryStrategies: Different strategies for retrying operations
- RetryManager: Manages retry operations across workflows
- StepRetryContext: Context for step retry operations
- Monitors & Reporters: Track and report retry operations
"""

import logging
import time
import json
import os
import copy
import asyncio
import inspect
import random
import traceback
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union, TypeVar, Generic, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager, asynccontextmanager

from .recovery_system import ErrorCategory, RecoveryAction, RecoveryContext
from .state_manager import StateManager, StateScope, StatePermission, StateVariable, state_manager

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryResult(str, Enum):
    """Results of a retry operation."""
    SUCCESS = "success"              # Retry succeeded
    FAILED = "failed"                # Retry failed
    MAX_RETRIES_EXCEEDED = "max_retries_exceeded"  # Maximum retries exceeded
    TIMEOUT_EXCEEDED = "timeout_exceeded"  # Overall timeout exceeded
    ABORTED = "aborted"              # Retry was aborted
    POLICY_REJECTED = "policy_rejected"  # Retry policy rejected the retry


class BackoffStrategy(str, Enum):
    """Strategies for calculating delay between retries."""
    CONSTANT = "constant"            # Constant delay
    LINEAR = "linear"                # Linear increasing delay
    EXPONENTIAL = "exponential"      # Exponential increasing delay
    FIBONACCI = "fibonacci"          # Fibonacci increasing delay
    RANDOM = "random"                # Random delay within a range
    DECORRELATED_JITTER = "decorrelated_jitter"  # Decorrelated jitter delay


@dataclass
class RetryPolicyConfig:
    """Configuration for retry policies."""
    max_retries: int = 3             # Maximum number of retry attempts
    initial_delay_ms: int = 1000     # Initial delay between retries in milliseconds
    max_delay_ms: int = 60000        # Maximum delay between retries in milliseconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL  # Strategy for delay calculation
    backoff_factor: float = 2.0      # Factor for backoff calculation
    jitter: bool = True              # Whether to add random jitter to delay
    jitter_factor: float = 0.2       # Maximum jitter as a percentage of delay
    retry_on: Set[ErrorCategory] = field(default_factory=lambda: {
        ErrorCategory.TRANSIENT,
        ErrorCategory.RESOURCE,
        ErrorCategory.DEPENDENCY,
        ErrorCategory.TIMEOUT
    })                               # Error categories to retry on
    timeout_ms: Optional[int] = None  # Overall timeout for all retries in milliseconds
    abort_on: Set[ErrorCategory] = field(default_factory=lambda: {
        ErrorCategory.SECURITY,
        ErrorCategory.PERMISSION
    })                               # Error categories to immediately abort on
    retry_status_codes: Optional[Set[int]] = None  # HTTP status codes to retry on (if applicable)
    max_retry_overhead_ms: Optional[int] = None  # Maximum cumulative delay time
    retry_circuit_breaker: bool = False  # Whether to use circuit breaker patterns
    circuit_breaker_threshold: int = 5  # Failure threshold for circuit breaker
    circuit_recovery_time_ms: int = 60000  # Time to reset circuit breaker 

    def to_dict(self) -> Dict[str, Any]:
        """Convert policy to a dictionary for persistence."""
        result = copy.deepcopy(self.__dict__)
        
        # Convert enum values to strings
        if isinstance(result.get("backoff_strategy"), BackoffStrategy):
            result["backoff_strategy"] = result["backoff_strategy"].value
            
        # Convert sets to lists for serialization
        if isinstance(result.get("retry_on"), set):
            result["retry_on"] = [cat.value if isinstance(cat, ErrorCategory) else cat 
                                 for cat in result["retry_on"]]
                                 
        if isinstance(result.get("abort_on"), set):
            result["abort_on"] = [cat.value if isinstance(cat, ErrorCategory) else cat 
                                 for cat in result["abort_on"]]
                                 
        if isinstance(result.get("retry_status_codes"), set):
            result["retry_status_codes"] = list(result["retry_status_codes"])
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RetryPolicyConfig':
        """Create a policy from a dictionary."""
        policy_data = copy.deepcopy(data)
        
        # Convert string to enum for backoff_strategy
        if isinstance(policy_data.get("backoff_strategy"), str):
            policy_data["backoff_strategy"] = BackoffStrategy(policy_data["backoff_strategy"])
            
        # Convert retry_on list to set of enums
        if isinstance(policy_data.get("retry_on"), list):
            policy_data["retry_on"] = {
                ErrorCategory(cat) if isinstance(cat, str) else cat 
                for cat in policy_data["retry_on"]
            }
            
        # Convert abort_on list to set of enums
        if isinstance(policy_data.get("abort_on"), list):
            policy_data["abort_on"] = {
                ErrorCategory(cat) if isinstance(cat, str) else cat 
                for cat in policy_data["abort_on"]
            }
            
        # Convert retry_status_codes list to set
        if isinstance(policy_data.get("retry_status_codes"), list):
            policy_data["retry_status_codes"] = set(policy_data["retry_status_codes"])
            
        return cls(**policy_data)


@dataclass
class StepRetryContext:
    """Context for step retry operations."""
    workflow_id: str                   # ID of the workflow
    step_id: str                       # ID of the step
    execution_id: str                  # Unique execution ID for this retry attempt
    original_error: Exception          # The original error that triggered retry
    error_category: ErrorCategory      # Categorized error type
    retry_count: int = 0               # Current retry attempt count
    max_retries: int = 3               # Maximum retries configured
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_retry_time: Optional[datetime] = None
    next_retry_time: Optional[datetime] = None
    total_delay_ms: int = 0            # Total time spent waiting between retries
    attempt_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_state: Dict[str, Any] = field(default_factory=dict)  # State preserved between retries
    additional_info: Dict[str, Any] = field(default_factory=dict)  # Additional context info

    def record_attempt(self, 
                      attempt_number: int, 
                      status: RetryResult, 
                      error: Optional[Exception] = None, 
                      duration_ms: Optional[int] = None):
        """Record a retry attempt."""
        attempt = {
            "attempt_number": attempt_number,
            "timestamp": datetime.utcnow().isoformat(),
            "status": status.value,
            "error": str(error) if error else None,
            "error_type": type(error).__name__ if error else None,
            "duration_ms": duration_ms,
        }
        self.attempt_history.append(attempt)
        
    def remaining_attempts(self) -> int:
        """Get the number of remaining retry attempts."""
        return max(0, self.max_retries - self.retry_count)
    
    def exceeds_max_retries(self) -> bool:
        """Check if maximum retries have been exceeded."""
        return self.retry_count >= self.max_retries
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a dictionary for persistence."""
        result = {
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "execution_id": self.execution_id,
            "original_error": str(self.original_error),
            "error_category": self.error_category.value,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "start_time": self.start_time.isoformat(),
            "last_retry_time": self.last_retry_time.isoformat() if self.last_retry_time else None,
            "next_retry_time": self.next_retry_time.isoformat() if self.next_retry_time else None,
            "total_delay_ms": self.total_delay_ms,
            "attempt_history": self.attempt_history,
            "retry_state": self.retry_state,
            "additional_info": self.additional_info
        }
        return result


class RetryPolicy:
    """Configurable policy for retry operations."""
    
    def __init__(self, config: RetryPolicyConfig = None):
        """Initialize a retry policy.
        
        Args:
            config: Configuration for the retry policy, uses default if not provided
        """
        self.config = config or RetryPolicyConfig()
        self._circuit_breaker_failures = 0
        self._circuit_open_until = None
        
    def should_retry(self, context: StepRetryContext) -> bool:
        """Determine if a retry should be attempted.
        
        Args:
            context: The step retry context
            
        Returns:
            True if retry should be attempted, False otherwise
        """
        # Check if circuit breaker is open (if enabled)
        if self.config.retry_circuit_breaker and self._is_circuit_open():
            logger.warning(f"Circuit breaker open - rejecting retry for step {context.step_id}")
            return False
        
        # Check retry count
        if context.retry_count >= self.config.max_retries:
            logger.info(f"Maximum retries ({self.config.max_retries}) exceeded for step {context.step_id}")
            return False
        
        # Check for abort error categories
        if context.error_category in self.config.abort_on:
            logger.info(f"Error category {context.error_category} is in abort list - no retry for step {context.step_id}")
            return False
            
        # Check if error category is in retry list
        if context.error_category not in self.config.retry_on:
            logger.info(f"Error category {context.error_category} not in retry list for step {context.step_id}")
            return False
        
        # Check overall timeout if configured
        if self.config.timeout_ms is not None:
            elapsed_ms = (datetime.utcnow() - context.start_time).total_seconds() * 1000
            if elapsed_ms >= self.config.timeout_ms:
                logger.info(f"Overall timeout ({self.config.timeout_ms}ms) exceeded for step {context.step_id}")
                return False
                
        # Check maximum retry overhead if configured
        if self.config.max_retry_overhead_ms is not None:
            if context.total_delay_ms >= self.config.max_retry_overhead_ms:
                logger.info(f"Maximum retry overhead ({self.config.max_retry_overhead_ms}ms) exceeded for step {context.step_id}")
                return False
                
        return True
        
    def get_delay_ms(self, retry_count: int) -> int:
        """Calculate the delay for the next retry in milliseconds.
        
        Args:
            retry_count: Current retry attempt count
            
        Returns:
            Delay in milliseconds
        """
        if self.config.backoff_strategy == BackoffStrategy.CONSTANT:
            delay = self.config.initial_delay_ms
            
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.initial_delay_ms * (retry_count + 1)
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.initial_delay_ms * (self.config.backoff_factor ** retry_count)
            
        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            # Generate Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13...
            fib = [1, 1]
            while len(fib) <= retry_count + 1:
                fib.append(fib[-1] + fib[-2])
            delay = self.config.initial_delay_ms * fib[retry_count]
            
        elif self.config.backoff_strategy == BackoffStrategy.RANDOM:
            min_delay = self.config.initial_delay_ms
            max_delay = self.config.initial_delay_ms * (self.config.backoff_factor ** retry_count)
            delay = random.uniform(min_delay, max_delay)
            
        elif self.config.backoff_strategy == BackoffStrategy.DECORRELATED_JITTER:
            # Implementation of the "Decorrelated Jitter" algorithm from
            # https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
            if retry_count == 0:
                delay = self.config.initial_delay_ms
            else:
                prev_delay = self.config.initial_delay_ms * (self.config.backoff_factor ** (retry_count - 1))
                delay = random.uniform(self.config.initial_delay_ms, prev_delay * 3)
            
        else:
            # Default to exponential backoff
            delay = self.config.initial_delay_ms * (self.config.backoff_factor ** retry_count)
        
        # Cap at maximum delay
        delay = min(delay, self.config.max_delay_ms)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            jitter_amount = random.uniform(-jitter_range, jitter_range)
            delay = max(self.config.initial_delay_ms, delay + jitter_amount)
            
        return int(delay)
    
    def record_success(self):
        """Record a successful operation for circuit breaker."""
        if self.config.retry_circuit_breaker:
            self._circuit_breaker_failures = 0
            self._circuit_open_until = None
    
    def record_failure(self):
        """Record a failed operation for circuit breaker."""
        if not self.config.retry_circuit_breaker:
            return
            
        self._circuit_breaker_failures += 1
        
        # Open circuit if threshold reached
        if self._circuit_breaker_failures >= self.config.circuit_breaker_threshold:
            self._circuit_open_until = datetime.utcnow() + timedelta(
                milliseconds=self.config.circuit_recovery_time_ms
            )
            logger.warning(f"Circuit breaker opened - will recover at {self._circuit_open_until}")
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open."""
        if not self.config.retry_circuit_breaker:
            return False
            
        if self._circuit_open_until is None:
            return False
            
        # Check if recovery time has passed
        if datetime.utcnow() > self._circuit_open_until:
            logger.info("Circuit breaker recovery time reached - resetting to half-open state")
            self._circuit_breaker_failures = self.config.circuit_breaker_threshold - 1
            self._circuit_open_until = None
            return False
            
        return True


class RetryStrategy:
    """Base class for retry strategies."""
    
    def __init__(self, name: str, retry_policy: RetryPolicy = None):
        """Initialize a retry strategy.
        
        Args:
            name: Name of the strategy
            retry_policy: Policy for retry operations, uses default if not provided
        """
        self.name = name
        self.retry_policy = retry_policy or RetryPolicy()
        
    async def execute_with_retry(self, 
                               context: StepRetryContext, 
                               func: Callable, 
                               *args, **kwargs) -> Tuple[Any, RetryResult]:
        """Execute a function with retry logic.
        
        Args:
            context: The step retry context
            func: The function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, retry_result)
        """
        raise NotImplementedError("Subclasses must implement execute_with_retry()")


class StandardRetryStrategy(RetryStrategy):
    """Standard retry strategy with configurable policy."""
    
    def __init__(self, retry_policy: RetryPolicy = None):
        """Initialize a standard retry strategy.
        
        Args:
            retry_policy: Policy for retry operations
        """
        super().__init__("standard", retry_policy)
        
    async def execute_with_retry(self, 
                               context: StepRetryContext, 
                               func: Callable, 
                               *args, **kwargs) -> Tuple[Any, RetryResult]:
        """Execute a function with standard retry logic.
        
        Args:
            context: The step retry context
            func: The function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, retry_result)
        """
        while True:
            try:
                start_time = time.time()
                
                # Execute the function
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                    
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record successful attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.SUCCESS,
                    duration_ms=duration_ms
                )
                
                # Record success for circuit breaker
                self.retry_policy.record_success()
                
                return result, RetryResult.SUCCESS
                
            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record failed attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.FAILED,
                    error=e,
                    duration_ms=duration_ms
                )
                
                # Record failure for circuit breaker
                self.retry_policy.record_failure()
                
                # Increment retry count
                context.retry_count += 1
                
                # Check if we should retry
                if not self.retry_policy.should_retry(context):
                    if context.exceeds_max_retries():
                        return None, RetryResult.MAX_RETRIES_EXCEEDED
                    else:
                        return None, RetryResult.POLICY_REJECTED
                        
                # Calculate delay
                delay_ms = self.retry_policy.get_delay_ms(context.retry_count - 1)
                
                # Update context
                context.last_retry_time = datetime.utcnow()
                context.next_retry_time = datetime.utcnow() + timedelta(milliseconds=delay_ms)
                context.total_delay_ms += delay_ms
                
                logger.info(
                    f"Retrying step {context.step_id} in workflow {context.workflow_id} "
                    f"after {delay_ms}ms (attempt {context.retry_count}/{context.max_retries})"
                )
                
                # Wait for delay
                await asyncio.sleep(delay_ms / 1000)


class GradualDegradationRetryStrategy(RetryStrategy):
    """Strategy that gradually degrades functionality with each retry."""
    
    def __init__(self, 
                retry_policy: RetryPolicy = None,
                degradation_levels: List[Dict[str, Any]] = None):
        """Initialize a gradual degradation retry strategy.
        
        Args:
            retry_policy: Policy for retry operations
            degradation_levels: List of degradation level configurations
        """
        super().__init__("gradual_degradation", retry_policy)
        
        # Default degradation levels if none provided
        self.degradation_levels = degradation_levels or [
            {"level": 0, "description": "Full functionality"},
            {"level": 1, "description": "Reduced functionality - timeout extensions", "timeout_multiplier": 1.5},
            {"level": 2, "description": "Reduced functionality - simplified processing", "simplify": True},
            {"level": 3, "description": "Minimal functionality - essential only", "essential_only": True},
        ]
        
    async def execute_with_retry(self, 
                               context: StepRetryContext, 
                               func: Callable, 
                               *args, **kwargs) -> Tuple[Any, RetryResult]:
        """Execute a function with gradual degradation retry logic.
        
        Args:
            context: The step retry context
            func: The function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, retry_result)
        """
        while True:
            try:
                start_time = time.time()
                
                # Determine degradation level based on retry count
                degradation_level = min(context.retry_count, len(self.degradation_levels) - 1)
                level_config = self.degradation_levels[degradation_level]
                
                # Apply degradation settings to kwargs
                modified_kwargs = kwargs.copy()
                
                # Apply timeout multiplier if specified
                if "timeout" in kwargs and "timeout_multiplier" in level_config:
                    modified_kwargs["timeout"] = kwargs["timeout"] * level_config["timeout_multiplier"]
                    
                # Apply simplification flag if specified
                if "simplify" in level_config:
                    modified_kwargs["simplify"] = level_config["simplify"]
                    
                # Apply essential_only flag if specified
                if "essential_only" in level_config:
                    modified_kwargs["essential_only"] = level_config["essential_only"]
                
                # Log degradation level
                logger.info(
                    f"Executing step {context.step_id} with degradation level {degradation_level}: "
                    f"{level_config['description']}"
                )
                
                # Execute the function with modified kwargs
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **modified_kwargs)
                else:
                    result = func(*args, **modified_kwargs)
                    
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record successful attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.SUCCESS,
                    duration_ms=duration_ms
                )
                
                # Record success for circuit breaker
                self.retry_policy.record_success()
                
                return result, RetryResult.SUCCESS
                
            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record failed attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.FAILED,
                    error=e,
                    duration_ms=duration_ms
                )
                
                # Record failure for circuit breaker
                self.retry_policy.record_failure()
                
                # Increment retry count
                context.retry_count += 1
                
                # Check if we should retry
                if not self.retry_policy.should_retry(context):
                    if context.exceeds_max_retries():
                        return None, RetryResult.MAX_RETRIES_EXCEEDED
                    else:
                        return None, RetryResult.POLICY_REJECTED
                        
                # Calculate delay
                delay_ms = self.retry_policy.get_delay_ms(context.retry_count - 1)
                
                # Update context
                context.last_retry_time = datetime.utcnow()
                context.next_retry_time = datetime.utcnow() + timedelta(milliseconds=delay_ms)
                context.total_delay_ms += delay_ms
                
                logger.info(
                    f"Retrying step {context.step_id} in workflow {context.workflow_id} "
                    f"after {delay_ms}ms with degradation level {min(context.retry_count, len(self.degradation_levels) - 1)}"
                )
                
                # Wait for delay
                await asyncio.sleep(delay_ms / 1000)


class FailoverRetryStrategy(RetryStrategy):
    """Strategy that tries alternative implementations if the primary fails."""
    
    def __init__(self, 
                retry_policy: RetryPolicy = None,
                failover_functions: List[Callable] = None):
        """Initialize a failover retry strategy.
        
        Args:
            retry_policy: Policy for retry operations
            failover_functions: List of failover function implementations
        """
        super().__init__("failover", retry_policy)
        self.failover_functions = failover_functions or []
        
    async def execute_with_retry(self, 
                               context: StepRetryContext, 
                               func: Callable, 
                               *args, **kwargs) -> Tuple[Any, RetryResult]:
        """Execute a function with failover retry logic.
        
        Args:
            context: The step retry context
            func: The primary function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, retry_result)
        """
        # Combine primary function with failover functions
        all_functions = [func] + self.failover_functions
        
        # Make sure we don't try more functions than we have
        max_retries = min(context.max_retries, len(all_functions) - 1)
        
        while context.retry_count <= max_retries:
            # Select function to try
            current_func = all_functions[min(context.retry_count, len(all_functions) - 1)]
            
            try:
                start_time = time.time()
                
                # Log which implementation we're trying
                if context.retry_count > 0:
                    logger.info(
                        f"Trying failover implementation #{context.retry_count} for "
                        f"step {context.step_id} in workflow {context.workflow_id}"
                    )
                
                # Execute the selected function
                if inspect.iscoroutinefunction(current_func):
                    result = await current_func(*args, **kwargs)
                else:
                    result = current_func(*args, **kwargs)
                    
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record successful attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.SUCCESS,
                    duration_ms=duration_ms
                )
                
                return result, RetryResult.SUCCESS
                
            except Exception as e:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Record failed attempt
                context.record_attempt(
                    context.retry_count,
                    RetryResult.FAILED,
                    error=e,
                    duration_ms=duration_ms
                )
                
                # Increment retry count
                context.retry_count += 1
                
                # Check if we've tried all implementations
                if context.retry_count > max_retries:
                    return None, RetryResult.MAX_RETRIES_EXCEEDED
                    
                # Calculate delay
                delay_ms = self.retry_policy.get_delay_ms(context.retry_count - 1)
                
                # Update context
                context.last_retry_time = datetime.utcnow()
                context.next_retry_time = datetime.utcnow() + timedelta(milliseconds=delay_ms)
                context.total_delay_ms += delay_ms
                
                logger.info(
                    f"Primary implementation failed for step {context.step_id}, "
                    f"switching to failover #{context.retry_count} after {delay_ms}ms"
                )
                
                # Wait for delay
                await asyncio.sleep(delay_ms / 1000)
                
        # Should not reach here, but return failure if it does
        return None, RetryResult.MAX_RETRIES_EXCEEDED


@dataclass
class RetryMonitorRecord:
    """Record of a retry operation for monitoring."""
    workflow_id: str
    step_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 0
    result: Optional[RetryResult] = None
    error_category: Optional[ErrorCategory] = None
    initial_error: Optional[str] = None
    final_error: Optional[str] = None
    total_duration_ms: Optional[int] = None
    total_delay_ms: Optional[int] = None
    attempt_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to a dictionary for persistence."""
        return {
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "result": self.result.value if self.result else None,
            "error_category": self.error_category.value if self.error_category else None,
            "initial_error": self.initial_error,
            "final_error": self.final_error,
            "total_duration_ms": self.total_duration_ms,
            "total_delay_ms": self.total_delay_ms,
            "attempt_history": self.attempt_history
        }


class RetryMonitor:
    """Monitors retry operations."""
    
    def __init__(self, persistence_dir: Optional[str] = None):
        """Initialize the retry monitor.
        
        Args:
            persistence_dir: Directory for persistence
        """
        self._persistence_dir = persistence_dir or os.path.join("data", "retry_monitor")
        self._records: Dict[str, RetryMonitorRecord] = {}
        
        # Ensure persistence directory exists
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)
            
    def start_monitoring(self, context: StepRetryContext) -> RetryMonitorRecord:
        """Start monitoring a retry operation.
        
        Args:
            context: The step retry context
            
        Returns:
            The created monitoring record
        """
        record = RetryMonitorRecord(
            workflow_id=context.workflow_id,
            step_id=context.step_id,
            execution_id=context.execution_id,
            start_time=context.start_time,
            max_retries=context.max_retries,
            error_category=context.error_category,
            initial_error=str(context.original_error)
        )
        
        self._records[context.execution_id] = record
        return record
        
    def update_record(self, context: StepRetryContext, result: RetryResult, final_error: Optional[Exception] = None):
        """Update a monitoring record with results.
        
        Args:
            context: The step retry context
            result: The retry result
            final_error: The final error if failed
        """
        record = self._records.get(context.execution_id)
        
        if record:
            record.end_time = datetime.utcnow()
            record.retry_count = context.retry_count
            record.result = result
            record.final_error = str(final_error) if final_error else None
            record.total_delay_ms = context.total_delay_ms
            record.attempt_history = copy.deepcopy(context.attempt_history)
            
            # Calculate total duration
            if record.start_time and record.end_time:
                record.total_duration_ms = int((record.end_time - record.start_time).total_seconds() * 1000)
                
            # Persist the record
            self._persist_record(record)
            
    def get_record(self, execution_id: str) -> Optional[RetryMonitorRecord]:
        """Get a monitoring record by execution ID.
        
        Args:
            execution_id: The execution ID
            
        Returns:
            The monitoring record, or None if not found
        """
        return self._records.get(execution_id)
        
    def get_records_for_workflow(self, workflow_id: str) -> List[RetryMonitorRecord]:
        """Get all monitoring records for a workflow.
        
        Args:
            workflow_id: The workflow ID
            
        Returns:
            List of monitoring records
        """
        return [r for r in self._records.values() if r.workflow_id == workflow_id]
        
    def get_records_for_step(self, workflow_id: str, step_id: str) -> List[RetryMonitorRecord]:
        """Get all monitoring records for a specific step.
        
        Args:
            workflow_id: The workflow ID
            step_id: The step ID
            
        Returns:
            List of monitoring records
        """
        return [
            r for r in self._records.values() 
            if r.workflow_id == workflow_id and r.step_id == step_id
        ]
        
    def get_retry_statistics(self, workflow_id: Optional[str] = None, step_id: Optional[str] = None) -> Dict[str, Any]:
        """Get retry statistics.
        
        Args:
            workflow_id: Optional workflow ID filter
            step_id: Optional step ID filter
            
        Returns:
            Dictionary of statistics
        """
        records = self._records.values()
        
        # Apply filters
        if workflow_id:
            records = [r for r in records if r.workflow_id == workflow_id]
        if step_id:
            records = [r for r in records if r.step_id == step_id]
            
        if not records:
            return {
                "total_operations": 0,
                "operations_with_retries": 0,
                "total_retries": 0,
                "success_rate": 0,
                "average_retries": 0,
                "average_delay_ms": 0,
                "results": {}
            }
            
        # Calculate statistics
        total_operations = len(records)
        operations_with_retries = sum(1 for r in records if r.retry_count > 0)
        total_retries = sum(r.retry_count for r in records)
        successful_operations = sum(1 for r in records if r.result == RetryResult.SUCCESS)
        
        # Result distribution
        result_counts = {}
        for r in records:
            if r.result:
                result_counts[r.result.value] = result_counts.get(r.result.value, 0) + 1
                
        # Calculate averages
        average_retries = total_retries / total_operations if total_operations > 0 else 0
        average_delay_ms = (
            sum(r.total_delay_ms for r in records if r.total_delay_ms is not None) / 
            sum(1 for r in records if r.total_delay_ms is not None)
        ) if any(r.total_delay_ms is not None for r in records) else 0
        
        return {
            "total_operations": total_operations,
            "operations_with_retries": operations_with_retries,
            "total_retries": total_retries,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "average_retries": average_retries,
            "average_delay_ms": average_delay_ms,
            "results": result_counts
        }
        
    def clear_records(self):
        """Clear all monitoring records."""
        self._records.clear()
        
    def _persist_record(self, record: RetryMonitorRecord):
        """Persist a monitoring record to disk.
        
        Args:
            record: The record to persist
        """
        if not self._persistence_dir:
            return
            
        filepath = os.path.join(self._persistence_dir, f"{record.execution_id}.json")
        
        try:
            with open(filepath, 'w') as f:
                json.dump(record.to_dict(), f, default=str, indent=2)
        except Exception as e:
            logger.error(f"Error persisting retry monitor record: {e}")


class RetryReporter:
    """Generates reports for retry operations."""
    
    def __init__(self, retry_monitor: RetryMonitor):
        """Initialize the retry reporter.
        
        Args:
            retry_monitor: The retry monitor to report on
        """
        self.retry_monitor = retry_monitor
        
    def generate_summary_report(self, 
                              workflow_id: Optional[str] = None, 
                              step_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a summary report.
        
        Args:
            workflow_id: Optional workflow ID filter
            step_id: Optional step ID filter
            
        Returns:
            Dictionary with report data
        """
        stats = self.retry_monitor.get_retry_statistics(workflow_id, step_id)
        
        # Get records based on filters
        records = []
        if workflow_id and step_id:
            records = self.retry_monitor.get_records_for_step(workflow_id, step_id)
        elif workflow_id:
            records = self.retry_monitor.get_records_for_workflow(workflow_id)
        else:
            records = list(self.retry_monitor._records.values())
            
        # Get error categories
        error_categories = {}
        for r in records:
            if r.error_category:
                category = r.error_category.value
                error_categories[category] = error_categories.get(category, 0) + 1
                
        # Get most retried steps
        step_retries = {}
        for r in records:
            key = f"{r.workflow_id}:{r.step_id}"
            if r.retry_count > 0:
                if key not in step_retries:
                    step_retries[key] = {
                        "workflow_id": r.workflow_id,
                        "step_id": r.step_id,
                        "total_retries": 0,
                        "operations": 0,
                        "success_rate": 0
                    }
                step_retries[key]["total_retries"] += r.retry_count
                step_retries[key]["operations"] += 1
                if r.result == RetryResult.SUCCESS:
                    step_retries[key]["success_rate"] += 1
        
        # Calculate success rates
        for key, data in step_retries.items():
            if data["operations"] > 0:
                data["success_rate"] = data["success_rate"] / data["operations"]
                
        # Sort steps by total retries
        most_retried_steps = sorted(
            step_retries.values(), 
            key=lambda x: x["total_retries"], 
            reverse=True
        )[:10]  # Top 10
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id,
            "step_id": step_id,
            "statistics": stats,
            "error_categories": error_categories,
            "most_retried_steps": most_retried_steps
        }
        
    def generate_detailed_report(self, 
                               workflow_id: str, 
                               step_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate a detailed report for a workflow.
        
        Args:
            workflow_id: The workflow ID
            step_id: Optional step ID filter
            
        Returns:
            Dictionary with report data
        """
        # Get records
        if step_id:
            records = self.retry_monitor.get_records_for_step(workflow_id, step_id)
        else:
            records = self.retry_monitor.get_records_for_workflow(workflow_id)
            
        # Convert records to dictionaries
        record_dicts = [r.to_dict() for r in records]
        
        # Get summary statistics
        summary = self.generate_summary_report(workflow_id, step_id)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_id": workflow_id,
            "step_id": step_id,
            "summary": summary,
            "records": record_dicts
        }
        
    def export_report_to_json(self, 
                            report_data: Dict[str, Any], 
                            file_path: str):
        """Export a report to JSON.
        
        Args:
            report_data: The report data
            file_path: Path to write the report
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(report_data, f, default=str, indent=2)
                
            logger.info(f"Report exported to {file_path}")
        except Exception as e:
            logger.error(f"Error exporting report: {e}")


class RetryManager:
    """Manages retry operations for workflow steps."""
    
    def __init__(self, 
                state_manager: StateManager,
                persistence_dir: Optional[str] = None):
        """Initialize the retry manager.
        
        Args:
            state_manager: The state manager for workflow state
            persistence_dir: Directory for persistence
        """
        self.state_manager = state_manager
        self._persistence_dir = persistence_dir or os.path.join("data", "retry")
        
        # Ensure persistence directory exists
        if self._persistence_dir:
            os.makedirs(self._persistence_dir, exist_ok=True)
            
        # Initialize components
        self.retry_monitor = RetryMonitor(os.path.join(self._persistence_dir, "monitor"))
        self.retry_reporter = RetryReporter(self.retry_monitor)
        
        # Policy registry
        self._policy_registry: Dict[str, RetryPolicy] = {}
        self._step_policy_mapping: Dict[str, Dict[str, str]] = {}  # workflow_id -> step_id -> policy_name
        
        # Strategy registry
        self._strategy_registry: Dict[str, RetryStrategy] = {
            "standard": StandardRetryStrategy(),
            "gradual_degradation": GradualDegradationRetryStrategy(),
            "failover": FailoverRetryStrategy()
        }
        self._step_strategy_mapping: Dict[str, Dict[str, str]] = {}  # workflow_id -> step_id -> strategy_name
        
        # Default policy
        self.register_policy("default", RetryPolicy())
        
    def register_policy(self, policy_name: str, policy: RetryPolicy):
        """Register a retry policy.
        
        Args:
            policy_name: Name for the policy
            policy: The retry policy to register
        """
        self._policy_registry[policy_name] = policy
        
    def register_strategy(self, strategy_name: str, strategy: RetryStrategy):
        """Register a retry strategy.
        
        Args:
            strategy_name: Name for the strategy
            strategy: The retry strategy to register
        """
        self._strategy_registry[strategy_name] = strategy
        
    def get_policy(self, policy_name: str) -> RetryPolicy:
        """Get a retry policy by name.
        
        Args:
            policy_name: Name of the policy
            
        Returns:
            The retry policy, or default if not found
        """
        return self._policy_registry.get(policy_name, self._policy_registry.get("default"))
        
    def get_strategy(self, strategy_name: str) -> RetryStrategy:
        """Get a retry strategy by name.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            The retry strategy, or standard if not found
        """
        return self._strategy_registry.get(strategy_name, self._strategy_registry.get("standard"))
        
    def assign_policy_to_step(self, workflow_id: str, step_id: str, policy_name: str):
        """Assign a retry policy to a step.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            policy_name: Name of the policy to assign
        """
        if workflow_id not in self._step_policy_mapping:
            self._step_policy_mapping[workflow_id] = {}
            
        self._step_policy_mapping[workflow_id][step_id] = policy_name
        
    def assign_strategy_to_step(self, workflow_id: str, step_id: str, strategy_name: str):
        """Assign a retry strategy to a step.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            strategy_name: Name of the strategy to assign
        """
        if workflow_id not in self._step_strategy_mapping:
            self._step_strategy_mapping[workflow_id] = {}
            
        self._step_strategy_mapping[workflow_id][step_id] = strategy_name
        
    def get_policy_for_step(self, workflow_id: str, step_id: str) -> RetryPolicy:
        """Get the retry policy for a step.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            
        Returns:
            The retry policy for the step
        """
        policy_name = self._step_policy_mapping.get(workflow_id, {}).get(step_id, "default")
        return self.get_policy(policy_name)
        
    def get_strategy_for_step(self, workflow_id: str, step_id: str) -> RetryStrategy:
        """Get the retry strategy for a step.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            
        Returns:
            The retry strategy for the step
        """
        strategy_name = self._step_strategy_mapping.get(workflow_id, {}).get(step_id, "standard")
        return self.get_strategy(strategy_name)
        
    async def execute_with_retry(self, 
                               workflow_id: str,
                               step_id: str,
                               func: Callable,
                               error_categorizer: Callable[[Exception], ErrorCategory] = None,
                               max_retries: Optional[int] = None,
                               *args, **kwargs) -> Tuple[Any, RetryResult]:
        """Execute a function with retry logic.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            func: The function to execute
            error_categorizer: Function to categorize errors, uses the default if not provided
            max_retries: Optional maximum retries, uses policy default if not provided
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Tuple of (result, retry_result)
        """
        # Get policy and strategy for this step
        policy = self.get_policy_for_step(workflow_id, step_id)
        strategy = self.get_strategy_for_step(workflow_id, step_id)
        
        # Ensure strategy uses the correct policy
        strategy.retry_policy = policy
        
        # Create execution ID
        execution_id = f"{workflow_id}_{step_id}_{datetime.utcnow().isoformat()}"
        
        # Default error categorizer if not provided
        if error_categorizer is None:
            from .recovery_system import ErrorCategorizer
            categorizer = ErrorCategorizer()
            error_categorizer = categorizer.categorize
            
        # Create initial context
        context = StepRetryContext(
            workflow_id=workflow_id,
            step_id=step_id,
            execution_id=execution_id,
            max_retries=max_retries or policy.config.max_retries,
            # These will be populated on first error
            original_error=Exception("Placeholder"),
            error_category=ErrorCategory.UNKNOWN
        )
        
        # Start monitoring
        self.retry_monitor.start_monitoring(context)
        
        try:
            # Try to execute without retry first
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
                
            # Update monitor with success
            self.retry_monitor.update_record(context, RetryResult.SUCCESS)
            
            return result, RetryResult.SUCCESS
            
        except Exception as e:
            # Categorize the error
            error_category = error_categorizer(e)
            
            # Update context with error information
            context.original_error = e
            context.error_category = error_category
            
            # Check if we should immediately abort based on policy
            if error_category in policy.config.abort_on:
                logger.warning(
                    f"Aborting without retry for step {step_id} due to error category {error_category}"
                )
                
                # Update monitor with abort
                self.retry_monitor.update_record(context, RetryResult.ABORTED, e)
                
                # Re-raise the exception
                raise
                
            # Execute with retry strategy
            try:
                result, retry_result = await strategy.execute_with_retry(context, func, *args, **kwargs)
                
                # Update monitor with result
                self.retry_monitor.update_record(context, retry_result)
                
                if retry_result != RetryResult.SUCCESS:
                    # Log failure
                    logger.warning(
                        f"Step {step_id} in workflow {workflow_id} failed after "
                        f"{context.retry_count} retries: {retry_result}"
                    )
                    
                    # Raise exception if it's a failure
                    if retry_result in (RetryResult.MAX_RETRIES_EXCEEDED, RetryResult.POLICY_REJECTED):
                        raise context.original_error
                        
                return result, retry_result
                
            except Exception as final_e:
                # Update monitor with final error
                self.retry_monitor.update_record(
                    context, 
                    RetryResult.FAILED, 
                    final_e
                )
                
                # Re-raise the exception
                raise
                
    @asynccontextmanager
    async def retry_context(self, 
                          workflow_id: str,
                          step_id: str,
                          error_categorizer: Callable[[Exception], ErrorCategory] = None,
                          max_retries: Optional[int] = None):
        """Context manager for retry operations.
        
        Args:
            workflow_id: ID of the workflow
            step_id: ID of the step
            error_categorizer: Function to categorize errors
            max_retries: Optional maximum retries
            
        Yields:
            The retry context
        """
        # Get policy for this step
        policy = self.get_policy_for_step(workflow_id, step_id)
        
        # Create execution ID
        execution_id = f"{workflow_id}_{step_id}_{datetime.utcnow().isoformat()}"
        
        # Default error categorizer if not provided
        if error_categorizer is None:
            from .recovery_system import ErrorCategorizer
            categorizer = ErrorCategorizer()
            error_categorizer = categorizer.categorize
            
        # Create initial context
        context = StepRetryContext(
            workflow_id=workflow_id,
            step_id=step_id,
            execution_id=execution_id,
            max_retries=max_retries or policy.config.max_retries,
            # These will be populated on error
            original_error=Exception("Placeholder"),
            error_category=ErrorCategory.UNKNOWN
        )
        
        # Start monitoring
        self.retry_monitor.start_monitoring(context)
        
        retry_count = 0
        while retry_count <= context.max_retries:
            try:
                # Execute the protected code
                yield context
                
                # If we get here, execution succeeded
                self.retry_monitor.update_record(context, RetryResult.SUCCESS)
                return
                
            except Exception as e:
                # On first error, update context
                if retry_count == 0:
                    context.original_error = e
                    context.error_category = error_categorizer(e)
                
                # Record the attempt
                context.record_attempt(
                    retry_count,
                    RetryResult.FAILED,
                    error=e
                )
                
                # Increment retry count
                retry_count += 1
                context.retry_count = retry_count
                
                # Check if we should abort based on policy
                if context.error_category in policy.config.abort_on:
                    logger.warning(
                        f"Aborting without retry for step {step_id} due to error category {context.error_category}"
                    )
                    
                    # Update monitor with abort
                    self.retry_monitor.update_record(context, RetryResult.ABORTED, e)
                    
                    # Re-raise the exception
                    raise
                
                # Check if we should retry
                if not policy.should_retry(context):
                    # Update monitor with result
                    result = RetryResult.MAX_RETRIES_EXCEEDED if context.exceeds_max_retries() else RetryResult.POLICY_REJECTED
                    self.retry_monitor.update_record(context, result, e)
                    
                    # Log failure
                    logger.warning(
                        f"Step {step_id} in workflow {workflow_id} failed after "
                        f"{retry_count - 1} retries: {result}"
                    )
                    
                    # Re-raise the exception
                    raise
                    
                # Calculate delay
                delay_ms = policy.get_delay_ms(retry_count - 1)
                
                # Update context
                context.last_retry_time = datetime.utcnow()
                context.next_retry_time = datetime.utcnow() + timedelta(milliseconds=delay_ms)
                context.total_delay_ms += delay_ms
                
                logger.info(
                    f"Retrying step {step_id} in workflow {workflow_id} "
                    f"after {delay_ms}ms (attempt {retry_count}/{context.max_retries})"
                )
                
                # Wait for delay
                await asyncio.sleep(delay_ms / 1000)
                
        # Should not reach here, but return failure if it does
        self.retry_monitor.update_record(context, RetryResult.MAX_RETRIES_EXCEEDED)
        raise context.original_error


# Create a global retry_manager instance for convenience
retry_manager = None

def init_retry_manager(state_manager_instance=None, persistence_dir=None) -> RetryManager:
    """Initialize the global retry manager.
    
    Args:
        state_manager_instance: The state manager to use, defaults to global state_manager
        persistence_dir: Directory for persistence
        
    Returns:
        The initialized retry manager
    """
    global retry_manager
    
    # Use the provided state manager or the global instance
    sm = state_manager_instance if state_manager_instance is not None else state_manager
    
    # Create retry manager if not already initialized
    if retry_manager is None:
        retry_manager = RetryManager(sm, persistence_dir)
        
    return retry_manager


# Convenience function for retrying operations
async def with_retry(
    func: Callable,
    workflow_id: str,
    step_id: str,
    retry_manager_instance: RetryManager = None,
    max_retries: Optional[int] = None,
    *args, **kwargs
) -> Any:
    """Execute a function with retry logic.
    
    Args:
        func: The function to execute
        workflow_id: ID of the workflow
        step_id: ID of the step
        retry_manager_instance: The retry manager to use, uses global if not provided
        max_retries: Optional maximum retries
        *args: Arguments for the function
        **kwargs: Keyword arguments for the function
        
    Returns:
        The result of the function
    """
    # Use the provided retry manager or the global instance
    rm = retry_manager_instance if retry_manager_instance is not None else retry_manager
    
    # Make sure we have a retry manager
    if rm is None:
        rm = init_retry_manager()
        
    # Execute with retry
    result, retry_result = await rm.execute_with_retry(
        workflow_id=workflow_id,
        step_id=step_id,
        func=func,
        max_retries=max_retries,
        *args, **kwargs
    )
    
    return result
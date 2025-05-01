"""Execution logging system for tracking workflow and playbook execution.

This module provides comprehensive logging for workflow and playbook execution,
capturing detailed metrics, step execution, agent communications, tool usage,
and overall performance data. It integrates with the progress tracking system
while providing additional details useful for debugging, performance analysis,
and audit trails.

Key components:
- ExecutionLogger: Main class for tracking and logging execution details
- ExecutionRecord: Data structure for storing execution information
- ExecutionMetrics: Performance and resource usage tracking
- ExecutionLogHandler: Storage and retrieval of execution logs
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union, Callable

from .tools.logger import BaseLogger
from .progress_tracker import ProgressTracker, ProgressItemType, progress_tracker
from .state_manager import StateManager, StateScope, state_manager
from .recovery_system import CheckpointManager, Checkpoint

# Configure module logger
logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of an execution process."""
    INITIATED = "initiated"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    PAUSED = "paused"


class LogLevel(str, Enum):
    """Log levels for execution events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ExecutionStepType(str, Enum):
    """Types of execution steps to log."""
    WORKFLOW_START = "workflow_start"
    WORKFLOW_END = "workflow_end"
    STEP_START = "step_start"
    STEP_END = "step_end"
    AGENT_ACTION = "agent_action"
    TOOL_CALL = "tool_call"
    USER_INPUT = "user_input"
    DECISION_POINT = "decision_point"
    STATE_CHANGE = "state_change"
    CHECKPOINT = "checkpoint"
    ROLLBACK = "rollback"
    RETRY = "retry"
    ERROR = "error"
    CUSTOM = "custom"


class ExecutionRecord:
    """A record of an execution process with detailed metrics and events."""
    
    def __init__(
        self,
        execution_id: str,
        name: str,
        type: str,
        description: str = "",
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Initialize an execution record.
        
        Args:
            execution_id: Unique ID for this execution
            name: Name of the execution (workflow/playbook name)
            type: Type of execution (e.g., "playbook", "workflow")
            description: Description of the execution
            correlation_id: ID for correlating related executions
            parent_id: Parent execution ID if this is a child execution
            metadata: Additional metadata about the execution
        """
        # Core identifiers
        self.execution_id = execution_id
        self.name = name
        self.type = type
        self.description = description
        self.correlation_id = correlation_id or execution_id
        self.parent_id = parent_id
        self.metadata = metadata or {}
        
        # Status and timing
        self.status = ExecutionStatus.INITIATED
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_seconds: float = 0.0
        
        # Components and resources
        self.agents_used: Set[str] = set()
        self.tools_used: Set[str] = set()
        self.llm_tokens_used: int = 0
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_cost: float = 0.0
        
        # Detailed event logs
        self.events: List[Dict[str, Any]] = []
        self.steps: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Metrics and performance data
        self.peak_memory_mb: float = 0.0
        self.avg_step_duration_seconds: float = 0.0
        self.max_step_duration_seconds: float = 0.0
        self.total_steps: int = 0
        self.failed_steps: int = 0
        self.retried_steps: int = 0
        
        # Progress tracking integration
        self.progress_id: Optional[str] = None
        
        # State tracking (for debugging and analysis)
        self.initial_state: Dict[str, Any] = {}
        self.final_state: Dict[str, Any] = {}
        self.state_changes: List[Dict[str, Any]] = []
    
    def start(self) -> None:
        """Mark the execution as started."""
        self.status = ExecutionStatus.RUNNING
        self.start_time = datetime.utcnow()
        self.add_event(
            ExecutionStepType.WORKFLOW_START,
            LogLevel.INFO,
            f"Started execution of {self.type} '{self.name}'",
            {"status": self.status}
        )
    
    def complete(self, success: bool = True) -> None:
        """Mark the execution as completed or failed.
        
        Args:
            success: Whether the execution was successful
        """
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        if success:
            self.status = ExecutionStatus.COMPLETED
            self.add_event(
                ExecutionStepType.WORKFLOW_END,
                LogLevel.INFO,
                f"Completed execution of {self.type} '{self.name}'",
                {
                    "status": self.status,
                    "duration_seconds": self.duration_seconds,
                    "total_steps": self.total_steps
                }
            )
        else:
            self.status = ExecutionStatus.FAILED
            self.add_event(
                ExecutionStepType.WORKFLOW_END,
                LogLevel.ERROR,
                f"Failed execution of {self.type} '{self.name}'",
                {
                    "status": self.status,
                    "duration_seconds": self.duration_seconds,
                    "total_steps": self.total_steps,
                    "failed_steps": self.failed_steps
                }
            )
    
    def abort(self, reason: str) -> None:
        """Mark the execution as aborted.
        
        Args:
            reason: Reason for aborting the execution
        """
        self.status = ExecutionStatus.ABORTED
        self.end_time = datetime.utcnow()
        self.duration_seconds = (self.end_time - self.start_time).total_seconds()
        
        self.add_event(
            ExecutionStepType.WORKFLOW_END,
            LogLevel.WARNING,
            f"Aborted execution of {self.type} '{self.name}': {reason}",
            {
                "status": self.status,
                "reason": reason,
                "duration_seconds": self.duration_seconds
            }
        )
    
    def pause(self, reason: str) -> None:
        """Mark the execution as paused.
        
        Args:
            reason: Reason for pausing the execution
        """
        self.status = ExecutionStatus.PAUSED
        
        self.add_event(
            ExecutionStepType.CUSTOM,
            LogLevel.INFO,
            f"Paused execution of {self.type} '{self.name}': {reason}",
            {
                "status": self.status,
                "reason": reason
            }
        )
    
    def resume(self) -> None:
        """Resume a paused execution."""
        if self.status == ExecutionStatus.PAUSED:
            self.status = ExecutionStatus.RUNNING
            
            self.add_event(
                ExecutionStepType.CUSTOM,
                LogLevel.INFO,
                f"Resumed execution of {self.type} '{self.name}'",
                {"status": self.status}
            )
    
    def add_event(
        self,
        step_type: ExecutionStepType,
        level: LogLevel,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add an event to the execution log.
        
        Args:
            step_type: Type of execution step
            level: Log level of the event
            message: Event message
            data: Additional event data
        """
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "step_type": step_type,
            "level": level,
            "message": message,
            "data": data or {}
        }
        
        self.events.append(event)
        
        # Add to steps list if it's a step event
        if step_type in (ExecutionStepType.STEP_START, ExecutionStepType.STEP_END):
            self.steps.append(event)
            
        # Add to errors list if it's an error
        if level == LogLevel.ERROR or step_type == ExecutionStepType.ERROR:
            self.errors.append(event)
    
    def log_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log LLM usage data.
        
        Args:
            model: LLM model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Estimated cost of the API call
            context: Additional context about the LLM usage
        """
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.llm_tokens_used += (prompt_tokens + completion_tokens)
        self.total_cost += cost
        
        self.add_event(
            ExecutionStepType.CUSTOM,
            LogLevel.INFO,
            f"LLM usage: {prompt_tokens} prompt tokens, {completion_tokens} completion tokens",
            {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "cost": cost,
                "context": context or {}
            }
        )
    
    def log_agent_action(
        self,
        agent_id: str,
        action: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log an agent action.
        
        Args:
            agent_id: ID of the agent
            action: Action performed by the agent
            input_data: Input data for the action
            output_data: Output data from the action
            duration_seconds: Duration of the action
            error: Error that occurred (if any)
        """
        self.agents_used.add(agent_id)
        
        # Determine level based on presence of error
        level = LogLevel.ERROR if error else LogLevel.INFO
        
        self.add_event(
            ExecutionStepType.AGENT_ACTION,
            level,
            f"Agent {agent_id}: {action}" + (f" (Error: {error})" if error else ""),
            {
                "agent_id": agent_id,
                "action": action,
                "input_data": input_data,
                "output_data": output_data,
                "duration_seconds": duration_seconds,
                "error": error
            }
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log a tool call.
        
        Args:
            tool_name: Name of the tool
            parameters: Parameters passed to the tool
            result: Result returned by the tool
            duration_seconds: Duration of the tool call
            error: Error that occurred (if any)
        """
        self.tools_used.add(tool_name)
        
        # Determine level based on presence of error
        level = LogLevel.ERROR if error else LogLevel.INFO
        
        self.add_event(
            ExecutionStepType.TOOL_CALL,
            level,
            f"Tool call: {tool_name}" + (f" (Error: {error})" if error else ""),
            {
                "tool_name": tool_name,
                "parameters": parameters,
                "result": result,
                "duration_seconds": duration_seconds,
                "error": error
            }
        )
    
    def log_step_start(
        self,
        step_id: str,
        step_name: str,
        step_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log the start of a workflow step.
        
        Args:
            step_id: ID of the step
            step_name: Name of the step
            step_type: Type of the step
            parameters: Parameters for the step
        """
        self.total_steps += 1
        
        self.add_event(
            ExecutionStepType.STEP_START,
            LogLevel.INFO,
            f"Started step: {step_name} ({step_type})",
            {
                "step_id": step_id,
                "step_name": step_name,
                "step_type": step_type,
                "parameters": parameters or {},
                "step_number": self.total_steps
            }
        )
    
    def log_step_end(
        self,
        step_id: str,
        step_name: str,
        success: bool,
        result: Optional[Any] = None,
        duration_seconds: float = 0.0,
        error: Optional[str] = None
    ) -> None:
        """Log the end of a workflow step.
        
        Args:
            step_id: ID of the step
            step_name: Name of the step
            success: Whether the step was successful
            result: Result of the step
            duration_seconds: Duration of the step
            error: Error that occurred (if any)
        """
        # Update step metrics
        if duration_seconds > 0:
            self.avg_step_duration_seconds = (
                (self.avg_step_duration_seconds * (self.total_steps - 1) + duration_seconds) / 
                self.total_steps
            )
            self.max_step_duration_seconds = max(self.max_step_duration_seconds, duration_seconds)
        
        if not success:
            self.failed_steps += 1
        
        # Determine level based on success
        level = LogLevel.ERROR if not success else LogLevel.INFO
        
        self.add_event(
            ExecutionStepType.STEP_END,
            level,
            f"{'Failed' if not success else 'Completed'} step: {step_name}",
            {
                "step_id": step_id,
                "step_name": step_name,
                "success": success,
                "result": result,
                "duration_seconds": duration_seconds,
                "error": error
            }
        )
    
    def log_decision(
        self,
        decision_point: str,
        condition: str,
        result: bool,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a decision point in the workflow.
        
        Args:
            decision_point: Description of the decision point
            condition: Condition that was evaluated
            result: Result of the condition evaluation
            context: Additional context for the decision
        """
        self.add_event(
            ExecutionStepType.DECISION_POINT,
            LogLevel.INFO,
            f"Decision point: {decision_point} -> {'True' if result else 'False'}",
            {
                "decision_point": decision_point,
                "condition": condition,
                "result": result,
                "context": context or {}
            }
        )
    
    def log_state_change(
        self,
        variable: str,
        old_value: Any,
        new_value: Any,
        source: Optional[str] = None
    ) -> None:
        """Log a state variable change.
        
        Args:
            variable: Name of the variable
            old_value: Previous value
            new_value: New value
            source: Source of the state change
        """
        change = {
            "timestamp": datetime.utcnow().isoformat(),
            "variable": variable,
            "old_value": old_value,
            "new_value": new_value,
            "source": source
        }
        
        self.state_changes.append(change)
        
        self.add_event(
            ExecutionStepType.STATE_CHANGE,
            LogLevel.INFO,
            f"State change: {variable} = {new_value}",
            change
        )
    
    def log_checkpoint(
        self,
        checkpoint_id: str,
        checkpoint_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a checkpoint creation.
        
        Args:
            checkpoint_id: ID of the checkpoint
            checkpoint_type: Type of checkpoint
            data: Additional checkpoint data
        """
        self.add_event(
            ExecutionStepType.CHECKPOINT,
            LogLevel.INFO,
            f"Created checkpoint: {checkpoint_id} ({checkpoint_type})",
            {
                "checkpoint_id": checkpoint_id,
                "checkpoint_type": checkpoint_type,
                "data": data or {}
            }
        )
    
    def log_rollback(
        self,
        checkpoint_id: str,
        reason: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log a rollback to checkpoint.
        
        Args:
            checkpoint_id: ID of the checkpoint
            reason: Reason for the rollback
            success: Whether the rollback was successful
            details: Additional rollback details
        """
        level = LogLevel.INFO if success else LogLevel.ERROR
        
        self.add_event(
            ExecutionStepType.ROLLBACK,
            level,
            f"Rollback to checkpoint {checkpoint_id}: {reason}",
            {
                "checkpoint_id": checkpoint_id,
                "reason": reason,
                "success": success,
                "details": details or {}
            }
        )
    
    def log_retry(
        self,
        step_id: str,
        step_name: str,
        attempt: int,
        max_attempts: int,
        reason: str,
        backoff_seconds: Optional[float] = None
    ) -> None:
        """Log a retry attempt.
        
        Args:
            step_id: ID of the step being retried
            step_name: Name of the step
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            reason: Reason for the retry
            backoff_seconds: Seconds to wait before retry
        """
        self.retried_steps += 1
        
        self.add_event(
            ExecutionStepType.RETRY,
            LogLevel.WARNING,
            f"Retrying step {step_name} (attempt {attempt}/{max_attempts}): {reason}",
            {
                "step_id": step_id,
                "step_name": step_name,
                "attempt": attempt,
                "max_attempts": max_attempts,
                "reason": reason,
                "backoff_seconds": backoff_seconds
            }
        )
    
    def log_error(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log an error.
        
        Args:
            error_message: Error message
            error_type: Type of error
            traceback: Error traceback
            context: Additional context about the error
        """
        self.add_event(
            ExecutionStepType.ERROR,
            LogLevel.ERROR,
            f"Error: {error_message}",
            {
                "error_message": error_message,
                "error_type": error_type,
                "traceback": traceback,
                "context": context or {}
            }
        )
    
    def log_user_input(
        self,
        input_type: str,
        prompt: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log user input.
        
        Args:
            input_type: Type of input
            prompt: Prompt shown to user
            response: User's response
            metadata: Additional metadata
        """
        self.add_event(
            ExecutionStepType.USER_INPUT,
            LogLevel.INFO,
            f"User input ({input_type}): {prompt}",
            {
                "input_type": input_type,
                "prompt": prompt,
                "response": response,
                "metadata": metadata or {}
            }
        )
    
    def log_memory_usage(self, memory_mb: float) -> None:
        """Log memory usage.
        
        Args:
            memory_mb: Memory usage in MB
        """
        # Update peak memory
        self.peak_memory_mb = max(self.peak_memory_mb, memory_mb)
        
        self.add_event(
            ExecutionStepType.CUSTOM,
            LogLevel.DEBUG,
            f"Memory usage: {memory_mb:.2f} MB",
            {"memory_mb": memory_mb}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the execution record to a dictionary.
        
        Returns:
            Dictionary representation of the execution record
        """
        return {
            # Identifiers
            "execution_id": self.execution_id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "correlation_id": self.correlation_id,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
            
            # Status and timing
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": self.duration_seconds,
            
            # Components and resources
            "agents_used": list(self.agents_used),
            "tools_used": list(self.tools_used),
            "llm_tokens_used": self.llm_tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_cost": self.total_cost,
            
            # Events
            "events": self.events,
            "steps": self.steps,
            "errors": self.errors,
            
            # Metrics
            "peak_memory_mb": self.peak_memory_mb,
            "avg_step_duration_seconds": self.avg_step_duration_seconds,
            "max_step_duration_seconds": self.max_step_duration_seconds,
            "total_steps": self.total_steps,
            "failed_steps": self.failed_steps,
            "retried_steps": self.retried_steps,
            
            # Progress tracking
            "progress_id": self.progress_id,
            
            # State tracking
            "initial_state": self.initial_state,
            "final_state": self.final_state,
            "state_changes": self.state_changes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecutionRecord':
        """Create an execution record from a dictionary.
        
        Args:
            data: Dictionary representation of an execution record
            
        Returns:
            ExecutionRecord instance
        """
        record = cls(
            execution_id=data["execution_id"],
            name=data["name"],
            type=data["type"],
            description=data.get("description", ""),
            correlation_id=data.get("correlation_id"),
            parent_id=data.get("parent_id"),
            metadata=data.get("metadata", {})
        )
        
        # Status and timing
        record.status = data["status"]
        record.start_time = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            record.end_time = datetime.fromisoformat(data["end_time"])
        record.duration_seconds = data.get("duration_seconds", 0.0)
        
        # Components and resources
        record.agents_used = set(data.get("agents_used", []))
        record.tools_used = set(data.get("tools_used", []))
        record.llm_tokens_used = data.get("llm_tokens_used", 0)
        record.prompt_tokens = data.get("prompt_tokens", 0)
        record.completion_tokens = data.get("completion_tokens", 0)
        record.total_cost = data.get("total_cost", 0.0)
        
        # Events
        record.events = data.get("events", [])
        record.steps = data.get("steps", [])
        record.errors = data.get("errors", [])
        
        # Metrics and performance data
        record.peak_memory_mb = data.get("peak_memory_mb", 0.0)
        record.avg_step_duration_seconds = data.get("avg_step_duration_seconds", 0.0)
        record.max_step_duration_seconds = data.get("max_step_duration_seconds", 0.0)
        record.total_steps = data.get("total_steps", 0)
        record.failed_steps = data.get("failed_steps", 0)
        record.retried_steps = data.get("retried_steps", 0)
        
        # Progress tracking
        record.progress_id = data.get("progress_id")
        
        # State tracking
        record.initial_state = data.get("initial_state", {})
        record.final_state = data.get("final_state", {})
        record.state_changes = data.get("state_changes", [])
        
        return record


class ExecutionLogHandler:
    """Handles storage and retrieval of execution logs."""
    
    def __init__(self, base_dir: str = "logs/executions"):
        """Initialize the execution log handler.
        
        Args:
            base_dir: Base directory for storing execution logs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def store_execution_log(self, record: ExecutionRecord) -> str:
        """Store an execution record.
        
        Args:
            record: Execution record to store
            
        Returns:
            Path where the log was stored
        """
        # Create directory structure by date
        date_subdir = record.start_time.strftime("%Y/%m/%d")
        log_dir = self.base_dir / date_subdir
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename
        filename = f"{record.execution_id}_{record.name.replace(' ', '_')}.json"
        log_path = log_dir / filename
        
        # Write log file
        with open(log_path, "w") as f:
            json.dump(record.to_dict(), f, indent=2)
            
        return str(log_path)
    
    def get_execution_log(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Retrieve an execution record by ID.
        
        Args:
            execution_id: ID of the execution to retrieve
            
        Returns:
            ExecutionRecord if found, None otherwise
        """
        # Search for the execution log file
        for path in self.base_dir.glob("**/*.json"):
            if execution_id in path.name:
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                        return ExecutionRecord.from_dict(data)
                except Exception as e:
                    logger.error(f"Error loading execution log {path}: {e}")
                    return None
        
        return None
    
    def find_execution_logs(
        self,
        name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find execution logs matching criteria.
        
        Args:
            name: Filter by execution name
            status: Filter by status
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)
            correlation_id: Filter by correlation ID
            limit: Maximum number of results to return
            
        Returns:
            List of matching execution log summaries
        """
        results = []
        
        # Find all log files
        for path in sorted(self.base_dir.glob("**/*.json"), reverse=True):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                    
                # Apply filters
                if name and name not in data.get("name", ""):
                    continue
                    
                if status and data.get("status") != status:
                    continue
                    
                if correlation_id and data.get("correlation_id") != correlation_id:
                    continue
                    
                log_start_time = datetime.fromisoformat(data.get("start_time", ""))
                
                if start_date and log_start_time < start_date:
                    continue
                    
                if end_date and log_start_time > end_date:
                    continue
                
                # Create summary (avoid including full event list)
                summary = {
                    "execution_id": data.get("execution_id"),
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "status": data.get("status"),
                    "start_time": data.get("start_time"),
                    "end_time": data.get("end_time"),
                    "duration_seconds": data.get("duration_seconds"),
                    "total_steps": data.get("total_steps"),
                    "failed_steps": data.get("failed_steps"),
                    "log_path": str(path)
                }
                
                results.append(summary)
                
                if len(results) >= limit:
                    break
                    
            except Exception as e:
                logger.error(f"Error processing log file {path}: {e}")
        
        return results
    
    def get_execution_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        execution_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated metrics for executions.
        
        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            execution_type: Filter by execution type
            
        Returns:
            Dictionary of aggregated metrics
        """
        metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_duration_seconds": 0,
            "total_llm_tokens": 0,
            "total_cost": 0,
            "total_steps": 0,
            "failed_steps": 0,
            "retried_steps": 0,
            "avg_steps_per_execution": 0,
            "status_counts": {},
            "tool_usage": {},
            "agent_usage": {},
            "executions_by_date": {},
            "avg_duration_by_type": {}
        }
        
        total_duration = 0
        
        # Process all log files
        for path in self.base_dir.glob("**/*.json"):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                
                # Apply filters
                log_start_time = datetime.fromisoformat(data.get("start_time", ""))
                
                if start_date and log_start_time < start_date:
                    continue
                    
                if end_date and log_start_time > end_date:
                    continue
                    
                if execution_type and data.get("type") != execution_type:
                    continue
                
                # Update basic metrics
                metrics["total_executions"] += 1
                
                if data.get("status") == ExecutionStatus.COMPLETED:
                    metrics["successful_executions"] += 1
                elif data.get("status") == ExecutionStatus.FAILED:
                    metrics["failed_executions"] += 1
                
                # Update status counts
                status = data.get("status", "unknown")
                metrics["status_counts"][status] = metrics["status_counts"].get(status, 0) + 1
                
                # Update duration metrics
                duration = data.get("duration_seconds", 0)
                total_duration += duration
                
                # Update type-specific metrics
                exec_type = data.get("type", "unknown")
                if exec_type not in metrics["avg_duration_by_type"]:
                    metrics["avg_duration_by_type"][exec_type] = {"total": 0, "count": 0}
                    
                metrics["avg_duration_by_type"][exec_type]["total"] += duration
                metrics["avg_duration_by_type"][exec_type]["count"] += 1
                
                # Update token and cost metrics
                metrics["total_llm_tokens"] += data.get("llm_tokens_used", 0)
                metrics["total_cost"] += data.get("total_cost", 0)
                
                # Update step metrics
                metrics["total_steps"] += data.get("total_steps", 0)
                metrics["failed_steps"] += data.get("failed_steps", 0)
                metrics["retried_steps"] += data.get("retried_steps", 0)
                
                # Update tool usage
                for tool in data.get("tools_used", []):
                    metrics["tool_usage"][tool] = metrics["tool_usage"].get(tool, 0) + 1
                
                # Update agent usage
                for agent in data.get("agents_used", []):
                    metrics["agent_usage"][agent] = metrics["agent_usage"].get(agent, 0) + 1
                
                # Update date-based metrics
                date_str = log_start_time.strftime("%Y-%m-%d")
                if date_str not in metrics["executions_by_date"]:
                    metrics["executions_by_date"][date_str] = 0
                    
                metrics["executions_by_date"][date_str] += 1
                
            except Exception as e:
                logger.error(f"Error processing metrics for {path}: {e}")
        
        # Calculate averages
        if metrics["total_executions"] > 0:
            metrics["avg_duration_seconds"] = total_duration / metrics["total_executions"]
            metrics["avg_steps_per_execution"] = metrics["total_steps"] / metrics["total_executions"]
            
            # Calculate average duration by type
            for exec_type, data in metrics["avg_duration_by_type"].items():
                if data["count"] > 0:
                    metrics["avg_duration_by_type"][exec_type] = data["total"] / data["count"]
        
        return metrics


class ExecutionLogger(BaseLogger):
    """Main class for logging execution details."""
    
    def __init__(
        self,
        log_handler: Optional[ExecutionLogHandler] = None,
        progress_tracker_instance: Optional[ProgressTracker] = None,
        state_manager_instance: Optional[StateManager] = None
    ):
        """Initialize the execution logger.
        
        Args:
            log_handler: Handler for log storage and retrieval
            progress_tracker_instance: Progress tracker for integration
            state_manager_instance: State manager for integration
        """
        super().__init__(name="execution_logger", log_file="logs/execution_logger.log")
        
        self.log_handler = log_handler or ExecutionLogHandler()
        self.progress_tracker = progress_tracker_instance or progress_tracker
        self.state_manager = state_manager_instance or state_manager
        
        # Active execution records
        self.active_executions: Dict[str, ExecutionRecord] = {}
        
        # Execution monitoring
        self.monitor_enabled = False
        self.monitor_interval = 60  # seconds
        self._monitor_task = None
    
    def create_execution(
        self,
        name: str,
        type: str,
        description: str = "",
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """Create a new execution record.
        
        Args:
            name: Name of the execution
            type: Type of execution
            description: Description of the execution
            correlation_id: ID for correlating related executions
            parent_id: Parent execution ID if this is a child execution
            metadata: Additional metadata about the execution
            execution_id: Optional predefined execution ID
            
        Returns:
            ID of the created execution
        """
        # Generate execution ID if not provided
        execution_id = execution_id or f"{type}_{uuid.uuid4()}"
        
        # Create record
        record = ExecutionRecord(
            execution_id=execution_id,
            name=name,
            type=type,
            description=description,
            correlation_id=correlation_id,
            parent_id=parent_id,
            metadata=metadata or {}
        )
        
        # Store in active executions
        self.active_executions[execution_id] = record
        
        # Create progress tracker item if available
        if self.progress_tracker:
            record.progress_id = self.progress_tracker.create_workflow(
                name=f"{type}: {name}",
                description=description,
                total_work=100.0,
                workflow_id=execution_id
            )
        
        # Capture initial state if state manager available
        if self.state_manager:
            record.initial_state = self.state_manager.get_all_variables()
        
        # Log creation
        self.info(
            f"Created execution record: {execution_id} for {type} '{name}'",
            {"execution_id": execution_id, "name": name, "type": type}
        )
        
        return execution_id
    
    def start_execution(self, execution_id: str) -> bool:
        """Start an execution.
        
        Args:
            execution_id: ID of the execution to start
            
        Returns:
            True if execution was started, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot start execution: {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.start()
        
        # Start progress tracking
        if self.progress_tracker and record.progress_id:
            self.progress_tracker.start_item(record.progress_id)
        
        self.info(f"Started execution: {execution_id}")
        return True
    
    def complete_execution(
        self,
        execution_id: str,
        success: bool = True,
        persist: bool = True
    ) -> bool:
        """Complete an execution.
        
        Args:
            execution_id: ID of the execution to complete
            success: Whether the execution was successful
            persist: Whether to persist the execution log
            
        Returns:
            True if execution was completed, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot complete execution: {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        
        # Capture final state if state manager available
        if self.state_manager:
            record.final_state = self.state_manager.get_all_variables()
        
        # Complete execution record
        record.complete(success)
        
        # Update progress tracking
        if self.progress_tracker and record.progress_id:
            if success:
                self.progress_tracker.complete_item(record.progress_id)
            else:
                self.progress_tracker.fail_item(record.progress_id, "Execution failed")
        
        # Persist if requested
        if persist:
            log_path = self.log_handler.store_execution_log(record)
            self.info(f"Execution log saved: {log_path}")
        
        self.info(
            f"Completed execution: {execution_id} (success={success})",
            {
                "execution_id": execution_id,
                "success": success,
                "duration_seconds": record.duration_seconds,
                "total_steps": record.total_steps,
                "failed_steps": record.failed_steps
            }
        )
        
        # Remove from active executions
        del self.active_executions[execution_id]
        
        return True
    
    def abort_execution(
        self,
        execution_id: str,
        reason: str,
        persist: bool = True
    ) -> bool:
        """Abort an execution.
        
        Args:
            execution_id: ID of the execution to abort
            reason: Reason for aborting
            persist: Whether to persist the execution log
            
        Returns:
            True if execution was aborted, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot abort execution: {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        
        # Capture final state if state manager available
        if self.state_manager:
            record.final_state = self.state_manager.get_all_variables()
        
        # Abort execution record
        record.abort(reason)
        
        # Update progress tracking
        if self.progress_tracker and record.progress_id:
            self.progress_tracker.fail_item(
                record.progress_id, 
                f"Execution aborted: {reason}"
            )
        
        # Persist if requested
        if persist:
            log_path = self.log_handler.store_execution_log(record)
            self.info(f"Execution log saved: {log_path}")
        
        self.warning(
            f"Aborted execution: {execution_id} - {reason}",
            {
                "execution_id": execution_id,
                "reason": reason,
                "duration_seconds": record.duration_seconds
            }
        )
        
        # Remove from active executions
        del self.active_executions[execution_id]
        
        return True
    
    def add_execution_event(
        self,
        execution_id: str,
        step_type: ExecutionStepType,
        level: LogLevel,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Add an event to an execution log.
        
        Args:
            execution_id: ID of the execution
            step_type: Type of execution step
            level: Log level of the event
            message: Event message
            data: Additional event data
            
        Returns:
            True if event was added, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot add event: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.add_event(step_type, level, message, data)
        
        # Log to system log based on level
        if level == LogLevel.ERROR:
            self.error(f"[{execution_id}] {message}")
        elif level == LogLevel.WARNING:
            self.warning(f"[{execution_id}] {message}")
        elif level == LogLevel.INFO:
            self.info(f"[{execution_id}] {message}")
        elif level == LogLevel.DEBUG:
            self.debug(f"[{execution_id}] {message}")
        
        return True
    
    def log_step_start(
        self,
        execution_id: str,
        step_id: str,
        step_name: str,
        step_type: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log the start of a step in an execution.
        
        Args:
            execution_id: ID of the execution
            step_id: ID of the step
            step_name: Name of the step
            step_type: Type of the step
            parameters: Parameters for the step
            
        Returns:
            True if step start was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log step start: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_step_start(step_id, step_name, step_type, parameters)
        
        # Create progress tracker item if available
        if self.progress_tracker and record.progress_id:
            self.progress_tracker.create_step(
                workflow_id=record.progress_id,
                name=step_name,
                description=f"{step_type} step",
                step_id=step_id
            )
            self.progress_tracker.start_item(step_id)
        
        self.info(f"[{execution_id}] Started step: {step_name} ({step_type})")
        return True
    
    def log_step_end(
        self,
        execution_id: str,
        step_id: str,
        step_name: str,
        success: bool,
        result: Optional[Any] = None,
        duration_seconds: float = 0.0,
        error: Optional[str] = None
    ) -> bool:
        """Log the end of a step in an execution.
        
        Args:
            execution_id: ID of the execution
            step_id: ID of the step
            step_name: Name of the step
            success: Whether the step was successful
            result: Result of the step
            duration_seconds: Duration of the step
            error: Error that occurred (if any)
            
        Returns:
            True if step end was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log step end: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_step_end(step_id, step_name, success, result, duration_seconds, error)
        
        # Update progress tracker if available
        if self.progress_tracker and step_id:
            if success:
                self.progress_tracker.complete_item(step_id)
            else:
                self.progress_tracker.fail_item(step_id, error or "Step failed")
        
        # Log to system log
        if not success:
            self.error(
                f"[{execution_id}] Failed step: {step_name}",
                {"error": error, "duration": duration_seconds}
            )
        else:
            self.info(
                f"[{execution_id}] Completed step: {step_name}",
                {"duration": duration_seconds}
            )
            
        return True
    
    def log_agent_action(
        self,
        execution_id: str,
        agent_id: str,
        action: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None
    ) -> bool:
        """Log an agent action in an execution.
        
        Args:
            execution_id: ID of the execution
            agent_id: ID of the agent
            action: Action performed by the agent
            input_data: Input data for the action
            output_data: Output data from the action
            duration_seconds: Duration of the action
            error: Error that occurred (if any)
            
        Returns:
            True if agent action was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log agent action: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_agent_action(
            agent_id, action, input_data, output_data, duration_seconds, error
        )
        
        # Log to system log
        if error:
            self.error(
                f"[{execution_id}] Agent {agent_id} {action} failed: {error}",
                {"duration": duration_seconds}
            )
        else:
            self.info(
                f"[{execution_id}] Agent {agent_id}: {action}",
                {"duration": duration_seconds}
            )
            
        return True
    
    def log_tool_call(
        self,
        execution_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Optional[Any] = None,
        duration_seconds: Optional[float] = None,
        error: Optional[str] = None
    ) -> bool:
        """Log a tool call in an execution.
        
        Args:
            execution_id: ID of the execution
            tool_name: Name of the tool
            parameters: Parameters passed to the tool
            result: Result returned by the tool
            duration_seconds: Duration of the tool call
            error: Error that occurred (if any)
            
        Returns:
            True if tool call was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log tool call: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_tool_call(tool_name, parameters, result, duration_seconds, error)
        
        # Log to system log
        if error:
            self.error(
                f"[{execution_id}] Tool {tool_name} failed: {error}",
                {"duration": duration_seconds}
            )
        else:
            self.info(
                f"[{execution_id}] Tool {tool_name} called",
                {"duration": duration_seconds}
            )
            
        return True
    
    def log_llm_usage(
        self,
        execution_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log LLM API usage in an execution.
        
        Args:
            execution_id: ID of the execution
            model: LLM model used
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cost: Estimated cost of the API call
            context: Additional context about the LLM usage
            
        Returns:
            True if LLM usage was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log LLM usage: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_llm_usage(model, prompt_tokens, completion_tokens, cost, context)
        
        self.info(
            f"[{execution_id}] LLM usage: {model} - {prompt_tokens} prompt, {completion_tokens} completion tokens",
            {"cost": cost}
        )
        return True
    
    def log_decision(
        self,
        execution_id: str,
        decision_point: str,
        condition: str,
        result: bool,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log a decision point in an execution.
        
        Args:
            execution_id: ID of the execution
            decision_point: Description of the decision point
            condition: Condition that was evaluated
            result: Result of the condition evaluation
            context: Additional context for the decision
            
        Returns:
            True if decision was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log decision: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_decision(decision_point, condition, result, context)
        
        self.info(
            f"[{execution_id}] Decision: {decision_point} -> {'True' if result else 'False'}",
            {"condition": condition}
        )
        return True
    
    def log_state_change(
        self,
        execution_id: str,
        variable: str,
        old_value: Any,
        new_value: Any,
        source: Optional[str] = None
    ) -> bool:
        """Log a state change in an execution.
        
        Args:
            execution_id: ID of the execution
            variable: Name of the variable
            old_value: Previous value
            new_value: New value
            source: Source of the state change
            
        Returns:
            True if state change was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log state change: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_state_change(variable, old_value, new_value, source)
        
        self.info(
            f"[{execution_id}] State change: {variable} = {new_value}"
        )
        return True
    
    def log_checkpoint(
        self,
        execution_id: str,
        checkpoint_id: str,
        checkpoint_type: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log a checkpoint in an execution.
        
        Args:
            execution_id: ID of the execution
            checkpoint_id: ID of the checkpoint
            checkpoint_type: Type of checkpoint
            data: Additional checkpoint data
            
        Returns:
            True if checkpoint was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log checkpoint: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_checkpoint(checkpoint_id, checkpoint_type, data)
        
        self.info(
            f"[{execution_id}] Created checkpoint: {checkpoint_id} ({checkpoint_type})"
        )
        return True
    
    def log_rollback(
        self,
        execution_id: str,
        checkpoint_id: str,
        reason: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log a rollback in an execution.
        
        Args:
            execution_id: ID of the execution
            checkpoint_id: ID of the checkpoint
            reason: Reason for the rollback
            success: Whether the rollback was successful
            details: Additional rollback details
            
        Returns:
            True if rollback was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log rollback: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_rollback(checkpoint_id, reason, success, details)
        
        if success:
            self.info(
                f"[{execution_id}] Rolled back to checkpoint {checkpoint_id}: {reason}"
            )
        else:
            self.error(
                f"[{execution_id}] Failed to roll back to checkpoint {checkpoint_id}: {reason}"
            )
            
        return True
    
    def log_retry(
        self,
        execution_id: str,
        step_id: str,
        step_name: str,
        attempt: int,
        max_attempts: int,
        reason: str,
        backoff_seconds: Optional[float] = None
    ) -> bool:
        """Log a retry attempt in an execution.
        
        Args:
            execution_id: ID of the execution
            step_id: ID of the step being retried
            step_name: Name of the step
            attempt: Current attempt number
            max_attempts: Maximum number of attempts
            reason: Reason for the retry
            backoff_seconds: Seconds to wait before retry
            
        Returns:
            True if retry was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log retry: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_retry(step_id, step_name, attempt, max_attempts, reason, backoff_seconds)
        
        self.warning(
            f"[{execution_id}] Retrying step {step_name} (attempt {attempt}/{max_attempts}): {reason}",
            {"backoff": backoff_seconds}
        )
        return True
    
    def log_error(
        self,
        execution_id: str,
        error_message: str,
        error_type: Optional[str] = None,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log an error in an execution.
        
        Args:
            execution_id: ID of the execution
            error_message: Error message
            error_type: Type of error
            traceback: Error traceback
            context: Additional context about the error
            
        Returns:
            True if error was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log error: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_error(error_message, error_type, traceback, context)
        
        self.error(
            f"[{execution_id}] Error: {error_message}",
            {"error_type": error_type, "context": context}
        )
        return True
    
    def log_user_input(
        self,
        execution_id: str,
        input_type: str,
        prompt: str,
        response: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log user input in an execution.
        
        Args:
            execution_id: ID of the execution
            input_type: Type of input
            prompt: Prompt shown to user
            response: User's response
            metadata: Additional metadata
            
        Returns:
            True if user input was logged, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot log user input: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        record.log_user_input(input_type, prompt, response, metadata)
        
        self.info(
            f"[{execution_id}] User input ({input_type}): {prompt}"
        )
        return True
    
    def update_progress(
        self,
        execution_id: str,
        progress: float,
        message: Optional[str] = None
    ) -> bool:
        """Update execution progress.
        
        Args:
            execution_id: ID of the execution
            progress: Current progress (0-100)
            message: Optional progress message
            
        Returns:
            True if progress was updated, False otherwise
        """
        if execution_id not in self.active_executions:
            self.error(f"Cannot update progress: execution {execution_id} not found")
            return False
            
        record = self.active_executions[execution_id]
        
        # Update progress tracker if available
        if self.progress_tracker and record.progress_id:
            self.progress_tracker.update_progress(record.progress_id, progress)
            
        # Add progress event
        if message:
            record.add_event(
                ExecutionStepType.CUSTOM,
                LogLevel.INFO,
                f"Progress: {progress:.1f}% - {message}",
                {"progress": progress, "message": message}
            )
        else:
            record.add_event(
                ExecutionStepType.CUSTOM,
                LogLevel.INFO,
                f"Progress: {progress:.1f}%",
                {"progress": progress}
            )
            
        return True
    
    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get an execution record by ID.
        
        Args:
            execution_id: ID of the execution to retrieve
            
        Returns:
            ExecutionRecord if found, None otherwise
        """
        # Check active executions first
        if execution_id in self.active_executions:
            return self.active_executions[execution_id]
            
        # Try to load from storage
        return self.log_handler.get_execution_log(execution_id)
    
    def get_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        execution_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get aggregated execution metrics.
        
        Args:
            start_date: Start date for metrics
            end_date: End date for metrics
            execution_type: Filter by execution type
            
        Returns:
            Dictionary of aggregated metrics
        """
        return self.log_handler.get_execution_metrics(
            start_date=start_date,
            end_date=end_date,
            execution_type=execution_type
        )
    
    def find_executions(
        self,
        name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Find execution logs matching criteria.
        
        Args:
            name: Filter by execution name
            status: Filter by status
            start_date: Filter by start date
            end_date: Filter by end date
            correlation_id: Filter by correlation ID
            limit: Maximum number of results
            
        Returns:
            List of matching execution log summaries
        """
        return self.log_handler.find_execution_logs(
            name=name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            correlation_id=correlation_id,
            limit=limit
        )
    
    async def start_monitoring(self, interval: int = 60):
        """Start background monitoring of active executions.
        
        Args:
            interval: Monitoring interval in seconds
        """
        self.monitor_interval = interval
        self.monitor_enabled = True
        
        import asyncio
        
        async def monitor_loop():
            while self.monitor_enabled:
                try:
                    self._monitor_executions()
                except Exception as e:
                    self.error(f"Error in execution monitor: {e}")
                    
                await asyncio.sleep(self.monitor_interval)
        
        self._monitor_task = asyncio.create_task(monitor_loop())
        self.info("Started execution monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring."""
        self.monitor_enabled = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            self._monitor_task = None
            
        self.info("Stopped execution monitoring")
    
    def _monitor_executions(self):
        """Monitor active executions for timeouts and resource usage."""
        current_time = datetime.utcnow()
        
        # Check each active execution
        for execution_id, record in list(self.active_executions.items()):
            # Only check running executions
            if record.status != ExecutionStatus.RUNNING:
                continue
                
            # Check execution duration
            if record.start_time:
                duration = (current_time - record.start_time).total_seconds()
                
                # Add duration event every 5 minutes
                if int(duration) % 300 < self.monitor_interval:
                    self.info(f"Execution {execution_id} running for {int(duration)} seconds")
                    
                    record.add_event(
                        ExecutionStepType.CUSTOM,
                        LogLevel.DEBUG,
                        f"Execution duration: {int(duration)} seconds",
                        {"duration_seconds": duration}
                    )
                    
            # Check memory usage
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / 1024 / 1024
                
                # Log memory usage
                record.log_memory_usage(memory_mb)
            except ImportError:
                pass  # psutil not available
            except Exception as e:
                self.error(f"Error monitoring memory: {e}")


# Create a global instance for convenience
execution_logger = None

def init_execution_logger(
    progress_tracker_instance=None,
    state_manager_instance=None,
    log_dir="logs/executions"
):
    """Initialize the global execution logger.
    
    Args:
        progress_tracker_instance: Progress tracker for integration
        state_manager_instance: State manager for integration
        log_dir: Directory for storing execution logs
        
    Returns:
        The initialized execution logger
    """
    global execution_logger
    
    if execution_logger is None:
        log_handler = ExecutionLogHandler(base_dir=log_dir)
        
        execution_logger = ExecutionLogger(
            log_handler=log_handler,
            progress_tracker_instance=progress_tracker_instance,
            state_manager_instance=state_manager_instance
        )
        
    return execution_logger


# Context manager for execution logging
class track_execution:
    """Context manager for logging an execution.
    
    Usage:
    ```python
    with track_execution("My Workflow", "workflow", metadata={"key": "value"}) as execution:
        # Log a step
        execution.log_step_start("step1", "Data Processing", "process")
        
        try:
            # Do work...
            result = process_data()
            execution.log_step_end("step1", "Data Processing", True, result, 1.5)
        except Exception as e:
            execution.log_step_end("step1", "Data Processing", False, None, 1.5, str(e))
            raise
    ```
    """
    
    def __init__(
        self,
        name: str,
        type: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        parent_id: Optional[str] = None,
        execution_id: Optional[str] = None,
        auto_start: bool = True
    ):
        """Initialize execution tracking.
        
        Args:
            name: Name of the execution
            type: Type of execution
            description: Description of the execution
            metadata: Additional metadata
            correlation_id: ID for correlating related executions
            parent_id: Parent execution ID if this is a child execution
            execution_id: Optional predefined execution ID
            auto_start: Whether to automatically start execution
        """
        self.name = name
        self.type = type
        self.description = description
        self.metadata = metadata
        self.correlation_id = correlation_id
        self.parent_id = parent_id
        self.execution_id = execution_id
        self.auto_start = auto_start
        self.created_execution_id = None
        
        # Ensure execution logger is initialized
        global execution_logger
        if execution_logger is None:
            from core.progress_tracker import progress_tracker
            from core.state_manager import state_manager
            execution_logger = init_execution_logger(
                progress_tracker_instance=progress_tracker,
                state_manager_instance=state_manager
            )
            
        self.logger = execution_logger
    
    def __enter__(self) -> ExecutionLogger:
        """Enter the context manager and create execution record.
        
        Returns:
            ExecutionLogger instance for the execution
        """
        # Create execution record
        self.created_execution_id = self.logger.create_execution(
            name=self.name,
            type=self.type,
            description=self.description,
            metadata=self.metadata,
            correlation_id=self.correlation_id,
            parent_id=self.parent_id,
            execution_id=self.execution_id
        )
        
        # Auto-start if requested
        if self.auto_start:
            self.logger.start_execution(self.created_execution_id)
            
        # Return logger with execution ID bound
        return self.logger
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and complete execution record."""
        if self.created_execution_id:
            if exc_type is not None:
                # An exception occurred, mark as failed
                error_message = str(exc_val) if exc_val else "Unknown error"
                
                # Log the error
                self.logger.log_error(
                    self.created_execution_id,
                    error_message,
                    error_type=exc_type.__name__,
                    traceback=str(exc_tb)
                )
                
                # Complete as failed
                self.logger.complete_execution(self.created_execution_id, success=False)
            else:
                # No exception, mark as successful
                self.logger.complete_execution(self.created_execution_id, success=True)
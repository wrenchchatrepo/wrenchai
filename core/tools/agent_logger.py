"""Agent activity logging module."""
from typing import Any, Dict, Optional
from uuid import UUID

from core.tools.logger import LoggerConfig, setup_logger

class AgentLogger:
    """Logger for agent activities and operations."""
    
    def __init__(self, agent_id: UUID, log_file: Optional[str] = None):
        """Initialize agent logger.
        
        Args:
            agent_id: Unique identifier for the agent
            log_file: Optional path to agent-specific log file
        """
        self.agent_id = agent_id
        
        # Configure agent-specific logger
        config = LoggerConfig(
            name=f"agent.{agent_id}",
            log_file=log_file or f"logs/agents/{agent_id}.log"
        )
        self.logger = setup_logger(config)
        
    def log_task_start(
        self,
        task_id: UUID,
        task_type: str,
        input_data: Dict[str, Any],
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log task start.
        
        Args:
            task_id: Task identifier
            task_type: Type of task being executed
            input_data: Task input parameters and data
            config: Optional task configuration
        """
        self.logger.info(
            "Task started",
            extra={
                "agent_id": str(self.agent_id),
                "task_id": str(task_id),
                "task_type": task_type,
                "input_data": input_data,
                "config": config
            }
        )
        
    def log_task_progress(
        self,
        task_id: UUID,
        progress: float,
        message: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log task progress.
        
        Args:
            task_id: Task identifier
            progress: Progress percentage (0-100)
            message: Progress description or status message
            metrics: Optional performance metrics
        """
        self.logger.info(
            "Task progress update",
            extra={
                "agent_id": str(self.agent_id),
                "task_id": str(task_id),
                "progress": progress,
                "message": message,
                "metrics": metrics
            }
        )
        
    def log_task_completion(
        self,
        task_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log task completion.
        
        Args:
            task_id: Task identifier
            status: Final task status
            result: Optional task results
            error: Optional error message if task failed
            metrics: Optional performance metrics
        """
        self.logger.info(
            "Task completed",
            extra={
                "agent_id": str(self.agent_id),
                "task_id": str(task_id),
                "status": status,
                "result": result,
                "error": error,
                "metrics": metrics
            }
        )
        
    def log_error(
        self,
        task_id: UUID,
        error: str,
        error_type: Optional[str] = None,
        stack_trace: Optional[str] = None
    ) -> None:
        """Log agent error.
        
        Args:
            task_id: Task identifier
            error: Error message
            error_type: Optional error type/classification
            stack_trace: Optional stack trace
        """
        self.logger.error(
            "Agent error",
            extra={
                "agent_id": str(self.agent_id),
                "task_id": str(task_id),
                "error": error,
                "error_type": error_type,
                "stack_trace": stack_trace
            }
        )
        
    def log_state_change(
        self,
        old_state: Dict[str, Any],
        new_state: Dict[str, Any],
        reason: str
    ) -> None:
        """Log agent state changes.
        
        Args:
            old_state: Previous agent state
            new_state: New agent state
            reason: Reason for state change
        """
        self.logger.info(
            "Agent state changed",
            extra={
                "agent_id": str(self.agent_id),
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason
            }
        )
        
    def log_metric(
        self,
        metric_name: str,
        value: Any,
        task_id: Optional[UUID] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Log agent performance metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            task_id: Optional associated task ID
            labels: Optional metric labels/tags
        """
        self.logger.info(
            "Agent metric",
            extra={
                "agent_id": str(self.agent_id),
                "task_id": str(task_id) if task_id else None,
                "metric": {
                    "name": metric_name,
                    "value": value,
                    "labels": labels
                }
            }
        ) 
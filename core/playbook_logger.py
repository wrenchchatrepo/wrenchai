"""Playbook execution logging module.

This module provides specialized logging for playbook execution,
building on the core execution logging system.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.execution_logger import (
    ExecutionLogger, 
    init_execution_logger, 
    track_execution,
    ExecutionStatus,
    ExecutionStepType
)
from core.progress_tracker import progress_tracker
from core.state_manager import state_manager

# Configure module logger
logger = logging.getLogger(__name__)

class PlaybookExecutionLogger:
    """Specialized logger for playbook execution."""
    
    def __init__(self):
        """Initialize the playbook execution logger."""
        # Ensure execution logger is initialized
        self.execution_logger = init_execution_logger(
            progress_tracker_instance=progress_tracker,
            state_manager_instance=state_manager
        )
    
    def start_playbook_execution(self, 
                               playbook_id: str,
                               playbook_name: str,
                               playbook_description: str = "",
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """Start logging a playbook execution.
        
        Args:
            playbook_id: Unique ID for the playbook execution
            playbook_name: Name of the playbook
            playbook_description: Description of the playbook
            metadata: Additional metadata for the execution
            
        Returns:
            Execution ID for the playbook execution
        """
        metadata = metadata or {}
        metadata.update({
            "playbook_id": playbook_id,
            "playbook_name": playbook_name,
            "started_at": datetime.utcnow().isoformat()
        })
        
        execution_id = self.execution_logger.create_execution(
            name=playbook_name,
            type="playbook",
            description=playbook_description,
            metadata=metadata,
            execution_id=f"playbook_{playbook_id}"
        )
        
        self.execution_logger.start_execution(execution_id)
        logger.info(f"Started logging playbook execution: {playbook_name} ({playbook_id})")
        return execution_id
    
    def log_step_execution(self,
                        execution_id: str,
                        step_id: str,
                        step_name: str,
                        step_type: str,
                        status: str = "running",
                        step_data: Optional[Dict[str, Any]] = None):
        """Log a playbook step execution.
        
        Args:
            execution_id: ID of the playbook execution
            step_id: Unique ID for the step
            step_name: Name of the step
            step_type: Type of step being executed
            status: Current status of the step
            step_data: Additional data for the step
        """
        step_data = step_data or {}
        
        if status == "started":
            self.execution_logger.log_step_start(
                execution_id=execution_id,
                step_id=step_id,
                step_name=step_name,
                step_type=step_type,
                step_data=step_data
            )
            logger.info(f"Started step {step_name} ({step_id}) in playbook execution {execution_id}")
        elif status in ["completed", "failed"]:
            success = status == "completed"
            result = step_data.get("result")
            error = step_data.get("error")
            duration = step_data.get("duration_seconds", 0)
            
            self.execution_logger.log_step_end(
                execution_id=execution_id,
                step_id=step_id,
                step_name=step_name,
                success=success,
                result=result,
                duration_seconds=duration,
                error_message=error
            )
            
            if success:
                logger.info(f"Completed step {step_name} ({step_id}) in playbook execution {execution_id}")
            else:
                logger.error(f"Failed step {step_name} ({step_id}) in playbook execution {execution_id}: {error}")
    
    def log_agent_execution(self,
                          execution_id: str,
                          agent_id: str,
                          agent_type: str,
                          action: str,
                          input_data: Optional[Dict[str, Any]] = None,
                          output_data: Optional[Dict[str, Any]] = None,
                          duration_seconds: float = 0):
        """Log an agent action during playbook execution.
        
        Args:
            execution_id: ID of the playbook execution
            agent_id: ID of the agent
            agent_type: Type of agent
            action: Action performed by the agent
            input_data: Input data for the agent
            output_data: Output data from the agent
            duration_seconds: Duration of the agent action
        """
        self.execution_logger.log_agent_action(
            execution_id=execution_id,
            agent_id=str(agent_id),
            agent_type=agent_type,
            action=action,
            input_data=input_data,
            output_data=output_data,
            duration_seconds=duration_seconds
        )
        
        logger.info(f"Agent {agent_type} ({agent_id}) performed {action} in playbook execution {execution_id}")
    
    def log_tool_usage(self,
                     execution_id: str,
                     tool_name: str,
                     inputs: Optional[Dict[str, Any]] = None,
                     outputs: Optional[Dict[str, Any]] = None,
                     success: bool = True,
                     error: Optional[str] = None,
                     duration_seconds: float = 0):
        """Log a tool usage during playbook execution.
        
        Args:
            execution_id: ID of the playbook execution
            tool_name: Name of the tool
            inputs: Input parameters for the tool
            outputs: Output data from the tool
            success: Whether the tool execution was successful
            error: Error message if tool execution failed
            duration_seconds: Duration of the tool execution
        """
        self.execution_logger.log_tool_call(
            execution_id=execution_id,
            tool_name=tool_name,
            inputs=inputs,
            outputs=outputs,
            success=success,
            error_message=error,
            duration_seconds=duration_seconds
        )
        
        if success:
            logger.info(f"Tool {tool_name} used in playbook execution {execution_id}")
        else:
            logger.error(f"Tool {tool_name} failed in playbook execution {execution_id}: {error}")
    
    def log_llm_usage(self,
                    execution_id: str,
                    model_name: str,
                    prompt_tokens: int,
                    completion_tokens: int,
                    total_tokens: int,
                    cost: float = 0,
                    context: Optional[str] = None):
        """Log LLM usage during playbook execution.
        
        Args:
            execution_id: ID of the playbook execution
            model_name: Name of the LLM model
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            total_tokens: Total tokens used
            cost: Cost of the LLM call
            context: Context for the LLM call
        """
        self.execution_logger.log_llm_usage(
            execution_id=execution_id,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost=cost,
            context=context
        )
        
        logger.info(f"LLM {model_name} used in playbook execution {execution_id}: {total_tokens} tokens")
    
    def complete_playbook_execution(self,
                                   execution_id: str,
                                   success: bool = True,
                                   result: Optional[Dict[str, Any]] = None,
                                   error: Optional[str] = None):
        """Complete a playbook execution log.
        
        Args:
            execution_id: ID of the playbook execution
            success: Whether the execution was successful
            result: Result data from the execution
            error: Error message if execution failed
        """
        result_data = result or {}
        if error:
            self.execution_logger.log_error(
                execution_id=execution_id,
                error_message=error
            )
        
        self.execution_logger.complete_execution(
            execution_id=execution_id,
            success=success,
            result=result_data
        )
        
        if success:
            logger.info(f"Completed playbook execution {execution_id} successfully")
        else:
            logger.error(f"Playbook execution {execution_id} failed: {error}")
    
    def get_playbook_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the execution record for a playbook.
        
        Args:
            execution_id: ID of the playbook execution
            
        Returns:
            Execution record or None if not found
        """
        return self.execution_logger.get_execution(execution_id)
    
    def query_playbook_executions(self,
                                name: Optional[str] = None,
                                status: Optional[str] = None,
                                start_time: Optional[datetime] = None,
                                end_time: Optional[datetime] = None,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Query playbook executions based on criteria.
        
        Args:
            name: Filter by playbook name
            status: Filter by execution status
            start_time: Filter by minimum start time
            end_time: Filter by maximum start time
            limit: Maximum number of results to return
            
        Returns:
            List of matching execution records
        """
        return self.execution_logger.find_executions(
            execution_type="playbook",
            name=name,
            status=status,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
    
    def get_playbook_execution_metrics(self, execution_id: str) -> Dict[str, Any]:
        """Get metrics for a playbook execution.
        
        Args:
            execution_id: ID of the playbook execution
            
        Returns:
            Dictionary of execution metrics
        """
        return self.execution_logger.get_metrics(execution_id)

# Initialize global instance
playbook_logger = PlaybookExecutionLogger()

# Context manager for playbook execution tracking
class track_playbook_execution:
    """Context manager for tracking playbook execution.
    
    Usage:
    ```python
    with track_playbook_execution(playbook_id, playbook_name, metadata={"key": "value"}) as execution_id:
        # Log a step
        playbook_logger.log_step_execution(execution_id, "step1", "Process Data", "process", "started")
        try:
            # Execute step
            result = process_data()
            playbook_logger.log_step_execution(
                execution_id, "step1", "Process Data", "process", "completed", 
                {"result": result, "duration_seconds": 1.5}
            )
        except Exception as e:
            playbook_logger.log_step_execution(
                execution_id, "step1", "Process Data", "process", "failed", 
                {"error": str(e), "duration_seconds": 1.5}
            )
            raise
    ```
    """
    
    def __init__(self,
               playbook_id: str,
               playbook_name: str,
               playbook_description: str = "",
               metadata: Optional[Dict[str, Any]] = None):
        """Initialize playbook execution tracking.
        
        Args:
            playbook_id: Unique ID for the playbook execution
            playbook_name: Name of the playbook
            playbook_description: Description of the playbook
            metadata: Additional metadata for the execution
        """
        self.playbook_id = playbook_id
        self.playbook_name = playbook_name
        self.playbook_description = playbook_description
        self.metadata = metadata
        self.execution_id = None
    
    def __enter__(self) -> str:
        """Enter the context manager and start playbook execution logging.
        
        Returns:
            Execution ID for the playbook execution
        """
        self.execution_id = playbook_logger.start_playbook_execution(
            playbook_id=self.playbook_id,
            playbook_name=self.playbook_name,
            playbook_description=self.playbook_description,
            metadata=self.metadata
        )
        return self.execution_id
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and complete playbook execution logging."""
        if self.execution_id:
            if exc_type is not None:
                # An exception occurred, mark as failed
                error_message = str(exc_val) if exc_val else "Unknown error"
                playbook_logger.complete_playbook_execution(
                    execution_id=self.execution_id,
                    success=False,
                    error=error_message
                )
            else:
                # No exception, mark as successful
                playbook_logger.complete_playbook_execution(
                    execution_id=self.execution_id,
                    success=True
                )
"""Execution Service for the WrenchAI Streamlit application.

This module provides services for managing and monitoring playbook executions.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, TypeVar
from datetime import datetime

from streamlit_app.services.api_client import ApiClient, ResourceClient, ApiError
from streamlit_app.models.playbook_config import ExecutionResult, ExecutionState

logger = logging.getLogger(__name__)


class ExecutionService:
    """Service for execution-related operations."""
    
    def __init__(self, api_client: ApiClient):
        """Initialize the execution service.
        
        Args:
            api_client: API client for making requests
        """
        self.api_client = api_client
        self.resource_client = ResourceClient(
            api_client=api_client,
            resource_path="api/executions",
            response_model=self._parse_execution
        )
    
    def _parse_execution(self, data: Dict[str, Any]) -> ExecutionResult:
        """Parse an execution result from API response data.
        
        Args:
            data: API response data
            
        Returns:
            Parsed ExecutionResult
        """
        try:
            # Try to parse as ExecutionResult
            return ExecutionResult.model_validate(data)
        except Exception as e:
            logger.warning(f"Error parsing execution result, falling back to minimal parsing: {e}")
            # Fall back to minimal parsing
            return ExecutionResult(
                execution_id=data.get("execution_id", ""),
                playbook_id=data.get("playbook_id", ""),
                state=data.get("state", ExecutionState.IDLE),
                start_time=datetime.now(),
                success=data.get("success", False),
                outputs=data.get("outputs", {}),
                logs=data.get("logs", [])
            )
    
    async def list_executions(self, 
                            playbook_id: Optional[str] = None,
                            state: Optional[str] = None,
                            limit: int = 10,
                            offset: int = 0) -> List[ExecutionResult]:
        """List playbook executions.
        
        Args:
            playbook_id: Optional playbook ID to filter by
            state: Optional execution state to filter by
            limit: Maximum number of results to return
            offset: Offset for pagination
            
        Returns:
            List of execution results
            
        Raises:
            ApiError: If the request fails
        """
        params = {"limit": limit, "offset": offset}
        if playbook_id:
            params["playbook_id"] = playbook_id
        if state:
            params["state"] = state
        
        try:
            return await self.resource_client.list(params=params)
        except ApiError as e:
            logger.error(f"Error listing executions: {e}")
            raise
    
    async def get_execution(self, execution_id: str) -> ExecutionResult:
        """Get a specific execution by ID.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            Execution result
            
        Raises:
            ApiError: If the request fails
        """
        try:
            return await self.resource_client.get(execution_id)
        except ApiError as e:
            logger.error(f"Error getting execution {execution_id}: {e}")
            raise
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution.
        
        Args:
            execution_id: Execution ID
            
        Returns:
            True if canceled successfully
            
        Raises:
            ApiError: If the request fails
        """
        try:
            response = await self.api_client.post(
                endpoint=f"api/executions/{execution_id}/cancel"
            )
            
            data = response.json()
            return data.get("success", False)
        except ApiError as e:
            logger.error(f"Error canceling execution {execution_id}: {e}")
            raise
    
    async def get_execution_logs(self, execution_id: str, 
                                from_line: int = 0,
                                limit: int = 100) -> List[Dict[str, Any]]:
        """Get logs for a specific execution.
        
        Args:
            execution_id: Execution ID
            from_line: Line number to start from
            limit: Maximum number of log lines to return
            
        Returns:
            List of log entries
            
        Raises:
            ApiError: If the request fails
        """
        try:
            response = await self.api_client.get(
                endpoint=f"api/executions/{execution_id}/logs",
                params={"from": from_line, "limit": limit}
            )
            
            data = response.json()
            return data.get("logs", [])
        except ApiError as e:
            logger.error(f"Error getting logs for execution {execution_id}: {e}")
            raise
    
    async def get_execution_output(self, execution_id: str, output_key: Optional[str] = None) -> Any:
        """Get output for a specific execution.
        
        Args:
            execution_id: Execution ID
            output_key: Optional specific output key to retrieve
            
        Returns:
            Execution output or specific output value
            
        Raises:
            ApiError: If the request fails
        """
        try:
            # Get the execution result
            execution = await self.get_execution(execution_id)
            
            # Return specific output or all outputs
            if output_key and execution.outputs:
                return execution.outputs.get(output_key)
            else:
                return execution.outputs
        except ApiError as e:
            logger.error(f"Error getting output for execution {execution_id}: {e}")
            raise
    
    async def watch_execution(self, execution_id: str, callback, interval_seconds: float = 1.0, max_attempts: int = 300):
        """Watch an execution until it completes or fails.
        
        Args:
            execution_id: Execution ID
            callback: Callback function to call with execution status
            interval_seconds: Polling interval in seconds
            max_attempts: Maximum number of polling attempts
            
        Returns:
            Final execution result
            
        Raises:
            ApiError: If the request fails
            TimeoutError: If max_attempts is reached
        """
        import asyncio
        
        attempts = 0
        previous_state = None
        
        while attempts < max_attempts:
            try:
                # Get current execution status
                execution = await self.get_execution(execution_id)
                
                # Call callback if state changed
                if execution.state != previous_state:
                    callback(execution)
                    previous_state = execution.state
                
                # Check if execution is complete
                if execution.state in [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELED]:
                    return execution
                
                # Wait before polling again
                await asyncio.sleep(interval_seconds)
                attempts += 1
                
            except ApiError as e:
                logger.error(f"Error watching execution {execution_id}: {e}")
                # Wait before retrying
                await asyncio.sleep(interval_seconds * 2)
                attempts += 1
        
        # If we got here, we exceeded max_attempts
        raise TimeoutError(f"Execution watch timed out after {max_attempts} attempts")
"""
API routes for tool operations.

This module provides standardized endpoints for working with tools,
including listing available tools, getting tool details, health checking, 
and executing tools with appropriate input validation.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import uuid

from core.schemas.responses import create_response, error_response, paginated_response
from core.schemas.requests import ToolExecuteRequest, Project

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/tools", tags=["tools"])

# Configuration directory
CONFIG_DIR = os.getenv("CONFIG_DIR", "core/configs")

# In-memory tool registry
# In production, this should be replaced with a database
tool_registry: Dict[str, Dict[str, Any]] = {}
tool_executions: Dict[str, Dict[str, Any]] = {}

class ToolValidator:
    """Dependency for tool validation operations."""
    
    def __init__(self):
        """Initialize tool validator."""
        self.config_dir = CONFIG_DIR
    
    async def validate_tool_input(self, tool_id: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate tool input based on tool specifications.
        
        Args:
            tool_id: ID of the tool
            input_data: Tool input data
            
        Returns:
            Validation result
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Check if tool exists
            if tool_id not in tool_registry:
                return {
                    "valid": False,
                    "errors": [f"Tool not found: {tool_id}"]
                }
            
            tool_data = tool_registry[tool_id]
            
            # Basic existence validation
            if "input_schema" not in tool_data:
                # No schema to validate against
                return {"valid": True}
            
            # Get required fields from schema
            required_fields = tool_data["input_schema"].get("required", [])
            properties = tool_data["input_schema"].get("properties", {})
            
            # Check if all required fields are present
            missing_fields = [field for field in required_fields if field not in input_data]
            if missing_fields:
                return {
                    "valid": False,
                    "errors": [f"Missing required fields: {', '.join(missing_fields)}"]
                }
            
            # Validate field types (basic validation)
            type_errors = []
            for field, value in input_data.items():
                if field in properties:
                    field_type = properties[field].get("type")
                    if field_type:
                        # Basic type checking
                        if field_type == "string" and not isinstance(value, str):
                            type_errors.append(f"Field '{field}' should be a string")
                        elif field_type == "number" and not isinstance(value, (int, float)):
                            type_errors.append(f"Field '{field}' should be a number")
                        elif field_type == "integer" and not isinstance(value, int):
                            type_errors.append(f"Field '{field}' should be an integer")
                        elif field_type == "boolean" and not isinstance(value, bool):
                            type_errors.append(f"Field '{field}' should be a boolean")
                        elif field_type == "array" and not isinstance(value, list):
                            type_errors.append(f"Field '{field}' should be an array")
                        elif field_type == "object" and not isinstance(value, dict):
                            type_errors.append(f"Field '{field}' should be an object")
            
            if type_errors:
                return {
                    "valid": False,
                    "errors": type_errors
                }
            
            # All checks passed
            return {"valid": True}
                
        except Exception as e:
            logger.error(f"Error validating tool input: {str(e)}")
            return {
                "valid": False,
                "errors": [str(e)]
            }

@router.get("/list", response_model=Dict[str, Any])
async def list_tools(
    category: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> JSONResponse:
    """List available tools with optional filtering.
    
    Args:
        category: Filter by tool category
        page: Page number for pagination
        limit: Number of items per page
        
    Returns:
        List of tools
    """
    try:
        # Filter tools
        filtered_tools = tool_registry.values()
        
        if category:
            filtered_tools = [t for t in filtered_tools if t.get("category") == category]
            
        # Sort by name
        sorted_tools = sorted(
            filtered_tools,
            key=lambda t: t.get("name", "")
        )
        
        # Paginate results
        total_count = len(sorted_tools)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_tools = sorted_tools[start_idx:end_idx]
        
        return JSONResponse(
            content=paginated_response(
                success=True,
                message=f"Found {total_count} tools",
                items=paginated_tools,
                total_count=total_count,
                page=page,
                page_size=limit
            )
        )
        
    except Exception as e:
        logger.error(f"Error listing tools: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to list tools",
                code="TOOL_LIST_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/{tool_id}", response_model=Dict[str, Any])
async def get_tool(tool_id: str) -> JSONResponse:
    """Get tool details by ID.
    
    Args:
        tool_id: Tool ID
        
    Returns:
        Tool details
    """
    try:
        # Check if tool exists
        if tool_id not in tool_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Tool not found: {tool_id}",
                    code="TOOL_NOT_FOUND"
                )
            )
            
        # Return tool details
        return JSONResponse(
            content=create_response(
                success=True,
                message="Tool found",
                data=tool_registry[tool_id]
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting tool {tool_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to get tool",
                code="TOOL_RETRIEVAL_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/{tool_id}/health", response_model=Dict[str, Any])
async def check_tool_health(tool_id: str) -> JSONResponse:
    """Check health/status of a tool.
    
    Args:
        tool_id: Tool ID
        
    Returns:
        Tool health status
    """
    try:
        # Check if tool exists
        if tool_id not in tool_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Tool not found: {tool_id}",
                    code="TOOL_NOT_FOUND"
                )
            )
            
        tool_data = tool_registry[tool_id]
        
        # In a real implementation, you would perform actual health checks
        # Here we just simulate a health check
        health_status = {
            "status": "healthy",
            "last_checked": datetime.utcnow().isoformat(),
            "version": tool_data.get("version", "unknown"),
            "latency_ms": 50,  # Simulated latency
            "uptime": "99.9%"  # Simulated uptime
        }
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Tool health check completed",
                data=health_status
            )
        )
        
    except Exception as e:
        logger.error(f"Error checking tool health {tool_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to check tool health",
                code="TOOL_HEALTH_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/{tool_id}/execute", response_model=Dict[str, Any])
async def execute_tool(
    tool_id: str,
    request: ToolExecuteRequest,
    background_tasks: BackgroundTasks,
    validator: ToolValidator = Depends(ToolValidator)
) -> JSONResponse:
    """Execute a tool with provided input.
    
    Args:
        tool_id: Tool ID
        request: Tool execution request
        background_tasks: FastAPI background tasks
        validator: Tool validator dependency
        
    Returns:
        Tool execution response
    """
    try:
        # Check if tool exists
        if tool_id not in tool_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Tool not found: {tool_id}",
                    code="TOOL_NOT_FOUND"
                )
            )
            
        # Validate input
        validation_result = await validator.validate_tool_input(
            tool_id=tool_id,
            input_data=request.input
        )
        
        if not validation_result.get("valid", False):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Invalid tool input",
                    code="INVALID_TOOL_INPUT",
                    details=validation_result
                )
            )
            
        # Generate execution ID
        execution_id = f"exec_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Initialize execution record
        tool_executions[execution_id] = {
            "id": execution_id,
            "tool_id": tool_id,
            "input": request.input,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": request.metadata
        }
        
        # Schedule execution in background
        background_tasks.add_task(
            _execute_tool_background,
            execution_id=execution_id,
            tool_id=tool_id,
            input_data=request.input
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=create_response(
                success=True,
                message="Tool execution started",
                data={
                    "execution_id": execution_id,
                    "tool_id": tool_id,
                    "status": "pending",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error executing tool {tool_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to execute tool",
                code="TOOL_EXECUTION_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/executions/{execution_id}", response_model=Dict[str, Any])
async def get_execution_status(execution_id: str) -> JSONResponse:
    """Get status of a tool execution.
    
    Args:
        execution_id: Execution ID
        
    Returns:
        Execution status
    """
    try:
        # Check if execution exists
        if execution_id not in tool_executions:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Execution not found: {execution_id}",
                    code="EXECUTION_NOT_FOUND"
                )
            )
            
        # Return execution details
        return JSONResponse(
            content=create_response(
                success=True,
                message="Execution found",
                data=tool_executions[execution_id]
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting execution {execution_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to get execution",
                code="EXECUTION_RETRIEVAL_ERROR",
                details={"error": str(e)}
            )
        )

# Background task implementations

async def _execute_tool_background(
    execution_id: str,
    tool_id: str,
    input_data: Dict[str, Any]
) -> None:
    """Execute tool in background.
    
    Args:
        execution_id: Execution ID
        tool_id: Tool ID
        input_data: Tool input data
    """
    try:
        # Update status to running
        if execution_id in tool_executions:
            tool_executions[execution_id]["status"] = "running"
            tool_executions[execution_id]["started_at"] = datetime.utcnow().isoformat()
        
        # Simulate tool execution
        # In a real implementation, this would invoke the actual tool
        import asyncio
        
        # Simulate processing with different steps
        total_steps = 3
        for i in range(total_steps):
            if execution_id in tool_executions:
                tool_executions[execution_id]["progress"] = {
                    "steps_total": total_steps,
                    "steps_completed": i,
                    "current_step": f"Step {i+1}",
                    "percentage_complete": int((i / total_steps) * 100)
                }
            
            # Simulate step execution
            await asyncio.sleep(1)
        
        # Finalize execution
        if execution_id in tool_executions:
            tool_executions[execution_id]["status"] = "completed"
            tool_executions[execution_id]["completed_at"] = datetime.utcnow().isoformat()
            
            # Generate mock result based on tool type
            tool_data = tool_registry.get(tool_id, {})
            tool_type = tool_data.get("type", "generic")
            
            if tool_type == "analyzer":
                result = {
                    "analysis_result": "Mock analysis completed successfully",
                    "metrics": {
                        "accuracy": 0.95,
                        "confidence": 0.87
                    }
                }
            elif tool_type == "transformer":
                result = {
                    "transformed_data": "Mock transformation completed successfully",
                    "transformation_details": {
                        "records_processed": 1000,
                        "records_transformed": 950
                    }
                }
            else:
                result = {
                    "result": "Mock execution completed successfully",
                    "details": {
                        "processed": True,
                        "execution_time_ms": 1500
                    }
                }
            
            tool_executions[execution_id]["result"] = result
    
    except Exception as e:
        logger.error(f"Error executing tool {tool_id}: {str(e)}")
        
        # Update execution status
        if execution_id in tool_executions:
            tool_executions[execution_id]["status"] = "failed"
            tool_executions[execution_id]["error"] = str(e)
            tool_executions[execution_id]["completed_at"] = datetime.utcnow().isoformat()
"""
API routes for playbook operations.

This module provides standardized endpoints for working with playbooks,
including validation, execution, and status checking.
"""

import os
import logging
import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from datetime import datetime
import time
import yaml
import uuid

from core.schemas.responses import create_response, error_response
from core.schemas.requests import PlaybookExecuteRequest, Project
from core.playbook_validator import validate_playbook_from_yaml, perform_full_validation
from core.condition_evaluator import analyze_playbook_conditions

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/playbooks", tags=["playbooks"])

# Configuration directory
CONFIG_DIR = os.getenv("CONFIG_DIR", "core/configs")

# In-memory task status storage
# In production, this should be replaced with a database
playbook_runs: Dict[str, Dict[str, Any]] = {}

class PlaybookValidator:
    """Dependency for playbook validation operations."""
    
    def __init__(self):
        """Initialize playbook validator."""
        self.config_dir = CONFIG_DIR
        
    async def get_playbook_path(self, playbook_name: str) -> str:
        """Get path to playbook file.
        
        Args:
            playbook_name: Name of the playbook
            
        Returns:
            Path to playbook file
            
        Raises:
            HTTPException: If playbook not found
        """
        # Normalize playbook name
        if playbook_name.endswith(".yaml") or playbook_name.endswith(".yml"):
            base_name = os.path.splitext(playbook_name)[0]
        else:
            base_name = playbook_name
            
        # Try different extensions
        for ext in [".yaml", ".yml"]:
            playbook_path = os.path.join(self.config_dir, "playbooks", f"{base_name}{ext}")
            if os.path.exists(playbook_path):
                return playbook_path
                
        # Playbook not found
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Playbook not found: {playbook_name}"
        )
    
    async def read_playbook(self, playbook_path: str) -> str:
        """Read playbook content from file.
        
        Args:
            playbook_path: Path to playbook file
            
        Returns:
            Playbook content
            
        Raises:
            HTTPException: If file cannot be read
        """
        try:
            with open(playbook_path, 'r') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read playbook: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to read playbook: {str(e)}"
            )
    
    async def validate_playbook(self, playbook_content: str) -> Dict[str, Any]:
        """Validate playbook content.
        
        Args:
            playbook_content: Playbook content
            
        Returns:
            Validation result
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            valid, error = validate_playbook_from_yaml(playbook_content)
            
            if not valid:
                return {
                    "valid": False,
                    "errors": [error]
                }
                
            # Parse playbook to analyze conditions
            try:
                playbook_dict = yaml.safe_load(playbook_content)
                conditions_analysis = analyze_playbook_conditions(playbook_dict)
                
                return {
                    "valid": True,
                    "conditions": conditions_analysis
                }
            except Exception as e:
                logger.error(f"Error analyzing conditions: {str(e)}")
                return {
                    "valid": True,
                    "conditions": {
                        "error": str(e)
                    }
                }
                
        except Exception as e:
            logger.error(f"Error validating playbook: {str(e)}")
            return {
                "valid": False,
                "errors": [str(e)]
            }

@router.post("/validate", response_model=Dict[str, Any])
async def validate_playbook(
    request: Dict[str, Any],
    validator: PlaybookValidator = Depends(PlaybookValidator)
) -> JSONResponse:
    """Validate a playbook without executing it.
    
    Args:
        request: Validation request
        validator: Playbook validator dependency
        
    Returns:
        Validation result
    """
    try:
        # Check request format
        if "playbook" not in request and "content" not in request:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Request must contain either 'playbook' name or 'content'",
                    code="MISSING_FIELD"
                )
            )
            
        # Validate from name or content
        if "playbook" in request:
            playbook_path = await validator.get_playbook_path(request["playbook"])
            playbook_content = await validator.read_playbook(playbook_path)
        else:
            playbook_content = request["content"]
            
        # Validate playbook
        validation_result = await validator.validate_playbook(playbook_content)
        
        if validation_result["valid"]:
            return JSONResponse(
                content=create_response(
                    success=True,
                    message="Playbook validation successful",
                    data=validation_result
                )
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Playbook validation failed",
                    code="VALIDATION_ERROR",
                    details=validation_result
                )
            )
            
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error validating playbook: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to validate playbook",
                code="VALIDATION_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/execute", response_model=Dict[str, Any])
async def execute_playbook(
    request: PlaybookExecuteRequest,
    background_tasks: BackgroundTasks,
    validator: PlaybookValidator = Depends(PlaybookValidator)
) -> JSONResponse:
    """Execute a playbook asynchronously.
    
    Args:
        request: Execution request
        background_tasks: FastAPI background tasks
        validator: Playbook validator dependency
        
    Returns:
        Execution response with run ID
    """
    try:
        # Validate playbook exists
        try:
            playbook_path = await validator.get_playbook_path(request.playbook_name)
        except HTTPException:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Playbook not found: {request.playbook_name}",
                    code="PLAYBOOK_NOT_FOUND"
                )
            )
            
        # Validate playbook content
        playbook_content = await validator.read_playbook(playbook_path)
        validation_result = await validator.validate_playbook(playbook_content)
        
        if not validation_result["valid"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Invalid playbook",
                    code="INVALID_PLAYBOOK",
                    details=validation_result
                )
            )
            
        # Generate a unique run ID
        run_id = f"run_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Initialize run status
        playbook_runs[run_id] = {
            "run_id": run_id,
            "status": "pending",
            "playbook": request.playbook_name,
            "parameters": request.parameters,
            "start_time": datetime.utcnow().isoformat(),
            "project": request.project.dict()
        }
        
        # Schedule background execution (mock for now)
        background_tasks.add_task(
            _execute_playbook_background,
            run_id=run_id,
            playbook_name=request.playbook_name,
            playbook_path=playbook_path,
            parameters=request.parameters,
            project=request.project.dict()
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=create_response(
                success=True,
                message="Playbook execution started",
                data={
                    "run_id": run_id,
                    "status": "pending",
                    "playbook": request.playbook_name,
                    "start_time": datetime.utcnow().isoformat()
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error starting playbook execution: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to start playbook execution",
                code="EXECUTION_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/status/{run_id}", response_model=Dict[str, Any])
async def get_execution_status(run_id: str) -> JSONResponse:
    """Get status of playbook execution.
    
    Args:
        run_id: Execution run ID
        
    Returns:
        Execution status
    """
    try:
        # Check if run exists
        if run_id not in playbook_runs:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Run not found: {run_id}",
                    code="RUN_NOT_FOUND"
                )
            )
            
        # Return run status
        return JSONResponse(
            content=create_response(
                success=True,
                message="Execution status retrieved",
                data=playbook_runs[run_id]
            )
        )
        
    except Exception as e:
        logger.error(f"Error retrieving execution status: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to retrieve execution status",
                code="STATUS_ERROR",
                details={"error": str(e)}
            )
        )

async def _execute_playbook_background(
    run_id: str,
    playbook_name: str,
    playbook_path: str,
    parameters: Dict[str, Any],
    project: Dict[str, Any]
) -> None:
    """Execute playbook in background task (mock).
    
    Args:
        run_id: Execution run ID
        playbook_name: Playbook name
        playbook_path: Path to playbook file
        parameters: Playbook parameters
        project: Project configuration
    """
    try:
        # Update status to running
        playbook_runs[run_id]["status"] = "running"
        
        # Simulate execution steps
        total_steps = 5
        for i in range(total_steps):
            # Update progress
            playbook_runs[run_id]["progress"] = {
                "steps_total": total_steps,
                "steps_completed": i,
                "current_step": f"Step {i+1}",
                "percentage_complete": int((i / total_steps) * 100)
            }
            
            # Simulate step execution
            await asyncio.sleep(1)
            
        # Mark as completed
        playbook_runs[run_id]["status"] = "completed"
        playbook_runs[run_id]["end_time"] = datetime.utcnow().isoformat()
        playbook_runs[run_id]["result"] = {
            "success": True,
            "output": "Playbook execution completed successfully (mock)"
        }
        
    except Exception as e:
        logger.error(f"Error executing playbook: {str(e)}")
        
        # Mark as failed
        if run_id in playbook_runs:
            playbook_runs[run_id]["status"] = "failed"
            playbook_runs[run_id]["end_time"] = datetime.utcnow().isoformat()
            playbook_runs[run_id]["error"] = str(e)
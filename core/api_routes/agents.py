"""
API routes for agent operations.

This module provides standardized endpoints for working with agents,
including creation, configuration, status management, and task assignment.
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
from core.schemas.requests import AgentCreateRequest, Project, AgentType
from core.agents.agent_definitions import get_agent, get_agents_by_type, get_agents_by_capability
from core.agents.agent_factory import AgentFactory
from core.agents.agent_state import agent_state_manager

# Set up logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/agents", tags=["agents"])

# Configuration directory
CONFIG_DIR = os.getenv("CONFIG_DIR", "core/configs")

# In-memory agent registry
# In production, this should be replaced with a database
agent_registry: Dict[str, Dict[str, Any]] = {}

class AgentValidator:
    """Dependency for agent validation operations."""
    
    def __init__(self):
        """Initialize agent validator."""
        self.config_dir = CONFIG_DIR
    
    async def validate_agent_config(self, agent_type: AgentType, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent configuration based on agent type.
        
        Args:
            agent_type: Type of the agent
            config: Agent configuration
            
        Returns:
            Validation result
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Validate based on agent type
            if agent_type == AgentType.CUSTOM and 'implementation' not in config:
                return {
                    "valid": False,
                    "errors": ["Custom agent type requires 'implementation' in config"]
                }
                
            # Each agent type may have specific validation rules
            # SUPER agent validation
            if agent_type == AgentType.SUPER:
                # Basic validation for now
                return {"valid": True}
                
            # INSPECTOR agent validation
            elif agent_type == AgentType.INSPECTOR:
                if 'review_standards' not in config:
                    return {
                        "valid": False,
                        "errors": ["Inspector agent requires 'review_standards' in config"]
                    }
                return {"valid": True}
                
            # JOURNEY agent validation
            elif agent_type == AgentType.JOURNEY:
                if 'repository_access' not in config:
                    return {
                        "valid": False,
                        "errors": ["Journey agent requires 'repository_access' in config"]
                    }
                return {"valid": True}
                
            # CODIFIER agent validation
            elif agent_type == AgentType.CODIFIER:
                if 'language_standards' not in config:
                    return {
                        "valid": False,
                        "errors": ["Codifier agent requires 'language_standards' in config"]
                    }
                return {"valid": True}
                
            # UX_DESIGNER agent validation
            elif agent_type == AgentType.UX_DESIGNER:
                if 'design_system' not in config:
                    return {
                        "valid": False,
                        "errors": ["UX Designer agent requires 'design_system' in config"]
                    }
                return {"valid": True}
                
            # TEST_ENGINEER agent validation
            elif agent_type == AgentType.TEST_ENGINEER:
                if 'testing_framework' not in config:
                    return {
                        "valid": False,
                        "errors": ["Test Engineer agent requires 'testing_framework' in config"]
                    }
                return {"valid": True}
                
            # COMPTROLLER agent validation
            elif agent_type == AgentType.COMPTROLLER:
                if 'supervision_scope' not in config:
                    return {
                        "valid": False,
                        "errors": ["Comptroller agent requires 'supervision_scope' in config"]
                    }
                return {"valid": True}
                
            # UAT agent validation
            elif agent_type == AgentType.UAT:
                if 'acceptance_criteria' not in config:
                    return {
                        "valid": False,
                        "errors": ["UAT agent requires 'acceptance_criteria' in config"]
                    }
                return {"valid": True}
                
            # Default case
            return {"valid": True}
                
        except Exception as e:
            logger.error(f"Error validating agent config: {str(e)}")
            return {
                "valid": False,
                "errors": [str(e)]
            }
    
    async def validate_tools_compatibility(self, agent_type: AgentType, tools: List[str]) -> Dict[str, Any]:
        """Validate tool compatibility with agent type.
        
        Args:
            agent_type: Type of the agent
            tools: List of tools to validate
            
        Returns:
            Validation result
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # This would check if the tools are compatible with the agent type
            # For now, we'll consider all tools valid for any agent type
            
            # In a real implementation, you would check against a tool registry
            # or agent capabilities mapping
            
            return {
                "valid": True,
                "compatible_tools": tools
            }
            
        except Exception as e:
            logger.error(f"Error validating tool compatibility: {str(e)}")
            return {
                "valid": False,
                "errors": [str(e)]
            }

@router.post("/create", response_model=Dict[str, Any])
async def create_agent(
    request: AgentCreateRequest,
    background_tasks: BackgroundTasks,
    validator: AgentValidator = Depends(AgentValidator)
) -> JSONResponse:
    """Create a new agent.
    
    Args:
        request: Agent creation request
        background_tasks: FastAPI background tasks
        validator: Agent validator dependency
        
    Returns:
        Agent creation response
    """
    try:
        # Validate agent configuration
        config_validation = await validator.validate_agent_config(
            agent_type=request.type,
            config=request.config
        )
        
        if not config_validation.get("valid", False):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Invalid agent configuration",
                    code="INVALID_AGENT_CONFIG",
                    details=config_validation
                )
            )
            
        # Validate tool compatibility
        tools_validation = await validator.validate_tools_compatibility(
            agent_type=request.type,
            tools=request.tools
        )
        
        if not tools_validation.get("valid", False):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Incompatible tools for agent type",
                    code="INCOMPATIBLE_TOOLS",
                    details=tools_validation
                )
            )
            
        # Generate a unique agent ID
        agent_id = f"agent_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Register agent in registry
        agent_registry[agent_id] = {
            "id": agent_id,
            "name": request.name,
            "type": request.type,
            "description": request.description,
            "config": request.config,
            "tools": request.tools,
            "status": "created",
            "created_at": datetime.utcnow().isoformat(),
            "metadata": request.metadata
        }
        
        # Initialize agent in background
        background_tasks.add_task(
            _initialize_agent_background,
            agent_id=agent_id,
            agent_data=agent_registry[agent_id]
        )
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=create_response(
                success=True,
                message="Agent creation started",
                data={
                    "agent_id": agent_id,
                    "name": request.name,
                    "type": request.type,
                    "status": "initializing",
                    "created_at": datetime.utcnow().isoformat()
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to create agent",
                code="AGENT_CREATION_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/list", response_model=Dict[str, Any])
async def list_agents(
    type: Optional[AgentType] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> JSONResponse:
    """List registered agents with optional filtering.
    
    Args:
        type: Filter by agent type
        status: Filter by agent status
        page: Page number for pagination
        limit: Number of items per page
        
    Returns:
        List of agents
    """
    try:
        # Filter agents
        filtered_agents = agent_registry.values()
        
        if type:
            filtered_agents = [a for a in filtered_agents if a["type"] == type]
            
        if status:
            filtered_agents = [a for a in filtered_agents if a["status"] == status]
            
        # Sort by creation time (newest first)
        sorted_agents = sorted(
            filtered_agents,
            key=lambda a: a.get("created_at", ""),
            reverse=True
        )
        
        # Paginate results
        total_count = len(sorted_agents)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_agents = sorted_agents[start_idx:end_idx]
        
        return JSONResponse(
            content=paginated_response(
                success=True,
                message=f"Found {total_count} agents",
                items=paginated_agents,
                total_count=total_count,
                page=page,
                page_size=limit
            )
        )
        
    except Exception as e:
        logger.error(f"Error listing agents: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to list agents",
                code="AGENT_LIST_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/{agent_id}", response_model=Dict[str, Any])
async def get_agent(agent_id: str) -> JSONResponse:
    """Get agent by ID.
    
    Args:
        agent_id: Agent ID
        
    Returns:
        Agent details
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        # Return agent details
        return JSONResponse(
            content=create_response(
                success=True,
                message="Agent found",
                data=agent_registry[agent_id]
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to get agent",
                code="AGENT_RETRIEVAL_ERROR",
                details={"error": str(e)}
            )
        )

@router.put("/{agent_id}", response_model=Dict[str, Any])
async def update_agent(
    agent_id: str,
    request: Dict[str, Any],
    validator: AgentValidator = Depends(AgentValidator)
) -> JSONResponse:
    """Update agent configuration.
    
    Args:
        agent_id: Agent ID
        request: Update request
        validator: Agent validator dependency
        
    Returns:
        Updated agent details
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if agent is in a state that allows updates
        if agent_data["status"] not in ["created", "ready", "idle", "error"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Cannot update agent in '{agent_data['status']}' state",
                    code="INVALID_AGENT_STATE"
                )
            )
            
        # Validate updates to configuration if included
        if "config" in request:
            config_validation = await validator.validate_agent_config(
                agent_type=agent_data["type"],
                config=request["config"]
            )
            
            if not config_validation.get("valid", False):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        message="Invalid agent configuration",
                        code="INVALID_AGENT_CONFIG",
                        details=config_validation
                    )
                )
                
        # Validate updates to tools if included
        if "tools" in request:
            tools_validation = await validator.validate_tools_compatibility(
                agent_type=agent_data["type"],
                tools=request["tools"]
            )
            
            if not tools_validation.get("valid", False):
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content=error_response(
                        message="Incompatible tools for agent type",
                        code="INCOMPATIBLE_TOOLS",
                        details=tools_validation
                    )
                )
                
        # Update agent data
        for field, value in request.items():
            # Don't allow updating id, type, or created_at
            if field not in ["id", "type", "created_at"]:
                agent_data[field] = value
                
        # Update last modified timestamp
        agent_data["updated_at"] = datetime.utcnow().isoformat()
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Agent updated successfully",
                data=agent_data
            )
        )
        
    except Exception as e:
        logger.error(f"Error updating agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to update agent",
                code="AGENT_UPDATE_ERROR",
                details={"error": str(e)}
            )
        )

@router.delete("/{agent_id}", response_model=Dict[str, Any])
async def delete_agent(
    agent_id: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Delete an agent.
    
    Args:
        agent_id: Agent ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Deletion confirmation
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if agent is in a state that allows deletion
        if agent_data["status"] not in ["created", "ready", "idle", "error"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Cannot delete agent in '{agent_data['status']}' state",
                    code="INVALID_AGENT_STATE"
                )
            )
            
        # Schedule agent shutdown in background
        background_tasks.add_task(
            _shutdown_agent_background,
            agent_id=agent_id
        )
        
        # Mark as deleting
        agent_data["status"] = "deleting"
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Agent deletion started",
                data={
                    "agent_id": agent_id,
                    "status": "deleting"
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error deleting agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to delete agent",
                code="AGENT_DELETION_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/{agent_id}/start", response_model=Dict[str, Any])
async def start_agent(
    agent_id: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Start an idle agent.
    
    Args:
        agent_id: Agent ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Agent start confirmation
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if agent is in a state that allows starting
        if agent_data["status"] not in ["ready", "idle", "stopped"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Cannot start agent in '{agent_data['status']}' state",
                    code="INVALID_AGENT_STATE"
                )
            )
            
        # Schedule agent start in background
        background_tasks.add_task(
            _start_agent_background,
            agent_id=agent_id
        )
        
        # Mark as starting
        agent_data["status"] = "starting"
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Agent start initiated",
                data={
                    "agent_id": agent_id,
                    "status": "starting"
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to start agent",
                code="AGENT_START_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/{agent_id}/stop", response_model=Dict[str, Any])
async def stop_agent(
    agent_id: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Stop a running agent.
    
    Args:
        agent_id: Agent ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Agent stop confirmation
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if agent is in a state that allows stopping
        if agent_data["status"] not in ["running", "idle"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Cannot stop agent in '{agent_data['status']}' state",
                    code="INVALID_AGENT_STATE"
                )
            )
            
        # Schedule agent stop in background
        background_tasks.add_task(
            _stop_agent_background,
            agent_id=agent_id
        )
        
        # Mark as stopping
        agent_data["status"] = "stopping"
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Agent stop initiated",
                data={
                    "agent_id": agent_id,
                    "status": "stopping"
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to stop agent",
                code="AGENT_STOP_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/{agent_id}/execute", response_model=Dict[str, Any])
async def execute_agent_task(
    agent_id: str,
    request: Dict[str, Any],
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Execute a task with an agent.
    
    Args:
        agent_id: Agent ID
        request: Task request
        background_tasks: FastAPI background tasks
        
    Returns:
        Task execution confirmation
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if agent is in a state that allows task execution
        if agent_data["status"] != "running":
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Agent must be in 'running' state to execute tasks, current state: '{agent_data['status']}'",
                    code="INVALID_AGENT_STATE"
                )
            )
            
        # Validate request
        if "task" not in request:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message="Task details missing from request",
                    code="MISSING_TASK_DETAILS"
                )
            )
            
        # Generate task ID
        task_id = f"task_{uuid.uuid4().hex[:8]}_{int(time.time())}"
        
        # Initialize task in agent's task list (create if not exists)
        if "tasks" not in agent_data:
            agent_data["tasks"] = {}
            
        agent_data["tasks"][task_id] = {
            "id": task_id,
            "agent_id": agent_id,
            "details": request["task"],
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Schedule task execution in background
        background_tasks.add_task(
            _execute_agent_task_background,
            agent_id=agent_id,
            task_id=task_id
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=create_response(
                success=True,
                message="Task execution started",
                data={
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "status": "pending"
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error executing task for agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to execute task",
                code="TASK_EXECUTION_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/{agent_id}/tasks", response_model=Dict[str, Any])
async def list_agent_tasks(
    agent_id: str,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 10
) -> JSONResponse:
    """List tasks for an agent.
    
    Args:
        agent_id: Agent ID
        status: Filter by task status
        page: Page number for pagination
        limit: Number of items per page
        
    Returns:
        List of tasks
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Get tasks
        tasks = []
        if "tasks" in agent_data:
            tasks = list(agent_data["tasks"].values())
            
            # Filter by status if provided
            if status:
                tasks = [t for t in tasks if t["status"] == status]
                
            # Sort by creation time (newest first)
            tasks = sorted(
                tasks,
                key=lambda t: t.get("created_at", ""),
                reverse=True
            )
            
        # Paginate results
        total_count = len(tasks)
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_tasks = tasks[start_idx:end_idx]
        
        return JSONResponse(
            content=paginated_response(
                success=True,
                message=f"Found {total_count} tasks",
                items=paginated_tasks,
                total_count=total_count,
                page=page,
                page_size=limit
            )
        )
        
    except Exception as e:
        logger.error(f"Error listing tasks for agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to list agent tasks",
                code="TASK_LIST_ERROR",
                details={"error": str(e)}
            )
        )

@router.get("/{agent_id}/tasks/{task_id}", response_model=Dict[str, Any])
async def get_agent_task(
    agent_id: str,
    task_id: str
) -> JSONResponse:
    """Get details for a specific task.
    
    Args:
        agent_id: Agent ID
        task_id: Task ID
        
    Returns:
        Task details
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if tasks exist for agent
        if "tasks" not in agent_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"No tasks for agent: {agent_id}",
                    code="NO_TASKS_FOUND"
                )
            )
            
        # Check if specific task exists
        if task_id not in agent_data["tasks"]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Task not found: {task_id}",
                    code="TASK_NOT_FOUND"
                )
            )
            
        # Return task details
        return JSONResponse(
            content=create_response(
                success=True,
                message="Task found",
                data=agent_data["tasks"][task_id]
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting task {task_id} for agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to get task details",
                code="TASK_RETRIEVAL_ERROR",
                details={"error": str(e)}
            )
        )

@router.post("/{agent_id}/tasks/{task_id}/cancel", response_model=Dict[str, Any])
async def cancel_agent_task(
    agent_id: str,
    task_id: str,
    background_tasks: BackgroundTasks
) -> JSONResponse:
    """Cancel a running task.
    
    Args:
        agent_id: Agent ID
        task_id: Task ID
        background_tasks: FastAPI background tasks
        
    Returns:
        Task cancellation confirmation
    """
    try:
        # Check if agent exists
        if agent_id not in agent_registry:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Agent not found: {agent_id}",
                    code="AGENT_NOT_FOUND"
                )
            )
            
        agent_data = agent_registry[agent_id]
        
        # Check if tasks exist for agent
        if "tasks" not in agent_data:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"No tasks for agent: {agent_id}",
                    code="NO_TASKS_FOUND"
                )
            )
            
        # Check if specific task exists
        if task_id not in agent_data["tasks"]:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=error_response(
                    message=f"Task not found: {task_id}",
                    code="TASK_NOT_FOUND"
                )
            )
            
        task_data = agent_data["tasks"][task_id]
        
        # Check if task is in a state that allows cancellation
        if task_data["status"] not in ["pending", "running"]:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content=error_response(
                    message=f"Cannot cancel task in '{task_data['status']}' state",
                    code="INVALID_TASK_STATE"
                )
            )
            
        # Schedule task cancellation in background
        background_tasks.add_task(
            _cancel_agent_task_background,
            agent_id=agent_id,
            task_id=task_id
        )
        
        # Mark as cancelling
        task_data["status"] = "cancelling"
        
        return JSONResponse(
            content=create_response(
                success=True,
                message="Task cancellation initiated",
                data={
                    "agent_id": agent_id,
                    "task_id": task_id,
                    "status": "cancelling"
                }
            )
        )
        
    except Exception as e:
        logger.error(f"Error cancelling task {task_id} for agent {agent_id}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                message="Failed to cancel task",
                code="TASK_CANCELLATION_ERROR",
                details={"error": str(e)}
            )
        )

# Background task implementations

async def _initialize_agent_background(agent_id: str, agent_data: Dict[str, Any]) -> None:
    """Initialize agent in background.
    
    Args:
        agent_id: Agent ID
        agent_data: Agent data
    """
    try:
        # Update status to initializing
        agent_registry[agent_id]["status"] = "initializing"
        
        # Simulate initialization steps
        await asyncio.sleep(2)
        
        # Set to ready status
        agent_registry[agent_id]["status"] = "ready"
        
        # Add initialization timestamp
        agent_registry[agent_id]["initialized_at"] = datetime.utcnow().isoformat()
        
    except Exception as e:
        logger.error(f"Error initializing agent {agent_id}: {str(e)}")
        
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "error"
            agent_registry[agent_id]["error"] = str(e)

async def _shutdown_agent_background(agent_id: str) -> None:
    """Shut down and remove agent in background.
    
    Args:
        agent_id: Agent ID
    """
    try:
        # Simulate shutdown process
        await asyncio.sleep(2)
        
        # Remove from registry
        if agent_id in agent_registry:
            del agent_registry[agent_id]
            
    except Exception as e:
        logger.error(f"Error shutting down agent {agent_id}: {str(e)}")
        
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "error"
            agent_registry[agent_id]["error"] = str(e)

async def _start_agent_background(agent_id: str) -> None:
    """Start agent in background.
    
    Args:
        agent_id: Agent ID
    """
    try:
        # Simulate startup process
        await asyncio.sleep(1)
        
        # Update status
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "running"
            agent_registry[agent_id]["started_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Error starting agent {agent_id}: {str(e)}")
        
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "error"
            agent_registry[agent_id]["error"] = str(e)

async def _stop_agent_background(agent_id: str) -> None:
    """Stop agent in background.
    
    Args:
        agent_id: Agent ID
    """
    try:
        # Simulate stop process
        await asyncio.sleep(1)
        
        # Update status
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "stopped"
            agent_registry[agent_id]["stopped_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Error stopping agent {agent_id}: {str(e)}")
        
        if agent_id in agent_registry:
            agent_registry[agent_id]["status"] = "error"
            agent_registry[agent_id]["error"] = str(e)

async def _execute_agent_task_background(agent_id: str, task_id: str) -> None:
    """Execute agent task in background.
    
    Args:
        agent_id: Agent ID
        task_id: Task ID
    """
    try:
        # Check if agent and task still exist
        if agent_id not in agent_registry:
            logger.error(f"Agent {agent_id} not found for task execution")
            return
            
        agent_data = agent_registry[agent_id]
        
        if "tasks" not in agent_data or task_id not in agent_data["tasks"]:
            logger.error(f"Task {task_id} not found for agent {agent_id}")
            return
            
        task_data = agent_data["tasks"][task_id]
        
        # Update status to running
        task_data["status"] = "running"
        task_data["started_at"] = datetime.utcnow().isoformat()
        
        # Simulate task execution
        total_steps = 3
        for i in range(total_steps):
            # Check for cancellation
            if task_data["status"] == "cancelling":
                task_data["status"] = "cancelled"
                task_data["error"] = "Task was cancelled"
                task_data["completed_at"] = datetime.utcnow().isoformat()
                return
                
            # Update progress
            task_data["progress"] = {
                "steps_total": total_steps,
                "steps_completed": i,
                "current_step": f"Step {i+1}",
                "percentage_complete": int((i / total_steps) * 100)
            }
            
            # Simulate step execution
            await asyncio.sleep(1)
            
        # Mark as completed
        task_data["status"] = "completed"
        task_data["completed_at"] = datetime.utcnow().isoformat()
        task_data["result"] = {
            "success": True,
            "output": "Task completed successfully (mock)"
        }
        
    except Exception as e:
        logger.error(f"Error executing task {task_id} for agent {agent_id}: {str(e)}")
        
        # Update task status
        if (agent_id in agent_registry and 
            "tasks" in agent_registry[agent_id] and 
            task_id in agent_registry[agent_id]["tasks"]):
            
            agent_registry[agent_id]["tasks"][task_id]["status"] = "failed"
            agent_registry[agent_id]["tasks"][task_id]["error"] = str(e)
            agent_registry[agent_id]["tasks"][task_id]["completed_at"] = datetime.utcnow().isoformat()

async def _cancel_agent_task_background(agent_id: str, task_id: str) -> None:
    """Cancel agent task in background.
    
    Args:
        agent_id: Agent ID
        task_id: Task ID
    """
    try:
        # Check if agent and task still exist
        if agent_id not in agent_registry:
            logger.error(f"Agent {agent_id} not found for task cancellation")
            return
            
        agent_data = agent_registry[agent_id]
        
        if "tasks" not in agent_data or task_id not in agent_data["tasks"]:
            logger.error(f"Task {task_id} not found for agent {agent_id}")
            return
            
        task_data = agent_data["tasks"][task_id]
        
        # If task is in cancelling state, set it to cancelled
        if task_data["status"] == "cancelling":
            # Simulate cancellation process
            await asyncio.sleep(1)
            
            task_data["status"] = "cancelled"
            task_data["cancelled_at"] = datetime.utcnow().isoformat()
            
    except Exception as e:
        logger.error(f"Error cancelling task {task_id} for agent {agent_id}: {str(e)}")
        
        # Update task status
        if (agent_id in agent_registry and 
            "tasks" in agent_registry[agent_id] and 
            task_id in agent_registry[agent_id]["tasks"]):
            
            agent_registry[agent_id]["tasks"][task_id]["status"] = "error"
            agent_registry[agent_id]["tasks"][task_id]["error"] = str(e)
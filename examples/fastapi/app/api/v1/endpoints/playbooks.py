from typing import Dict, List, Optional, Any
from uuid import uuid4
from datetime import datetime
import asyncio
import json
import time

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agents import SuperAgent, InspectorAgent, JourneyAgent
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.responses import ResponseModel
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate
from core.playbook_logger import playbook_logger, track_playbook_execution

logger = get_logger(__name__)
router = APIRouter()

# In-memory task status storage
# In production, this should be replaced with a proper database
task_statuses: Dict[str, Dict] = {}

class Project(BaseModel):
    """Project configuration for playbook execution."""
    name: str = Field(..., description="Name of the project")
    description: Optional[str] = Field(None, description="Project description")
    repository_url: Optional[str] = Field(None, description="Git repository URL")
    branch: str = Field("main", description="Git branch to use")

class PlaybookConfig(BaseModel):
    """Configuration for playbook execution."""
    name: str = Field(..., description="Name of the playbook to execute")
    project: Project
    parameters: Dict = Field(default_factory=dict, description="Playbook parameters")
    agents: List[str] = Field(
        default=["super", "inspector", "journey"],
        description="List of agents to use for execution"
    )

class PlaybookExecutionResponse(BaseModel):
    """Response model for playbook execution."""
    task_id: str = Field(..., description="Unique task ID for tracking execution")
    status: str = Field(..., description="Current status of the execution")
    message: str = Field(..., description="Status message")

class PlaybookStep(BaseModel):
    """Model for a playbook step."""
    name: str
    action: str
    params: Dict[str, Any] = Field(default_factory=dict)

class PlaybookAgent(BaseModel):
    """Model for a playbook agent."""
    type: str
    config: Dict[str, Any] = Field(default_factory=dict)

class PlaybookExecuteRequest(BaseModel):
    """Request model for playbook execution."""
    name: str
    description: str
    steps: List[PlaybookStep]
    agents: List[PlaybookAgent]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PlaybookExecuteResponse(BaseModel):
    """Response model for playbook execution."""
    success: bool
    playbook_id: str
    message: str = ""
    error: str = ""

async def get_agents(
    agent_names: List[str],
    settings: Settings = Depends(get_settings)
) -> Dict:
    """
    Asynchronously initializes and returns agent instances for the specified agent names.
    
    Raises:
        HTTPException: If an unknown agent type is requested or agent initialization fails.
    
    Returns:
        A dictionary mapping agent names to their initialized instances.
    """
    try:
        agents = {}
        for name in agent_names:
            if name == "super":
                agents["super"] = await SuperAgent.create(settings)
            elif name == "inspector":
                agents["inspector"] = await InspectorAgent.create(settings)
            elif name == "journey":
                agents["journey"] = await JourneyAgent.create(settings)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown agent type: {name}"
                )
        return agents
    except Exception as e:
        logger.error(f"Failed to initialize agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize required agents"
        )

async def execute_playbook_task(
    task_id: str,
    config: PlaybookConfig,
    agents: Dict,
    settings: Settings
):
    """Execute playbook in background task."""
    try:
        # Update task status to running
        task_statuses[task_id]["status"] = "running"
        task_statuses[task_id]["message"] = "Playbook execution in progress"
        
        # Track playbook execution using the logger
        start_time = time.time()
        with track_playbook_execution(
            playbook_id=task_id,
            playbook_name=config.name,
            playbook_description=f"Execution of {config.name} playbook",
            metadata={
                "project": config.project.dict(),
                "parameters": config.parameters,
                "agents": config.agents
            }
        ) as execution_id:
            # Log the initial setup
            for agent_name, agent_instance in agents.items():
                playbook_logger.log_agent_execution(
                    execution_id=execution_id,
                    agent_id=agent_name,
                    agent_type=agent_name,
                    action="initialize",
                    input_data={"settings": str(settings)},
                    output_data={"status": "initialized"}
                )

            # Execute playbook using SuperAgent
            super_agent = agents.get("super")
            if not super_agent:
                raise ValueError("SuperAgent not initialized")
            
            # Log playbook start step
            playbook_logger.log_step_execution(
                execution_id=execution_id,
                step_id="playbook_start",
                step_name=f"Start {config.name}",
                step_type="playbook_start",
                status="started"
            )
            
            try:
                # Execute the playbook
                result = await super_agent.execute_playbook(
                    config.name,
                    config.project.dict(),
                    config.parameters
                )
                
                # Log successful execution
                execution_time = time.time() - start_time
                playbook_logger.log_step_execution(
                    execution_id=execution_id,
                    step_id="playbook_end",
                    step_name=f"End {config.name}",
                    step_type="playbook_end",
                    status="completed",
                    step_data={
                        "result": result,
                        "duration_seconds": execution_time
                    }
                )
                
                # Update task status based on execution result
                task_statuses[task_id].update({
                    "status": "completed",
                    "message": "Playbook execution completed successfully",
                    "result": result,
                    "execution_time": execution_time
                })
                
            except Exception as e:
                # Log step failure
                execution_time = time.time() - start_time
                playbook_logger.log_step_execution(
                    execution_id=execution_id,
                    step_id="playbook_error",
                    step_name=f"Error in {config.name}",
                    step_type="playbook_error",
                    status="failed",
                    step_data={
                        "error": str(e),
                        "duration_seconds": execution_time
                    }
                )
                raise

    except Exception as e:
        logger.error(f"Playbook execution failed: {str(e)}")
        task_statuses[task_id].update({
            "status": "failed",
            "message": f"Playbook execution failed: {str(e)}",
            "error": str(e),
            "execution_time": time.time() - start_time if 'start_time' in locals() else 0
        })

@router.post(
    "/execute",
    response_model=ResponseModel[PlaybookExecutionResponse],
    status_code=status.HTTP_202_ACCEPTED,
    description="Execute a playbook asynchronously"
)
async def execute_playbook(
    config: PlaybookConfig,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
) -> ResponseModel[PlaybookExecutionResponse]:
    """
    Execute a playbook asynchronously.
    
    Args:
        config: Playbook configuration
        background_tasks: FastAPI background tasks
        settings: Application settings
    
    Returns:
        Response with task ID and initial status
    """
    try:
        # Initialize required agents
        agents = await get_agents(config.agents, settings)

        # Generate unique task ID
        task_id = str(uuid4())

        # Initialize task status
        task_statuses[task_id] = {
            "status": "pending",
            "message": "Playbook execution queued",
            "config": config.dict()
        }

        # Add execution task to background tasks
        background_tasks.add_task(
            execute_playbook_task,
            task_id,
            config,
            agents,
            settings
        )

        return ResponseModel(
            success=True,
            message="Playbook execution started",
            data=PlaybookExecutionResponse(
                task_id=task_id,
                status="pending",
                message="Playbook execution queued"
            )
        )

    except Exception as e:
        logger.error(f"Failed to start playbook execution: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start playbook execution: {str(e)}"
        )

@router.get(
    "/status/{task_id}",
    response_model=ResponseModel[Dict],
    description="Get the status of a playbook execution"
)
async def get_execution_status(task_id: str) -> ResponseModel[Dict]:
    """
    Retrieves the current status of a playbook execution task by its task ID.
    
    Raises:
        HTTPException: If the specified task ID does not exist.
    
    Returns:
        ResponseModel containing the status information of the requested task.
    """
    if task_id not in task_statuses:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task ID {task_id} not found"
        )

    return ResponseModel(
        success=True,
        message="Task status retrieved successfully",
        data=task_statuses[task_id]
    )

async def initialize_agents(
    db: AsyncSession,
    agents_config: List[PlaybookAgent],
    user: User
) -> List[Agent]:
    """
    Creates and persists agent records in the database for the specified user based on the provided agent configurations.
    
    Args:
        agents_config: A list of agent configuration objects specifying agent type and settings.
        user: The user for whom the agents are being initialized.
    
    Returns:
        A list of Agent instances that have been created and activated for the user.
    """
    initialized_agents = []
    
    for agent_config in agents_config:
        # Create or get existing agent
        agent = Agent(
            type=agent_config.type,
            config=agent_config.config,
            user_id=user.id,
            status="active"
        )
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        initialized_agents.append(agent)
        
    return initialized_agents

async def create_execution_tasks(
    db: AsyncSession,
    playbook_id: str,
    steps: List[PlaybookStep],
    agents: List[Agent]
) -> List[Task]:
    """
    Creates and persists a database task for each playbook step, assigning steps to agents in a round-robin manner.
    
    Args:
        playbook_id: The unique identifier for the playbook execution.
        steps: A list of playbook steps to be executed.
        agents: A list of agent instances to which tasks will be assigned.
    
    Returns:
        A list of Task objects created and stored in the database, each representing a playbook step assigned to an agent.
    """
    tasks = []
    
    for i, step in enumerate(steps):
        # Assign step to appropriate agent
        agent = agents[i % len(agents)]  # Round-robin assignment
        
        task = Task(
            type=step.action,
            input_data={
                "params": step.params,
                "step_name": step.name,
                "playbook_id": playbook_id
            },
            status=TaskStatus.pending,
            agent_id=agent.id
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        tasks.append(task)
        
    return tasks

@router.post("/execute", response_model=PlaybookExecuteResponse)
async def execute_playbook(
    request: PlaybookExecuteRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> PlaybookExecuteResponse:
    """
    Executes a playbook by initializing agents and creating tasks for each playbook step.
    
    Initializes agents in the database for the current user, creates tasks for each step in the playbook, and returns a response containing the playbook ID and execution status.
    
    Returns:
        PlaybookExecuteResponse: Contains success status, playbook ID, and an execution message.
    
    Raises:
        HTTPException: If agent initialization or task creation fails.
    """
    try:
        # Generate playbook ID
        playbook_id = f"pb_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        # Initialize agents
        agents = await initialize_agents(db, request.agents, current_user)
        logger.info(f"Initialized {len(agents)} agents for playbook {playbook_id}")
        
        # Create tasks
        tasks = await create_execution_tasks(db, playbook_id, request.steps, agents)
        logger.info(f"Created {len(tasks)} tasks for playbook {playbook_id}")
        
        # Store playbook metadata
        metadata = {
            **request.metadata,
            "user_id": str(current_user.id),
            "started_at": datetime.utcnow().isoformat(),
            "total_steps": len(request.steps),
            "agent_ids": [str(agent.id) for agent in agents],
            "task_ids": [str(task.id) for task in tasks]
        }
        
        # Return success response
        return PlaybookExecuteResponse(
            success=True,
            playbook_id=playbook_id,
            message=f"Playbook execution started with {len(tasks)} tasks"
        )
        
    except Exception as e:
        logger.error(f"Failed to execute playbook: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute playbook: {str(e)}"
        )

@router.get(
    "/logs/{execution_id}",
    response_model=ResponseModel[Dict],
    description="Get detailed logs for a playbook execution"
)
async def get_execution_logs(execution_id: str) -> ResponseModel[Dict]:
    """
    Retrieves detailed execution logs for a playbook execution identified by its execution ID.
    
    The logs include events, step details, agent actions, tool calls, and performance metrics.
    
    Args:
        execution_id: The ID of the playbook execution
        
    Returns:
        ResponseModel containing the detailed execution logs
    
    Raises:
        HTTPException: If the execution logs could not be found
    """
    try:
        # Fetch the execution logs
        log_data = playbook_logger.get_playbook_execution(execution_id)
        if not log_data:
            # If not found with direct ID, try with playbook prefix
            prefixed_id = f"playbook_{execution_id}"
            log_data = playbook_logger.get_playbook_execution(prefixed_id)
        
        if not log_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution logs not found for ID {execution_id}"
            )
        
        # Get metrics for the execution
        metrics = playbook_logger.get_playbook_execution_metrics(execution_id)
        
        # Combine logs and metrics
        result = {
            "execution": log_data,
            "metrics": metrics
        }
        
        return ResponseModel(
            success=True,
            message="Execution logs retrieved successfully",
            data=result
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"Failed to retrieve execution logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve execution logs: {str(e)}"
        )

@router.get(
    "/recent_executions",
    response_model=ResponseModel[List[Dict]],
    description="Get recent playbook executions"
)
async def get_recent_executions(
    limit: int = 10,
    status: Optional[str] = None
) -> ResponseModel[List[Dict]]:
    """
    Retrieves a list of recent playbook executions, optionally filtered by status.
    
    Args:
        limit: Maximum number of executions to return
        status: Filter by execution status (e.g., "completed", "failed")
        
    Returns:
        ResponseModel containing the list of execution summaries
    
    Raises:
        HTTPException: If there was an error retrieving the executions
    """
    try:
        # Query for recent executions
        executions = playbook_logger.query_playbook_executions(
            status=status,
            limit=limit
        )
        
        # Format the results
        result = [
            {
                "execution_id": execution.get("execution_id"),
                "name": execution.get("name"),
                "status": execution.get("status"),
                "start_time": execution.get("start_time"),
                "end_time": execution.get("end_time"),
                "duration_seconds": execution.get("duration_seconds"),
                "steps_count": len(execution.get("steps", [])),
                "errors_count": len(execution.get("errors", []))
            }
            for execution in executions
        ]
        
        return ResponseModel(
            success=True,
            message="Recent executions retrieved successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve recent executions: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent executions: {str(e)}"
        )
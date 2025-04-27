from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.agents import SuperAgent, InspectorAgent, JourneyAgent
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.schemas.responses import ResponseModel

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

async def get_agents(
    agent_names: List[str],
    settings: Settings = Depends(get_settings)
) -> Dict:
    """Initialize required agents for playbook execution."""
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

        # Execute playbook using SuperAgent
        super_agent = agents.get("super")
        if not super_agent:
            raise ValueError("SuperAgent not initialized")

        result = await super_agent.execute_playbook(
            config.name,
            config.project.dict(),
            config.parameters
        )

        # Update task status based on execution result
        task_statuses[task_id].update({
            "status": "completed",
            "message": "Playbook execution completed successfully",
            "result": result
        })

    except Exception as e:
        logger.error(f"Playbook execution failed: {str(e)}")
        task_statuses[task_id].update({
            "status": "failed",
            "message": f"Playbook execution failed: {str(e)}",
            "error": str(e)
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
    Get the current status of a playbook execution task.
    
    Args:
        task_id: Unique task ID
    
    Returns:
        Current status of the execution task
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
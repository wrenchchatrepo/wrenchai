from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.websocket import manager
from app.db.models.user import User
from app.db.session import get_db
from app.api.v1.endpoints.users import get_current_user
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate, TaskRequest

router = APIRouter()

@router.post("", response_model=AgentResponse)
async def create_agent(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    agent_in: AgentCreate,
) -> AgentResponse:
    """Create new agent.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        agent_in: Agent creation data
        
    Returns:
        AgentResponse: Created agent
    """
    # Initialize agent with SuperAgent
    super_agent = SuperAgent()
    agent = await super_agent.create_agent(
        role=agent_in.role,
        config=agent_in.config,
        owner_id=current_user.id,
    )
    return agent

@router.post("/execute", response_model=dict)
async def execute_task(
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    task: TaskRequest,
) -> dict:
    """Execute task with agents.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        task: Task request
        
    Returns:
        dict: Task execution result
    """
    try:
        # Initialize agents
        super_agent = SuperAgent()
        inspector_agent = InspectorAgent()
        
        # Execute task
        result = await super_agent.orchestrate_task(task)
        
        # Monitor execution
        monitoring = await inspector_agent.monitor_execution(
            task.task_id,
            result
        )
        
        return {
            "status": "success",
            "task_id": task.task_id,
            "result": result,
            "monitoring": monitoring
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}",
        )

@router.websocket("/ws/{task_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    task_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """WebSocket endpoint for real-time task updates.
    
    Args:
        websocket: WebSocket connection
        task_id: Task ID
        db: Database session
    """
    await manager.connect(websocket, task_id)
    try:
        while True:
            # Get task status
            status = await get_task_status(task_id)
            
            # Broadcast status
            await manager.broadcast(
                {
                    "task_id": task_id,
                    "status": status.dict(),
                    "timestamp": datetime.utcnow().isoformat()
                },
                task_id
            )
            
            # Check if task is completed
            if status.status in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
    except Exception as e:
        await manager.broadcast(
            {
                "task_id": task_id,
                "status": {"status": "error", "message": str(e)},
                "timestamp": datetime.utcnow().isoformat()
            },
            task_id
        )
    finally:
        await manager.disconnect(websocket, task_id) 
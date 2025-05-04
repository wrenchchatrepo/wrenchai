"""FastAPI endpoints for agent management."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse, AgentUpdate
from app.schemas.task import TaskResponse
from app.schemas.responses import ResponseModel

logger = get_logger(__name__)
router = APIRouter()

@router.post(
    "",
    response_model=ResponseModel[AgentResponse],
    status_code=status.HTTP_201_CREATED,
    description="Create a new agent"
)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[AgentResponse]:
    """
    Creates a new agent associated with the current authenticated user.
    
    The agent is initialized with the provided type and configuration, assigned an "inactive" status, and persisted to the database. Returns a response model containing the created agent's data.
    """
    try:
        # Create agent instance
        agent = Agent(
            type=agent_data.type,
            config=agent_data.config,
            user_id=current_user.id,
            status="inactive"
        )
        
        # Save to database
        db.add(agent)
        await db.commit()
        await db.refresh(agent)
        
        logger.info(f"Created agent: {agent.id}")
        return ResponseModel(
            success=True,
            message="Agent created successfully",
            data=AgentResponse.model_validate(agent)
        )
        
    except Exception as e:
        logger.error(f"Failed to create agent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )

@router.get(
    "",
    response_model=ResponseModel[List[AgentResponse]],
    description="Get all agents for current user"
)
async def list_agents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[List[AgentResponse]]:
    """
    Retrieves all agents belonging to the current authenticated user.
    
    Returns:
        A response model containing a list of agent data for the user.
    """
    try:
        # Query agents
        result = await db.execute(
            select(Agent).where(Agent.user_id == current_user.id)
        )
        agents = result.scalars().all()
        
        return ResponseModel(
            success=True,
            message=f"Found {len(agents)} agents",
            data=[AgentResponse.model_validate(agent) for agent in agents]
        )
        
    except Exception as e:
        logger.error(f"Failed to list agents: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}"
        )

@router.get(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    description="Get agent by ID"
)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[AgentResponse]:
    """
    Retrieves a specific agent by its UUID for the current authenticated user.
    
    Raises:
        HTTPException: If the agent does not exist or does not belong to the user, a 404 error is raised. On unexpected errors, a 500 error is raised.
    
    Returns:
        A response model containing the agent data if found.
    """
    try:
        # Query agent
        result = await db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .where(Agent.user_id == current_user.id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
            
        return ResponseModel(
            success=True,
            message="Agent found",
            data=AgentResponse.model_validate(agent)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent: {str(e)}"
        )

@router.put(
    "/{agent_id}",
    response_model=ResponseModel[AgentResponse],
    description="Update agent"
)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[AgentResponse]:
    """
    Updates an existing agent for the current authenticated user.
    
    Attempts to update the agent identified by `agent_id` with the provided data. Only fields explicitly set in `agent_data` are modified. Returns the updated agent data on success. Raises a 404 error if the agent does not exist or is not owned by the user.
    """
    try:
        # Query agent
        result = await db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .where(Agent.user_id == current_user.id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
            
        # Update fields
        for field, value in agent_data.model_dump(exclude_unset=True).items():
            setattr(agent, field, value)
            
        await db.commit()
        await db.refresh(agent)
        
        logger.info(f"Updated agent: {agent.id}")
        return ResponseModel(
            success=True,
            message="Agent updated successfully",
            data=AgentResponse.model_validate(agent)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )

@router.delete(
    "/{agent_id}",
    response_model=ResponseModel[bool],
    description="Delete agent"
)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[bool]:
    """
    Deletes an agent by its UUID if it belongs to the current authenticated user.
    
    Raises:
        HTTPException: If the agent does not exist or does not belong to the user (404),
            or if an unexpected error occurs during deletion (500).
    
    Returns:
        ResponseModel[bool]: A response indicating whether the agent was successfully deleted.
    """
    try:
        # Query agent
        result = await db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .where(Agent.user_id == current_user.id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
            
        # Delete agent
        await db.delete(agent)
        await db.commit()
        
        logger.info(f"Deleted agent: {agent_id}")
        return ResponseModel(
            success=True,
            message="Agent deleted successfully",
            data=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )

@router.get(
    "/{agent_id}/tasks",
    response_model=ResponseModel[List[TaskResponse]],
    description="Get tasks for agent"
)
async def get_agent_tasks(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[List[TaskResponse]]:
    """
    Retrieves all tasks associated with a specific agent owned by the current user.
    
    Raises:
        HTTPException: If the agent does not exist or does not belong to the user, a 404 error is raised. If an unexpected error occurs, a 500 error is raised.
    
    Returns:
        A response model containing a list of tasks linked to the specified agent.
    """
    try:
        # Verify agent exists and belongs to user
        result = await db.execute(
            select(Agent)
            .where(Agent.id == agent_id)
            .where(Agent.user_id == current_user.id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
            
        # Get tasks
        tasks = await db.execute(
            select(Task)
            .where(Task.agent_id == agent_id)
            .order_by(Task.created_at.desc())
        )
        tasks = tasks.scalars().all()
        
        return ResponseModel(
            success=True,
            message=f"Found {len(tasks)} tasks",
            data=[TaskResponse.model_validate(task) for task in tasks]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tasks for agent {agent_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent tasks: {str(e)}"
        ) 
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
    """Create a new agent."""
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
    """Get all agents for the current user."""
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
    """Get agent by ID."""
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
    """Update agent."""
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
    """Delete agent."""
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
    """Get tasks for agent."""
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
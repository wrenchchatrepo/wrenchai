"""FastAPI endpoints for task management."""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logging import get_logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.task import Task
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.schemas.responses import ResponseModel

logger = get_logger(__name__)
router = APIRouter()

@router.post(
    "",
    response_model=ResponseModel[TaskResponse],
    status_code=status.HTTP_201_CREATED,
    description="Create a new task"
)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[TaskResponse]:
    """
    Creates a new task associated with an agent owned by the current user.
    
    Verifies that the specified agent exists and belongs to the authenticated user before creating the task. Returns the created task data on success. Raises a 404 error if the agent is not found.
    """
    try:
        # Verify agent exists and belongs to user
        result = await db.execute(
            select(Agent)
            .where(Agent.id == task_data.agent_id)
            .where(Agent.user_id == current_user.id)
        )
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {task_data.agent_id} not found"
            )
            
        # Create task instance
        task = Task(
            type=task_data.type,
            input_data=task_data.input_data,
            config=task_data.config or {},
            agent_id=task_data.agent_id,
            status="pending"
        )
        
        # Save to database
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Created task: {task.id}")
        return ResponseModel(
            success=True,
            message="Task created successfully",
            data=TaskResponse.model_validate(task)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )

@router.get(
    "",
    response_model=ResponseModel[List[TaskResponse]],
    description="Get all tasks for current user"
)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[List[TaskResponse]]:
    """
    Retrieves all tasks associated with agents owned by the current user.
    
    Returns:
        A response containing a list of tasks ordered by creation date in descending order.
    """
    try:
        # Get tasks for all user's agents
        result = await db.execute(
            select(Task)
            .join(Agent)
            .where(Agent.user_id == current_user.id)
            .order_by(Task.created_at.desc())
        )
        tasks = result.scalars().all()
        
        return ResponseModel(
            success=True,
            message=f"Found {len(tasks)} tasks",
            data=[TaskResponse.model_validate(task) for task in tasks]
        )
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )

@router.get(
    "/{task_id}",
    response_model=ResponseModel[TaskResponse],
    description="Get task by ID"
)
async def get_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[TaskResponse]:
    """
    Retrieves a specific task by its UUID for the authenticated user.
    
    Args:
        task_id: The UUID of the task to retrieve.
    
    Returns:
        A response model containing the task data if found.
    
    Raises:
        HTTPException: If the task does not exist or does not belong to the user, or on database errors.
    """
    try:
        # Query task
        result = await db.execute(
            select(Task)
            .join(Agent)
            .where(Task.id == task_id)
            .where(Agent.user_id == current_user.id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        return ResponseModel(
            success=True,
            message="Task found",
            data=TaskResponse.model_validate(task)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task: {str(e)}"
        )

@router.put(
    "/{task_id}",
    response_model=ResponseModel[TaskResponse],
    description="Update task"
)
async def update_task(
    task_id: UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[TaskResponse]:
    """
    Updates an existing task belonging to the current user.
    
    If the task with the specified ID does not exist or is not owned by the user, raises a 404 error. Only fields provided in the update data are modified.
    
    Args:
        task_id: The UUID of the task to update.
        task_data: The fields to update for the task.
    
    Returns:
        A response containing the updated task data.
    """
    try:
        # Query task
        result = await db.execute(
            select(Task)
            .join(Agent)
            .where(Task.id == task_id)
            .where(Agent.user_id == current_user.id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        # Update fields
        for field, value in task_data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
            
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"Updated task: {task.id}")
        return ResponseModel(
            success=True,
            message="Task updated successfully",
            data=TaskResponse.model_validate(task)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task: {str(e)}"
        )

@router.delete(
    "/{task_id}",
    response_model=ResponseModel[bool],
    description="Delete task"
)
async def delete_task(
    task_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> ResponseModel[bool]:
    """
    Deletes a task owned by the current user.
    
    Args:
        task_id: The UUID of the task to delete.
    
    Returns:
        A response indicating whether the task was successfully deleted.
    
    Raises:
        HTTPException: If the task does not exist or an internal error occurs.
    """
    try:
        # Query task
        result = await db.execute(
            select(Task)
            .join(Agent)
            .where(Task.id == task_id)
            .where(Agent.user_id == current_user.id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
            
        # Delete task
        await db.delete(task)
        await db.commit()
        
        logger.info(f"Deleted task: {task_id}")
        return ResponseModel(
            success=True,
            message="Task deleted successfully",
            data=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete task: {str(e)}"
        ) 
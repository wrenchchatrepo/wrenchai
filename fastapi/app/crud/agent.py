from typing import List, Optional, Dict
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload

from app.models.agent import Agent, Task
from app.schemas.agent import AgentCreate, AgentUpdate, TaskRequest

class AgentCRUD:
    """CRUD operations for agents."""

    @staticmethod
    async def create(db: AsyncSession, *, obj_in: AgentCreate, owner_id: str) -> Agent:
        """Create a new agent."""
        db_obj = Agent(
            id=str(uuid4()),
            role=obj_in.role,
            config=obj_in.config,
            is_active=obj_in.is_active,
            owner_id=owner_id
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get(db: AsyncSession, id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        result = await db.execute(
            select(Agent)
            .options(selectinload(Agent.tasks))
            .filter(Agent.id == id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_multi(
        db: AsyncSession, *, skip: int = 0, limit: int = 100
    ) -> List[Agent]:
        """Get multiple agents."""
        result = await db.execute(
            select(Agent)
            .options(selectinload(Agent.tasks))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession, *, db_obj: Agent, obj_in: AgentUpdate
    ) -> Agent:
        """Update an agent."""
        update_data = obj_in.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def delete(db: AsyncSession, *, id: str) -> bool:
        """Delete an agent."""
        result = await db.execute(delete(Agent).where(Agent.id == id))
        await db.commit()
        return bool(result.rowcount)

class TaskCRUD:
    """CRUD operations for tasks."""

    @staticmethod
    async def create(db: AsyncSession, *, obj_in: TaskRequest, agent_id: str) -> Task:
        """Create a new task."""
        db_obj = Task(
            id=str(uuid4()),
            agent_id=agent_id,
            task_type=obj_in.task_type,
            input_data=obj_in.input_data,
            config=obj_in.config
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    @staticmethod
    async def get(db: AsyncSession, id: str) -> Optional[Task]:
        """Get a task by ID."""
        result = await db.execute(
            select(Task)
            .options(selectinload(Task.agent))
            .filter(Task.id == id)
        )
        return result.scalars().first()

    @staticmethod
    async def get_multi(
        db: AsyncSession, *, agent_id: str, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        """Get multiple tasks for an agent."""
        result = await db.execute(
            select(Task)
            .filter(Task.agent_id == agent_id)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def update_status(
        db: AsyncSession,
        *,
        task_id: str,
        status: str,
        progress: float = None,
        message: str = None,
        result: Dict = None,
        error: str = None
    ) -> Task:
        """Update task status."""
        update_data = {
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "error": error
        }
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(**update_data)
            .returning(Task)
        )
        result = await db.execute(stmt)
        await db.commit()
        return result.scalars().first()

    @staticmethod
    async def delete(db: AsyncSession, *, id: str) -> bool:
        """Delete a task."""
        result = await db.execute(delete(Task).where(Task.id == id))
        await db.commit()
        return bool(result.rowcount) 
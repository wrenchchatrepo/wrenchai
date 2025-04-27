"""Repository classes for database operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from core.db.models import AuditLog, QueryMetrics, Agent, Task

class BaseRepository:
    """Base repository with common database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _execute_and_commit(self, statement):
        """Execute a statement and commit the transaction."""
        try:
            result = await self.session.execute(statement)
            await self.session.commit()
            return result
        except Exception as e:
            await self.session.rollback()
            raise e

class AuditLogRepository(BaseRepository):
    """Repository for audit log operations."""
    
    async def create(self, user: str, action: str, table_name: str, 
                    query: str, affected_rows: int, execution_time: int) -> AuditLog:
        """Create a new audit log entry.
        
        Args:
            user: User who performed the action
            action: Type of action (INSERT, UPDATE, DELETE)
            table_name: Name of the affected table
            query: SQL query that was executed
            affected_rows: Number of rows affected
            execution_time: Time taken to execute in milliseconds
            
        Returns:
            The created AuditLog instance
        """
        audit_log = AuditLog(
            user=user,
            action=action,
            table_name=table_name,
            query=query,
            affected_rows=affected_rows,
            execution_time=execution_time
        )
        self.session.add(audit_log)
        await self.session.commit()
        return audit_log
    
    async def get_by_timeframe(self, start_time: datetime, 
                             end_time: datetime) -> List[AuditLog]:
        """Get audit logs within a specific timeframe.
        
        Args:
            start_time: Start of the timeframe
            end_time: End of the timeframe
            
        Returns:
            List of AuditLog instances
        """
        stmt = select(AuditLog).where(
            AuditLog.timestamp.between(start_time, end_time)
        ).order_by(AuditLog.timestamp.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

class QueryMetricsRepository(BaseRepository):
    """Repository for query metrics operations."""
    
    async def update_metrics(self, query_hash: str, normalized_query: str,
                           execution_time: int, row_count: int) -> QueryMetrics:
        """Update metrics for a query.
        
        Args:
            query_hash: Hash of the normalized query
            normalized_query: Query with parameters replaced
            execution_time: Time taken to execute in milliseconds
            row_count: Number of rows returned/affected
            
        Returns:
            Updated QueryMetrics instance
        """
        stmt = select(QueryMetrics).where(QueryMetrics.query_hash == query_hash)
        result = await self.session.execute(stmt)
        metrics = result.scalar_one_or_none()
        
        if metrics is None:
            metrics = QueryMetrics(
                query_hash=query_hash,
                normalized_query=normalized_query,
                execution_count=1,
                total_execution_time=execution_time,
                avg_execution_time=execution_time,
                min_execution_time=execution_time,
                max_execution_time=execution_time,
                last_executed=func.now(),
                row_count=row_count
            )
            self.session.add(metrics)
        else:
            metrics.execution_count += 1
            metrics.total_execution_time += execution_time
            metrics.avg_execution_time = (
                metrics.total_execution_time // metrics.execution_count
            )
            metrics.min_execution_time = min(
                metrics.min_execution_time, execution_time
            )
            metrics.max_execution_time = max(
                metrics.max_execution_time, execution_time
            )
            metrics.last_executed = func.now()
            metrics.row_count = row_count
        
        await self.session.commit()
        return metrics

class AgentRepository(BaseRepository):
    """Repository for agent operations."""
    
    async def create(self, name: str, agent_type: str, 
                    config: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a new agent.
        
        Args:
            name: Agent name
            agent_type: Type of agent
            config: Optional agent configuration
            
        Returns:
            Created Agent instance
        """
        agent = Agent(
            name=name,
            type=agent_type,
            config=config,
            is_active=True
        )
        self.session.add(agent)
        await self.session.commit()
        return agent
    
    async def get_by_id(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent instance if found, None otherwise
        """
        stmt = select(Agent).where(Agent.id == agent_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents.
        
        Returns:
            List of active Agent instances
        """
        stmt = select(Agent).where(Agent.is_active == True)
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_last_active(self, agent_id: int) -> Optional[Agent]:
        """Update the last active timestamp for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Updated Agent instance if found, None otherwise
        """
        stmt = (
            update(Agent)
            .where(Agent.id == agent_id)
            .values(last_active=func.now())
            .returning(Agent)
        )
        result = await self._execute_and_commit(stmt)
        return result.scalar_one_or_none()

class TaskRepository(BaseRepository):
    """Repository for task operations."""
    
    async def create(self, agent_id: int, priority: int = 3,
                    input_data: Optional[Dict[str, Any]] = None) -> Task:
        """Create a new task.
        
        Args:
            agent_id: ID of the agent to assign the task to
            priority: Task priority (1-5, 1 being highest)
            input_data: Optional input data for the task
            
        Returns:
            Created Task instance
        """
        task = Task(
            agent_id=agent_id,
            status="pending",
            priority=priority,
            input_data=input_data
        )
        self.session.add(task)
        await self.session.commit()
        return task
    
    async def get_by_id(self, task_id: int) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task instance if found, None otherwise
        """
        stmt = select(Task).where(Task.id == task_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_status(self, task_id: int, status: str,
                          output_data: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None) -> Optional[Task]:
        """Update the status of a task.
        
        Args:
            task_id: ID of the task
            status: New status
            output_data: Optional output data from the task
            error: Optional error message if task failed
            
        Returns:
            Updated Task instance if found, None otherwise
        """
        update_values = {
            "status": status,
            "output_data": output_data,
            "error": error
        }
        
        if status == "started":
            update_values["started_at"] = func.now()
        elif status in ["completed", "failed"]:
            update_values["completed_at"] = func.now()
        
        stmt = (
            update(Task)
            .where(Task.id == task_id)
            .values(**update_values)
            .returning(Task)
        )
        result = await self._execute_and_commit(stmt)
        return result.scalar_one_or_none()
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get pending tasks ordered by priority.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending Task instances
        """
        stmt = (
            select(Task)
            .where(Task.status == "pending")
            .order_by(Task.priority.asc(), Task.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all() 
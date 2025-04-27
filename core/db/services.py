"""Service layer for database operations."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from core.db.repositories import (
    AuditLogRepository,
    QueryMetricsRepository,
    AgentRepository,
    TaskRepository
)
from core.db.models import AuditLog, QueryMetrics, Agent, Task

class DatabaseService:
    """Service for database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.audit_log_repo = AuditLogRepository(session)
        self.query_metrics_repo = QueryMetricsRepository(session)
        self.agent_repo = AgentRepository(session)
        self.task_repo = TaskRepository(session)
    
    async def log_operation(self, user: str, action: str, table_name: str,
                          query: str, affected_rows: int,
                          execution_time: int) -> AuditLog:
        """Log a database operation.
        
        Args:
            user: User who performed the action
            action: Type of action (INSERT, UPDATE, DELETE)
            table_name: Name of the affected table
            query: SQL query that was executed
            affected_rows: Number of rows affected
            execution_time: Time taken to execute in milliseconds
            
        Returns:
            Created AuditLog instance
        """
        return await self.audit_log_repo.create(
            user=user,
            action=action,
            table_name=table_name,
            query=query,
            affected_rows=affected_rows,
            execution_time=execution_time
        )
    
    async def get_audit_logs(self, start_time: datetime,
                           end_time: datetime) -> List[AuditLog]:
        """Get audit logs for a specific timeframe.
        
        Args:
            start_time: Start of the timeframe
            end_time: End of the timeframe
            
        Returns:
            List of AuditLog instances
        """
        return await self.audit_log_repo.get_by_timeframe(start_time, end_time)
    
    async def record_query_metrics(self, query_hash: str, normalized_query: str,
                                 execution_time: int,
                                 row_count: int) -> QueryMetrics:
        """Record metrics for a query execution.
        
        Args:
            query_hash: Hash of the normalized query
            normalized_query: Query with parameters replaced
            execution_time: Time taken to execute in milliseconds
            row_count: Number of rows returned/affected
            
        Returns:
            Updated QueryMetrics instance
        """
        return await self.query_metrics_repo.update_metrics(
            query_hash=query_hash,
            normalized_query=normalized_query,
            execution_time=execution_time,
            row_count=row_count
        )

class AgentService:
    """Service for agent operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_repo = AgentRepository(session)
        self.task_repo = TaskRepository(session)
    
    async def create_agent(self, name: str, agent_type: str,
                         config: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a new agent.
        
        Args:
            name: Agent name
            agent_type: Type of agent
            config: Optional agent configuration
            
        Returns:
            Created Agent instance
        """
        return await self.agent_repo.create(
            name=name,
            agent_type=agent_type,
            config=config
        )
    
    async def get_agent(self, agent_id: int) -> Optional[Agent]:
        """Get an agent by ID.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Agent instance if found, None otherwise
        """
        return await self.agent_repo.get_by_id(agent_id)
    
    async def get_active_agents(self) -> List[Agent]:
        """Get all active agents.
        
        Returns:
            List of active Agent instances
        """
        return await self.agent_repo.get_active_agents()
    
    async def update_agent_activity(self, agent_id: int) -> Optional[Agent]:
        """Update the last active timestamp for an agent.
        
        Args:
            agent_id: ID of the agent
            
        Returns:
            Updated Agent instance if found, None otherwise
        """
        return await self.agent_repo.update_last_active(agent_id)
    
    async def create_task(self, agent_id: int, priority: int = 3,
                         input_data: Optional[Dict[str, Any]] = None) -> Task:
        """Create a new task for an agent.
        
        Args:
            agent_id: ID of the agent to assign the task to
            priority: Task priority (1-5, 1 being highest)
            input_data: Optional input data for the task
            
        Returns:
            Created Task instance
        """
        # Verify agent exists and is active
        agent = await self.agent_repo.get_by_id(agent_id)
        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found")
        if not agent.is_active:
            raise ValueError(f"Agent with ID {agent_id} is not active")
        
        return await self.task_repo.create(
            agent_id=agent_id,
            priority=priority,
            input_data=input_data
        )
    
    async def get_task(self, task_id: int) -> Optional[Task]:
        """Get a task by ID.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Task instance if found, None otherwise
        """
        return await self.task_repo.get_by_id(task_id)
    
    async def update_task_status(self, task_id: int, status: str,
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
        # Verify task exists
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise ValueError(f"Task with ID {task_id} not found")
        
        # Verify status transition is valid
        valid_transitions = {
            "pending": ["started"],
            "started": ["completed", "failed"],
            "completed": [],
            "failed": []
        }
        
        if task.status not in valid_transitions or \
           status not in valid_transitions[task.status]:
            raise ValueError(
                f"Invalid status transition from {task.status} to {status}"
            )
        
        return await self.task_repo.update_status(
            task_id=task_id,
            status=status,
            output_data=output_data,
            error=error
        )
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Task]:
        """Get pending tasks ordered by priority.
        
        Args:
            limit: Maximum number of tasks to return
            
        Returns:
            List of pending Task instances
        """
        return await self.task_repo.get_pending_tasks(limit) 
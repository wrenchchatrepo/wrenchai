"""Error recovery system for tasks."""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.task import Task
from app.schemas.task import TaskUpdate

logger = get_logger(__name__)

class ErrorRecovery:
    """Handles task error recovery and cleanup."""
    
    def __init__(self, db: AsyncSession):
        """
        Initializes the ErrorRecovery instance with an asynchronous database session.
        
        Args:
            db: An asynchronous SQLAlchemy session used for database operations.
        """
        self.db = db
        
    async def recover_stuck_tasks(
        self,
        max_age_minutes: int = 30,
        max_retries: int = 3
    ) -> List[Task]:
        """
        Attempts to recover tasks stuck in the "running" state beyond a specified age.
        
        Finds tasks that have been running longer than `max_age_minutes` and have not exceeded
        the maximum number of retries. For each such task, increments the retry count and either
        resets the task for another attempt or marks it as failed if the retry limit is reached.
        
        Args:
            max_age_minutes: The minimum age in minutes for a task to be considered stuck.
            max_retries: The maximum number of retry attempts allowed for a task.
        
        Returns:
            A list of tasks that were recovered or marked as failed.
        """
        try:
            # Find stuck tasks
            cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
            result = await self.db.execute(
                select(Task)
                .where(Task.status == "running")
                .where(Task.updated_at < cutoff_time)
                .where(Task.retry_count < max_retries)
            )
            stuck_tasks = result.scalars().all()
            
            recovered_tasks = []
            for task in stuck_tasks:
                # Increment retry count
                task.retry_count += 1
                
                if task.retry_count >= max_retries:
                    # Mark as failed if max retries reached
                    task.status = "failed"
                    task.error = {
                        "type": "max_retries_exceeded",
                        "message": f"Task failed after {max_retries} retries"
                    }
                else:
                    # Reset for retry
                    task.status = "pending"
                    task.progress = 0.0
                    task.message = f"Retrying task (attempt {task.retry_count + 1})"
                    
                recovered_tasks.append(task)
                
            if recovered_tasks:
                await self.db.commit()
                logger.info(f"Recovered {len(recovered_tasks)} stuck tasks")
                
            return recovered_tasks
            
        except Exception as e:
            logger.error(f"Failed to recover stuck tasks: {str(e)}")
            return []
            
    async def cleanup_incomplete_tasks(
        self,
        agent_id: Optional[str] = None
    ) -> List[Task]:
        """
        Marks all tasks in "pending" or "running" states as failed due to a system or agent crash.
        
        If an agent ID is provided, only tasks associated with that agent are affected. Returns a list of tasks that were marked as failed, or an empty list if none were found or an error occurred.
        """
        try:
            # Build query
            query = select(Task).where(
                Task.status.in_(["pending", "running"])
            )
            if agent_id:
                query = query.where(Task.agent_id == agent_id)
                
            # Find incomplete tasks
            result = await self.db.execute(query)
            incomplete_tasks = result.scalars().all()
            
            cleaned_tasks = []
            for task in incomplete_tasks:
                task.status = "failed"
                task.error = {
                    "type": "system_crash",
                    "message": "Task incomplete due to system/agent crash"
                }
                cleaned_tasks.append(task)
                
            if cleaned_tasks:
                await self.db.commit()
                logger.info(
                    f"Cleaned up {len(cleaned_tasks)} incomplete tasks" +
                    (f" for agent {agent_id}" if agent_id else "")
                )
                
            return cleaned_tasks
            
        except Exception as e:
            logger.error(f"Failed to clean up incomplete tasks: {str(e)}")
            return []
            
    async def retry_failed_task(self, task_id: str) -> Optional[Task]:
        """
        Attempts to retry a task that is currently in the "failed" state.
        
        If the specified task exists and is marked as "failed", its status is reset to "pending", progress is cleared, error information is removed, the retry count is incremented, and it is queued for another attempt. Returns the updated task on success, or None if the task does not exist, is not failed, or an error occurs.
        
        Args:
            task_id: The unique identifier of the task to retry.
        
        Returns:
            The updated Task object if the retry is queued successfully, or None otherwise.
        """
        try:
            # Get task
            task = await self.db.get(Task, task_id)
            if not task:
                logger.error(f"Task {task_id} not found")
                return None
                
            if task.status != "failed":
                logger.error(f"Task {task_id} is not in failed state")
                return None
                
            # Reset task for retry
            task.status = "pending"
            task.progress = 0.0
            task.error = None
            task.message = "Task queued for retry"
            task.retry_count += 1
            
            await self.db.commit()
            logger.info(f"Queued task {task_id} for retry")
            return task
            
        except Exception as e:
            logger.error(f"Failed to retry task {task_id}: {str(e)}")
            return None
            
    async def start_recovery_monitor(
        self,
        check_interval: int = 300,  # 5 minutes
        max_age_minutes: int = 30,
        max_retries: int = 3
    ):
        """
        Runs a background loop that periodically attempts to recover stuck tasks.
        
        Continuously calls the task recovery process at specified intervals, handling and logging any exceptions without stopping the monitoring loop.
        """
        while True:
            try:
                # Recover stuck tasks
                await self.recover_stuck_tasks(max_age_minutes, max_retries)
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Recovery monitor error: {str(e)}")
                await asyncio.sleep(check_interval) 
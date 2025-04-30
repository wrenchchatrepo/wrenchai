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
        """Initialize error recovery."""
        self.db = db
        
    async def recover_stuck_tasks(
        self,
        max_age_minutes: int = 30,
        max_retries: int = 3
    ) -> List[Task]:
        """Recover tasks stuck in running state."""
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
        """Clean up incomplete tasks after agent/system crash."""
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
        """Retry a failed task."""
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
        """Start background recovery monitor."""
        while True:
            try:
                # Recover stuck tasks
                await self.recover_stuck_tasks(max_age_minutes, max_retries)
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Recovery monitor error: {str(e)}")
                await asyncio.sleep(check_interval) 
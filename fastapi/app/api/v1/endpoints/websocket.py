"""WebSocket endpoints for real-time task updates."""

from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.websocket import manager
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.task import Task

logger = get_logger(__name__)
router = APIRouter()

@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_endpoint(
    websocket: WebSocket,
    task_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Handles a WebSocket connection for real-time updates on a specific task.
    
    Upon connection, registers the client to receive updates for the given task ID, sends the current task state if available, and maintains the connection for bidirectional communication. Responds to "ping" messages with "pong" and manages client disconnection and error reporting.
    """
    try:
        # Connect client
        await manager.connect(websocket, str(task_id))
        
        # Send initial task state
        task = await db.get(Task, task_id)
        if task:
            await manager.broadcast_task_update(
                str(task_id),
                task.status,
                task.progress,
                task.message,
                task.result,
                task.error
            )
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_json()
                
                # Handle client messages if needed
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
        except WebSocketDisconnect:
            await manager.disconnect(websocket, str(task_id))
            
    except Exception as e:
        logger.error(f"WebSocket error for task {task_id}: {str(e)}")
        await manager.send_error(websocket, str(e))
        await manager.disconnect(websocket, str(task_id))

@router.websocket("/ws/agents/{agent_id}/tasks")
async def websocket_agent_tasks_endpoint(
    websocket: WebSocket,
    agent_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Handles a WebSocket connection to provide real-time updates for all tasks associated with a specific agent.
    
    Upon connection, sends the current state of each task belonging to the agent and maintains the connection for ongoing updates and client messages. Responds to "ping" messages to keep the connection alive and manages client disconnections and error reporting.
    
    Args:
        agent_id: The UUID of the agent whose tasks are being monitored.
    """
    try:
        # Connect client
        await manager.connect(websocket, str(agent_id))
        
        # Send initial tasks state
        tasks = await db.execute(
            select(Task)
            .where(Task.agent_id == agent_id)
            .order_by(Task.created_at.desc())
        )
        tasks = tasks.scalars().all()
        
        for task in tasks:
            await manager.broadcast_task_update(
                str(task.id),
                task.status,
                task.progress,
                task.message,
                task.result,
                task.error
            )
        
        try:
            while True:
                # Keep connection alive and handle incoming messages
                data = await websocket.receive_json()
                
                # Handle client messages if needed
                if data.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                    
        except WebSocketDisconnect:
            await manager.disconnect(websocket, str(agent_id))
            
    except Exception as e:
        logger.error(f"WebSocket error for agent {agent_id}: {str(e)}")
        await manager.send_error(websocket, str(e))
        await manager.disconnect(websocket, str(agent_id)) 
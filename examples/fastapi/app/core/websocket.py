"""WebSocket manager for real-time updates."""

from typing import Dict, List, Optional
from fastapi import WebSocket
from pydantic import BaseModel
from app.core.logging import get_logger
from datetime import datetime

logger = get_logger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        """
        Initializes the connection manager with an empty set of active WebSocket connections.
        """
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accepts a WebSocket connection and registers it under the specified client ID.
        
        Adds the WebSocket to the list of active connections for the client.
        """
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"Client {client_id} connected")
        
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """
        Removes a WebSocket connection from the active connections for a given client.
        
        If the client has no remaining active connections after removal, the client entry is deleted.
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")
        
    async def broadcast(self, message: dict, client_id: str):
        """
        Sends a JSON message to all active WebSocket connections for a specific client.
        
        If sending fails for any connection, the connection is removed from the client's active connections.
        """
        if client_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[client_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message to client {client_id}: {str(e)}")
                    disconnected.append(connection)
                    
            # Clean up disconnected clients
            for connection in disconnected:
                await self.disconnect(connection, client_id)
                
    async def broadcast_task_update(
        self,
        task_id: str,
        status: str,
        progress: float,
        message: str = None,
        result: dict = None,
        error: dict = None,
        step_details: dict = None,
        timestamp: str = None
    ):
        """
        Broadcasts a task update to all connected clients.
        
        Constructs a task update message containing the task ID, status, progress, optional message, result, error, and a UTC timestamp, then sends it to every connected client.
<<<<<<< HEAD:examples/fastapi/app/core/websocket.py
        
        Args:
            task_id: Unique identifier for the task
            status: Current status of the task
            progress: Progress percentage (0.0 to 100.0)
            message: Optional status message
            result: Optional result data
            error: Optional error information
            step_details: Optional detailed information about the current step
            timestamp: Optional ISO format timestamp (if not provided, current time is used)
=======
>>>>>>> update-mvp-implementation-plan:fastapi/app/core/websocket.py
        """
        update = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "error": error,
            "step_details": step_details,
            "timestamp": timestamp if timestamp else datetime.utcnow().isoformat()
        }
        
        # Broadcast to all clients
        for client_id in list(self.active_connections.keys()):
            await self.broadcast(update, client_id)
            
    async def send_error(self, websocket: WebSocket, message: str):
        """
        Sends an error message with a timestamp to a specific WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to send the error message to.
            message: The error message content.
        """
        try:
            await websocket.send_json({
                "type": "error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")
            
    async def start_heartbeat(self, client_id: str, interval: float = 30.0):
        """
        Starts a heartbeat to keep the WebSocket connection alive.
        
        Args:
            client_id: The client ID to send heartbeats to
            interval: Time between heartbeats in seconds
        """
        while client_id in self.active_connections:
            try:
                # Send a ping message to client
                await self.broadcast({"type": "ping", "timestamp": datetime.utcnow().isoformat()}, client_id)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Heartbeat error for client {client_id}: {str(e)}")
                # If error occurred, break the loop
                break

class WebSocketMessage(BaseModel):
    """WebSocket message schema.
    
    Attributes:
        type: Message type
        data: Message data
    """
    type: str
    data: dict

# Global connection manager instance
manager = ConnectionManager() 
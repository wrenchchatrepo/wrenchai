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
        """Initialize connection manager."""
        self.active_connections: Dict[str, List[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, client_id: str):
        """Connect a client."""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
        logger.info(f"Client {client_id} connected")
        
    async def disconnect(self, websocket: WebSocket, client_id: str):
        """Disconnect a client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        logger.info(f"Client {client_id} disconnected")
        
    async def broadcast(self, message: dict, client_id: str):
        """Broadcast message to specific client."""
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
        error: dict = None
    ):
        """Broadcast task update to all connected clients."""
        update = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Broadcast to all clients
        for client_id in list(self.active_connections.keys()):
            await self.broadcast(update, client_id)
            
    async def send_error(self, websocket: WebSocket, message: str):
        """Send error message to specific connection."""
        try:
            await websocket.send_json({
                "type": "error",
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Failed to send error message: {str(e)}")

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
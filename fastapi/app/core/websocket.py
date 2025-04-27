from typing import Dict, List, Optional

from fastapi import WebSocket
from pydantic import BaseModel

class ConnectionManager:
    """WebSocket connection manager.
    
    This class manages WebSocket connections and broadcasts messages to connected clients.
    """
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Connect a client.
        
        Args:
            websocket: WebSocket connection
            client_id: Client identifier
        """
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = []
        self.active_connections[client_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Disconnect a client.
        
        Args:
            websocket: WebSocket connection
            client_id: Client identifier
        """
        if client_id in self.active_connections:
            self.active_connections[client_id].remove(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
    
    async def broadcast(self, message: dict, client_id: Optional[str] = None) -> None:
        """Broadcast message to connected clients.
        
        Args:
            message: Message to broadcast
            client_id: Optional client ID to broadcast to specific client
        """
        if client_id:
            # Broadcast to specific client
            if client_id in self.active_connections:
                for connection in self.active_connections[client_id]:
                    await connection.send_json(message)
        else:
            # Broadcast to all clients
            for connections in self.active_connections.values():
                for connection in connections:
                    await connection.send_json(message)

class WebSocketMessage(BaseModel):
    """WebSocket message schema.
    
    Attributes:
        type: Message type
        data: Message data
    """
    type: str
    data: dict

# Create global connection manager instance
manager = ConnectionManager() 
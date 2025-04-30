"""Message queue implementation for agent communication."""

import asyncio
from typing import Dict, Optional

class MessageQueue:
    """Asynchronous message queue for agent communication."""
    
    def __init__(self):
        """Initialize message queue."""
        self._queue = asyncio.Queue()
        self._subscribers: Dict[str, asyncio.Queue] = {}
    
    async def put(self, message: dict):
        """Put a message in the queue."""
        await self._queue.put(message)
        # Also send to any subscribers
        recipient = message.get("recipient")
        if recipient and recipient in self._subscribers:
            await self._subscribers[recipient].put(message)
    
    async def get(self) -> Optional[dict]:
        """Get a message from the queue."""
        try:
            return await self._queue.get()
        except asyncio.QueueEmpty:
            return None
    
    async def subscribe(self, agent_name: str) -> asyncio.Queue:
        """Subscribe an agent to receive messages."""
        if agent_name not in self._subscribers:
            self._subscribers[agent_name] = asyncio.Queue()
        return self._subscribers[agent_name]
    
    async def unsubscribe(self, agent_name: str):
        """Unsubscribe an agent from receiving messages."""
        if agent_name in self._subscribers:
            del self._subscribers[agent_name]
    
    async def clear(self):
        """Clear all messages from the queue."""
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Clear subscriber queues
        for subscriber_queue in self._subscribers.values():
            while not subscriber_queue.empty():
                try:
                    subscriber_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
    
    def size(self) -> int:
        """Get the current size of the queue."""
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return self._queue.empty() 
"""Message queue implementation for agent communication."""

import asyncio
from typing import Dict, Optional

class MessageQueue:
    """Asynchronous message queue for agent communication."""
    
    def __init__(self):
        """
        Initializes the message queue and subscriber management structures.
        
        Creates the main asynchronous queue for messages and a dictionary to track subscriber queues by agent name.
        """
        self._queue = asyncio.Queue()
        self._subscribers: Dict[str, asyncio.Queue] = {}
    
    async def put(self, message: dict):
        """
        Adds a message to the main queue and forwards it to a recipient's subscriber queue if specified.
        
        If the message contains a "recipient" key matching a subscribed agent, the message is also placed in that agent's dedicated queue.
        """
        await self._queue.put(message)
        # Also send to any subscribers
        recipient = message.get("recipient")
        if recipient and recipient in self._subscribers:
            await self._subscribers[recipient].put(message)
    
    async def get(self) -> Optional[dict]:
        """
        Retrieves a message from the main queue asynchronously.
        
        Returns:
            The next message as a dictionary if available, or None if the queue is empty.
        """
        try:
            return await self._queue.get()
        except asyncio.QueueEmpty:
            return None
    
    async def subscribe(self, agent_name: str) -> asyncio.Queue:
        """
        Subscribes an agent to receive messages via a dedicated queue.
        
        If the agent is not already subscribed, creates a new queue for the agent.
        Returns the agent's subscriber queue.
        """
        if agent_name not in self._subscribers:
            self._subscribers[agent_name] = asyncio.Queue()
        return self._subscribers[agent_name]
    
    async def unsubscribe(self, agent_name: str):
        """
        Removes the specified agent's subscription to stop delivering messages to them.
        
        Args:
            agent_name: The name of the agent to unsubscribe.
        """
        if agent_name in self._subscribers:
            del self._subscribers[agent_name]
    
    async def clear(self):
        """
        Removes all messages from the main queue and all subscriber queues.
        
        This method empties the main message queue and each subscriber's queue, discarding any messages they contain.
        """
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
        """
        Returns the number of messages currently in the main queue.
        
        Returns:
            The count of messages in the main queue.
        """
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        """
        Returns True if the main message queue is empty, otherwise False.
        """
        return self._queue.empty() 
"""
Enhanced message broker for advanced agent communication patterns.

This module provides a comprehensive message broker system that supports:
- Direct messaging between agents
- Broadcast and multicast messaging
- Pub-sub patterns with topics
- Workflow-oriented messaging
- Message acknowledgment and receipts
- Message prioritization and routing
- Message persistence and history
"""

import asyncio
import logging
import uuid
import json
import time
from datetime import datetime
from enum import Enum
from typing import Dict, List, Set, Any, Optional, Union, Callable, Tuple, Awaitable
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages in the system."""
    TEXT = "text"
    COMMAND = "command"
    EVENT = "event"
    WORKFLOW = "workflow"
    RESPONSE = "response"
    ERROR = "error"
    BROADCAST = "broadcast"
    SYSTEM = "system"
    PING = "ping"
    ACK = "ack"


class MessagePriority(int, Enum):
    """Priority levels for messages."""
    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4  # Lowest priority


class MessageStatus(str, Enum):
    """Status of a message."""
    CREATED = "created"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    PROCESSED = "processed"
    FAILED = "failed"
    EXPIRED = "expired"


class Message(BaseModel):
    """Model for a message in the broker system."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message ID")
    sender: str = Field(..., description="Sender agent name")
    recipient: Optional[str] = Field(None, description="Recipient agent name (None for broadcasts)")
    topic: Optional[str] = Field(None, description="Message topic for pub-sub")
    workflow_id: Optional[str] = Field(None, description="Associated workflow ID")
    content: Any = Field(..., description="Message content")
    type: MessageType = Field(default=MessageType.TEXT, description="Type of message")
    priority: MessagePriority = Field(default=MessagePriority.NORMAL, description="Message priority")
    status: MessageStatus = Field(default=MessageStatus.CREATED, description="Current status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    sent_at: Optional[datetime] = Field(None, description="Sent timestamp")
    delivered_at: Optional[datetime] = Field(None, description="Delivery timestamp")
    read_at: Optional[datetime] = Field(None, description="Read timestamp")
    processed_at: Optional[datetime] = Field(None, description="Processed timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration timestamp")
    reply_to: Optional[str] = Field(None, description="ID of message this is replying to")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    trace_id: Optional[str] = Field(None, description="Trace ID for distributed tracing")

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }

    def mark_sent(self):
        """Mark the message as sent."""
        self.status = MessageStatus.SENT
        self.sent_at = datetime.utcnow()
        return self

    def mark_delivered(self):
        """Mark the message as delivered."""
        self.status = MessageStatus.DELIVERED
        self.delivered_at = datetime.utcnow()
        return self

    def mark_read(self):
        """Mark the message as read."""
        self.status = MessageStatus.READ
        self.read_at = datetime.utcnow()
        return self

    def mark_processed(self):
        """Mark the message as processed."""
        self.status = MessageStatus.PROCESSED
        self.processed_at = datetime.utcnow()
        return self

    def mark_failed(self, reason: str = None):
        """Mark the message as failed."""
        self.status = MessageStatus.FAILED
        if reason:
            self.metadata["failure_reason"] = reason
        return self

    def create_reply(self, content: Any, type: MessageType = MessageType.RESPONSE) -> 'Message':
        """Create a reply to this message."""
        return Message(
            sender=self.recipient,
            recipient=self.sender,
            content=content,
            type=type,
            reply_to=self.id,
            workflow_id=self.workflow_id,
            trace_id=self.trace_id,
            topic=self.topic
        )

    def is_expired(self) -> bool:
        """Check if the message has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    @validator('recipient', 'topic', pre=True)
    def validate_recipient_or_topic(cls, v, values):
        """Validate that either recipient or topic is provided."""
        if 'type' in values and values['type'] == MessageType.BROADCAST:
            # Broadcast can have neither
            return v
            
        if v is None and 'topic' not in values and 'recipient' not in values:
            raise ValueError("Either recipient or topic must be provided")
        return v


class MessageFilter(BaseModel):
    """Filter criteria for message retrieval."""
    sender: Optional[str] = None
    recipient: Optional[str] = None
    topic: Optional[str] = None
    workflow_id: Optional[str] = None
    type: Optional[MessageType] = None
    priority: Optional[MessagePriority] = None
    status: Optional[MessageStatus] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    reply_to: Optional[str] = None
    
    def matches(self, message: Message) -> bool:
        """Check if a message matches this filter."""
        if self.sender and message.sender != self.sender:
            return False
        if self.recipient and message.recipient != self.recipient:
            return False
        if self.topic and message.topic != self.topic:
            return False
        if self.workflow_id and message.workflow_id != self.workflow_id:
            return False
        if self.type and message.type != self.type:
            return False
        if self.priority and message.priority != self.priority:
            return False
        if self.status and message.status != self.status:
            return False
        if self.since and message.created_at < self.since:
            return False
        if self.until and message.created_at > self.until:
            return False
        if self.reply_to and message.reply_to != self.reply_to:
            return False
        return True


class MessageHandler:
    """Handler for message processing."""
    
    def __init__(
        self, 
        callback: Callable[[Message], Awaitable[None]],
        filter_: Optional[MessageFilter] = None,
        description: Optional[str] = None
    ):
        """Initialize a message handler.
        
        Args:
            callback: Async function to call when a message matches
            filter_: Filter to apply to messages
            description: Optional description of this handler
        """
        self.callback = callback
        self.filter = filter_ or MessageFilter()
        self.description = description or "Message handler"
        self.id = str(uuid.uuid4())
        
    async def process(self, message: Message) -> bool:
        """Process a message if it matches the filter.
        
        Args:
            message: Message to process
            
        Returns:
            Whether the message was processed
        """
        if self.filter.matches(message):
            try:
                await self.callback(message)
                return True
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
                return False
        return False


class TopicStats(BaseModel):
    """Statistics for a message topic."""
    name: str
    message_count: int = 0
    subscriber_count: int = 0
    last_message_at: Optional[datetime] = None


class AgentStats(BaseModel):
    """Statistics for an agent's message activity."""
    name: str
    sent_count: int = 0
    received_count: int = 0
    last_sent_at: Optional[datetime] = None
    last_received_at: Optional[datetime] = None
    subscribed_topics: List[str] = Field(default_factory=list)


class WorkflowStats(BaseModel):
    """Statistics for workflow messaging."""
    workflow_id: str
    message_count: int = 0
    agent_participants: List[str] = Field(default_factory=list)
    last_message_at: Optional[datetime] = None


class BrokerStats(BaseModel):
    """Overall statistics for the message broker."""
    start_time: datetime = Field(default_factory=datetime.utcnow)
    total_messages: int = 0
    messages_by_type: Dict[str, int] = Field(default_factory=dict)
    messages_by_priority: Dict[str, int] = Field(default_factory=dict)
    active_agents: int = 0
    active_topics: int = 0
    messages_per_second: float = 0


class MessageBroker:
    """Enhanced message broker for agent communication."""
    
    def __init__(self, persistence_enabled: bool = True, max_history: int = 1000):
        """Initialize the message broker.
        
        Args:
            persistence_enabled: Whether to persist messages
            max_history: Maximum number of messages to keep in history
        """
        # Direct messaging queues
        self._agent_queues: Dict[str, asyncio.PriorityQueue] = {}
        
        # Topic subscriptions
        self._topic_subscribers: Dict[str, Set[str]] = {}
        
        # Message handlers for more complex patterns
        self._message_handlers: Dict[str, MessageHandler] = {}
        
        # Message history
        self._message_history: List[Message] = []
        self.max_history = max_history
        
        # Statistics
        self._topic_stats: Dict[str, TopicStats] = {}
        self._agent_stats: Dict[str, AgentStats] = {}
        self._workflow_stats: Dict[str, WorkflowStats] = {}
        self._broker_stats = BrokerStats()
        
        # Locks for thread safety
        self._queues_lock = asyncio.Lock()
        self._topics_lock = asyncio.Lock()
        self._handlers_lock = asyncio.Lock()
        self._history_lock = asyncio.Lock()
        
        # Periodic tasks
        self._cleanup_task = None
        self._stats_task = None
        
        # Status tracking
        self._active = True
        self._persistence_enabled = persistence_enabled
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background maintenance tasks."""
        loop = asyncio.get_event_loop()
        self._cleanup_task = loop.create_task(self._periodic_cleanup())
        self._stats_task = loop.create_task(self._update_stats())
    
    async def _periodic_cleanup(self):
        """Periodically clean up expired messages."""
        while self._active:
            try:
                # Clean up expired messages in queues
                async with self._queues_lock:
                    for agent, queue in self._agent_queues.items():
                        # We can't directly manipulate the queue, so we'll rebuild it
                        temp_queue = asyncio.PriorityQueue()
                        while not queue.empty():
                            try:
                                priority, message = await queue.get()
                                if not message.is_expired():
                                    await temp_queue.put((priority, message))
                                else:
                                    message.status = MessageStatus.EXPIRED
                                    logger.debug(f"Expired message {message.id} for {agent}")
                            except Exception as e:
                                logger.error(f"Error during queue cleanup: {e}")
                        self._agent_queues[agent] = temp_queue
                
                # Clean up message history if needed
                if len(self._message_history) > self.max_history:
                    async with self._history_lock:
                        # Remove oldest messages
                        self._message_history = self._message_history[-self.max_history:]
                
            except Exception as e:
                logger.error(f"Error in message cleanup: {e}")
            
            # Run every 60 seconds
            await asyncio.sleep(60)
    
    async def _update_stats(self):
        """Periodically update broker statistics."""
        last_count = 0
        last_time = time.time()
        
        while self._active:
            try:
                current_count = self._broker_stats.total_messages
                current_time = time.time()
                
                # Calculate messages per second
                time_diff = current_time - last_time
                if time_diff > 0:
                    message_diff = current_count - last_count
                    self._broker_stats.messages_per_second = message_diff / time_diff
                
                last_count = current_count
                last_time = current_time
                
                # Update active counts
                self._broker_stats.active_agents = len(self._agent_queues)
                self._broker_stats.active_topics = len(self._topic_subscribers)
                
            except Exception as e:
                logger.error(f"Error updating stats: {e}")
            
            # Run every 5 seconds
            await asyncio.sleep(5)
    
    async def register_agent(self, agent_name: str) -> bool:
        """Register an agent with the broker.
        
        Args:
            agent_name: Name of the agent to register
            
        Returns:
            Whether the registration was successful
        """
        async with self._queues_lock:
            if agent_name not in self._agent_queues:
                self._agent_queues[agent_name] = asyncio.PriorityQueue()
                self._agent_stats[agent_name] = AgentStats(name=agent_name)
                logger.info(f"Registered agent: {agent_name}")
                return True
            return False
    
    async def unregister_agent(self, agent_name: str) -> bool:
        """Unregister an agent from the broker.
        
        Args:
            agent_name: Name of the agent to unregister
            
        Returns:
            Whether the unregistration was successful
        """
        async with self._queues_lock:
            if agent_name in self._agent_queues:
                del self._agent_queues[agent_name]
                
                # Remove from all topic subscriptions
                async with self._topics_lock:
                    for topic, subscribers in self._topic_subscribers.items():
                        subscribers.discard(agent_name)
                
                logger.info(f"Unregistered agent: {agent_name}")
                return True
            return False
    
    async def subscribe_to_topic(self, agent_name: str, topic: str) -> bool:
        """Subscribe an agent to a topic.
        
        Args:
            agent_name: Name of the agent
            topic: Topic to subscribe to
            
        Returns:
            Whether the subscription was successful
        """
        # Ensure agent is registered
        if agent_name not in self._agent_queues:
            await self.register_agent(agent_name)
        
        async with self._topics_lock:
            if topic not in self._topic_subscribers:
                self._topic_subscribers[topic] = set()
                self._topic_stats[topic] = TopicStats(name=topic)
            
            self._topic_subscribers[topic].add(agent_name)
            self._topic_stats[topic].subscriber_count = len(self._topic_subscribers[topic])
            
            # Update agent stats
            if agent_name in self._agent_stats:
                if topic not in self._agent_stats[agent_name].subscribed_topics:
                    self._agent_stats[agent_name].subscribed_topics.append(topic)
            
            logger.info(f"Agent {agent_name} subscribed to topic: {topic}")
            return True
    
    async def unsubscribe_from_topic(self, agent_name: str, topic: str) -> bool:
        """Unsubscribe an agent from a topic.
        
        Args:
            agent_name: Name of the agent
            topic: Topic to unsubscribe from
            
        Returns:
            Whether the unsubscription was successful
        """
        async with self._topics_lock:
            if topic in self._topic_subscribers and agent_name in self._topic_subscribers[topic]:
                self._topic_subscribers[topic].remove(agent_name)
                self._topic_stats[topic].subscriber_count = len(self._topic_subscribers[topic])
                
                # Update agent stats
                if agent_name in self._agent_stats:
                    if topic in self._agent_stats[agent_name].subscribed_topics:
                        self._agent_stats[agent_name].subscribed_topics.remove(topic)
                
                logger.info(f"Agent {agent_name} unsubscribed from topic: {topic}")
                return True
            return False
    
    async def register_handler(self, handler: MessageHandler) -> str:
        """Register a message handler.
        
        Args:
            handler: The message handler to register
            
        Returns:
            Handler ID for later reference
        """
        async with self._handlers_lock:
            self._message_handlers[handler.id] = handler
            logger.info(f"Registered message handler: {handler.description}")
            return handler.id
    
    async def unregister_handler(self, handler_id: str) -> bool:
        """Unregister a message handler.
        
        Args:
            handler_id: ID of the handler to unregister
            
        Returns:
            Whether the handler was unregistered
        """
        async with self._handlers_lock:
            if handler_id in self._message_handlers:
                del self._message_handlers[handler_id]
                logger.info(f"Unregistered message handler: {handler_id}")
                return True
            return False
    
    async def send(self, message: Message) -> bool:
        """Send a message.
        
        Args:
            message: Message to send
            
        Returns:
            Whether the message was sent successfully
        """
        # Mark as sent
        message.mark_sent()
        
        # Handle different message routing based on type
        if message.type == MessageType.BROADCAST:
            return await self._send_broadcast(message)
        elif message.topic:
            return await self._send_to_topic(message)
        elif message.recipient:
            return await self._send_to_agent(message)
        else:
            logger.error(f"Message has neither recipient nor topic: {message.id}")
            return False
    
    async def _send_to_agent(self, message: Message) -> bool:
        """Send a message to a specific agent.
        
        Args:
            message: Message to send
            
        Returns:
            Whether the message was sent successfully
        """
        recipient = message.recipient
        if not recipient:
            logger.error(f"Message {message.id} has no recipient")
            return False
        
        # Ensure recipient is registered
        if recipient not in self._agent_queues:
            await self.register_agent(recipient)
        
        # Add to recipient's queue
        async with self._queues_lock:
            queue = self._agent_queues.get(recipient)
            if queue:
                # Use priority as queue priority
                await queue.put((message.priority.value, message))
                
                # Update statistics
                self._update_message_stats(message)
                
                # Add to history if persistence is enabled
                if self._persistence_enabled:
                    async with self._history_lock:
                        self._message_history.append(message)
                
                logger.debug(f"Sent message {message.id} to {recipient}")
                return True
            else:
                logger.warning(f"No queue found for recipient {recipient}")
                return False
    
    async def _send_to_topic(self, message: Message) -> bool:
        """Send a message to a topic.
        
        Args:
            message: Message to send
            
        Returns:
            Whether the message was sent successfully
        """
        topic = message.topic
        if not topic:
            logger.error(f"Message {message.id} has no topic")
            return False
        
        async with self._topics_lock:
            subscribers = self._topic_subscribers.get(topic, set())
            if not subscribers:
                logger.warning(f"No subscribers for topic {topic}")
                return False
            
            # Send to all subscribers
            success = True
            for subscriber in subscribers:
                # Create a copy of the message for each subscriber
                subscriber_message = Message(
                    **message.dict(exclude={"id", "recipient"}),
                    recipient=subscriber
                )
                
                if not await self._send_to_agent(subscriber_message):
                    success = False
            
            # Update topic stats
            if topic in self._topic_stats:
                self._topic_stats[topic].message_count += 1
                self._topic_stats[topic].last_message_at = datetime.utcnow()
            
            return success
    
    async def _send_broadcast(self, message: Message) -> bool:
        """Send a broadcast message to all registered agents.
        
        Args:
            message: Message to send
            
        Returns:
            Whether the message was sent successfully
        """
        async with self._queues_lock:
            if not self._agent_queues:
                logger.warning("No agents registered for broadcast")
                return False
            
            # Send to all agents
            success = True
            for agent_name in self._agent_queues.keys():
                # Skip sender
                if agent_name == message.sender:
                    continue
                
                # Create a copy of the message for each agent
                agent_message = Message(
                    **message.dict(exclude={"id", "recipient"}),
                    recipient=agent_name
                )
                
                if not await self._send_to_agent(agent_message):
                    success = False
            
            return success
    
    async def receive(self, agent_name: str, timeout: Optional[float] = None) -> Optional[Message]:
        """Receive a message for an agent.
        
        Args:
            agent_name: Name of the agent
            timeout: Optional timeout in seconds
            
        Returns:
            Message or None if timeout occurs
        """
        # Ensure agent is registered
        if agent_name not in self._agent_queues:
            await self.register_agent(agent_name)
        
        async with self._queues_lock:
            queue = self._agent_queues.get(agent_name)
            if not queue:
                logger.warning(f"No queue found for agent {agent_name}")
                return None
            
            try:
                # Wait for message with timeout
                if timeout is not None:
                    try:
                        priority, message = await asyncio.wait_for(queue.get(), timeout)
                    except asyncio.TimeoutError:
                        return None
                else:
                    priority, message = await queue.get()
                
                # Mark as delivered
                message.mark_delivered()
                
                # Update agent stats
                if agent_name in self._agent_stats:
                    self._agent_stats[agent_name].received_count += 1
                    self._agent_stats[agent_name].last_received_at = datetime.utcnow()
                
                logger.debug(f"Agent {agent_name} received message {message.id}")
                return message
            except Exception as e:
                logger.error(f"Error receiving message for {agent_name}: {e}")
                return None
    
    async def get_messages(self, filter_: MessageFilter) -> List[Message]:
        """Get messages matching a filter from history.
        
        Args:
            filter_: Filter criteria
            
        Returns:
            List of matching messages
        """
        if not self._persistence_enabled:
            logger.warning("Message history is disabled")
            return []
        
        async with self._history_lock:
            return [msg for msg in self._message_history if filter_.matches(msg)]
    
    async def process_message_handlers(self, message: Message) -> int:
        """Process a message through all registered handlers.
        
        Args:
            message: Message to process
            
        Returns:
            Number of handlers that processed the message
        """
        async with self._handlers_lock:
            handlers = list(self._message_handlers.values())
        
        count = 0
        for handler in handlers:
            try:
                if await handler.process(message):
                    count += 1
            except Exception as e:
                logger.error(f"Error in message handler: {e}")
        
        if count > 0:
            message.mark_processed()
        
        return count
    
    def _update_message_stats(self, message: Message):
        """Update message statistics.
        
        Args:
            message: Message to update statistics for
        """
        # Update broker stats
        self._broker_stats.total_messages += 1
        
        # Update type stats
        type_str = str(message.type.value)
        if type_str in self._broker_stats.messages_by_type:
            self._broker_stats.messages_by_type[type_str] += 1
        else:
            self._broker_stats.messages_by_type[type_str] = 1
        
        # Update priority stats
        priority_str = str(message.priority.value)
        if priority_str in self._broker_stats.messages_by_priority:
            self._broker_stats.messages_by_priority[priority_str] += 1
        else:
            self._broker_stats.messages_by_priority[priority_str] = 1
        
        # Update sender stats
        if message.sender in self._agent_stats:
            self._agent_stats[message.sender].sent_count += 1
            self._agent_stats[message.sender].last_sent_at = datetime.utcnow()
        
        # Update workflow stats
        if message.workflow_id:
            if message.workflow_id not in self._workflow_stats:
                self._workflow_stats[message.workflow_id] = WorkflowStats(workflow_id=message.workflow_id)
            
            workflow_stats = self._workflow_stats[message.workflow_id]
            workflow_stats.message_count += 1
            workflow_stats.last_message_at = datetime.utcnow()
            
            # Add participants if not already in the list
            if message.sender not in workflow_stats.agent_participants:
                workflow_stats.agent_participants.append(message.sender)
            if message.recipient and message.recipient not in workflow_stats.agent_participants:
                workflow_stats.agent_participants.append(message.recipient)
    
    async def get_broker_stats(self) -> BrokerStats:
        """Get overall broker statistics.
        
        Returns:
            Current broker statistics
        """
        return self._broker_stats
    
    async def get_agent_stats(self, agent_name: str) -> Optional[AgentStats]:
        """Get statistics for a specific agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent statistics or None if not found
        """
        return self._agent_stats.get(agent_name)
    
    async def get_topic_stats(self, topic: str) -> Optional[TopicStats]:
        """Get statistics for a specific topic.
        
        Args:
            topic: Topic name
            
        Returns:
            Topic statistics or None if not found
        """
        return self._topic_stats.get(topic)
    
    async def get_workflow_stats(self, workflow_id: str) -> Optional[WorkflowStats]:
        """Get statistics for a specific workflow.
        
        Args:
            workflow_id: Workflow ID
            
        Returns:
            Workflow statistics or None if not found
        """
        return self._workflow_stats.get(workflow_id)
    
    async def clear_agent_queue(self, agent_name: str) -> int:
        """Clear an agent's message queue.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Number of messages cleared
        """
        async with self._queues_lock:
            if agent_name not in self._agent_queues:
                return 0
            
            queue = self._agent_queues[agent_name]
            count = queue.qsize()
            
            # Create a new empty queue
            self._agent_queues[agent_name] = asyncio.PriorityQueue()
            
            return count
    
    async def shutdown(self):
        """Shutdown the message broker cleanly."""
        self._active = False
        
        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self._stats_task:
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Message broker shut down")


# Global instance
message_broker = MessageBroker()
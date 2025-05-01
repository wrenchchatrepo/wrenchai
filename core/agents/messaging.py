"""
Agent messaging module for enhanced communication patterns.

This module provides interfaces and adapters for agents to communicate 
using the enhanced message broker system.
"""

import asyncio
import logging
from typing import Dict, List, Set, Any, Optional, Union, Callable, TypeVar, Awaitable
from datetime import datetime, timedelta
import uuid

from core.tools.message_broker import (
    MessageBroker,
    Message,
    MessageType,
    MessagePriority,
    MessageFilter,
    MessageHandler,
    message_broker
)

logger = logging.getLogger(__name__)

# Type for message callback functions
T_MessageCallback = Callable[[Message], Awaitable[None]]


class MessagingCapability:
    """Messaging capability for agents."""
    
    def __init__(self, agent_name: str, broker: Optional[MessageBroker] = None):
        """Initialize the messaging capability.
        
        Args:
            agent_name: Name of the agent
            broker: Optional message broker to use (defaults to global)
        """
        self.agent_name = agent_name
        self.broker = broker or message_broker
        self.subscribed_topics: Set[str] = set()
        self.registered_handlers: Dict[str, MessageHandler] = {}
        self.active = False
        self.listener_task = None
    
    async def initialize(self):
        """Initialize the messaging capability."""
        # Register with broker
        await self.broker.register_agent(self.agent_name)
        self.active = True
        logger.info(f"Initialized messaging for agent {self.agent_name}")
    
    async def shutdown(self):
        """Shut down the messaging capability."""
        # Stop message listener if running
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass
            self.listener_task = None
        
        # Unregister from broker
        await self.broker.unregister_agent(self.agent_name)
        
        # Unregister all handlers
        for handler_id in list(self.registered_handlers.keys()):
            await self.broker.unregister_handler(handler_id)
        self.registered_handlers.clear()
        
        self.active = False
        logger.info(f"Shut down messaging for agent {self.agent_name}")
    
    async def send_message(
        self,
        recipient: str,
        content: Any,
        message_type: MessageType = MessageType.TEXT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        ttl: Optional[int] = None,
        trace_id: Optional[str] = None
    ) -> Optional[str]:
        """Send a direct message to another agent.
        
        Args:
            recipient: Recipient agent name
            content: Message content
            message_type: Type of message
            priority: Message priority
            metadata: Additional metadata
            workflow_id: Optional workflow ID
            ttl: Time-to-live in seconds
            trace_id: Optional trace ID for distributed tracing
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return None
        
        # Create message
        message = Message(
            sender=self.agent_name,
            recipient=recipient,
            content=content,
            type=message_type,
            priority=priority,
            metadata=metadata or {},
            workflow_id=workflow_id,
            trace_id=trace_id or str(uuid.uuid4())
        )
        
        # Set expiration if TTL is provided
        if ttl is not None:
            message.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Send the message
        success = await self.broker.send(message)
        
        if success:
            return message.id
        return None
    
    async def broadcast_message(
        self,
        content: Any,
        message_type: MessageType = MessageType.BROADCAST,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        ttl: Optional[int] = None,
        trace_id: Optional[str] = None
    ) -> Optional[str]:
        """Broadcast a message to all agents.
        
        Args:
            content: Message content
            message_type: Type of message
            priority: Message priority
            metadata: Additional metadata
            workflow_id: Optional workflow ID
            ttl: Time-to-live in seconds
            trace_id: Optional trace ID for distributed tracing
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return None
        
        # Create message (recipient=None for broadcast)
        message = Message(
            sender=self.agent_name,
            recipient=None,
            content=content,
            type=MessageType.BROADCAST,
            priority=priority,
            metadata=metadata or {},
            workflow_id=workflow_id,
            trace_id=trace_id or str(uuid.uuid4())
        )
        
        # Set expiration if TTL is provided
        if ttl is not None:
            message.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Send the message
        success = await self.broker.send(message)
        
        if success:
            return message.id
        return None
    
    async def publish_to_topic(
        self,
        topic: str,
        content: Any,
        message_type: MessageType = MessageType.TEXT,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        ttl: Optional[int] = None,
        trace_id: Optional[str] = None
    ) -> Optional[str]:
        """Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            content: Message content
            message_type: Type of message
            priority: Message priority
            metadata: Additional metadata
            workflow_id: Optional workflow ID
            ttl: Time-to-live in seconds
            trace_id: Optional trace ID for distributed tracing
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return None
        
        # Create message
        message = Message(
            sender=self.agent_name,
            recipient=None,
            topic=topic,
            content=content,
            type=message_type,
            priority=priority,
            metadata=metadata or {},
            workflow_id=workflow_id,
            trace_id=trace_id or str(uuid.uuid4())
        )
        
        # Set expiration if TTL is provided
        if ttl is not None:
            message.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Send the message
        success = await self.broker.send(message)
        
        if success:
            return message.id
        return None
    
    async def reply_to_message(
        self,
        original_message: Message,
        content: Any,
        message_type: MessageType = MessageType.RESPONSE,
        priority: Optional[MessagePriority] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None
    ) -> Optional[str]:
        """Reply to a message.
        
        Args:
            original_message: Original message to reply to
            content: Reply content
            message_type: Type of message
            priority: Message priority (defaults to same as original)
            metadata: Additional metadata
            ttl: Time-to-live in seconds
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return None
        
        # Create reply message
        reply = original_message.create_reply(content, message_type)
        
        # Set priority (defaults to same as original)
        if priority is not None:
            reply.priority = priority
        
        # Add metadata if provided
        if metadata:
            reply.metadata.update(metadata)
        
        # Set expiration if TTL is provided
        if ttl is not None:
            reply.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Send the reply
        success = await self.broker.send(reply)
        
        if success:
            return reply.id
        return None
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Receive a message.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Received message or None if timeout occurs
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return None
        
        return await self.broker.receive(self.agent_name, timeout)
    
    async def receive_and_process(self, timeout: Optional[float] = None) -> Optional[Message]:
        """Receive a message and process it through handlers.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Received message or None if timeout occurs
        """
        message = await self.receive_message(timeout)
        if message:
            await self.broker.process_message_handlers(message)
        return message
    
    async def start_message_listener(self, callback: Optional[T_MessageCallback] = None):
        """Start a background task to listen for messages.
        
        Args:
            callback: Optional callback function for received messages
        """
        if self.listener_task and not self.listener_task.done():
            logger.warning(f"Message listener for agent {self.agent_name} already running")
            return
        
        # Define the listener task
        async def listener_loop():
            logger.info(f"Started message listener for agent {self.agent_name}")
            while self.active:
                try:
                    message = await self.broker.receive(self.agent_name)
                    if message:
                        # Process through handlers
                        await self.broker.process_message_handlers(message)
                        
                        # Call callback if provided
                        if callback:
                            try:
                                await callback(message)
                            except Exception as e:
                                logger.error(f"Error in message callback: {e}")
                except asyncio.CancelledError:
                    logger.info(f"Message listener for agent {self.agent_name} cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in message listener: {e}")
                    # Brief pause to avoid tight loop on error
                    await asyncio.sleep(0.1)
        
        # Start the listener task
        self.listener_task = asyncio.create_task(listener_loop())
    
    async def subscribe_to_topic(self, topic: str) -> bool:
        """Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            
        Returns:
            Whether the subscription was successful
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return False
        
        success = await self.broker.subscribe_to_topic(self.agent_name, topic)
        if success:
            self.subscribed_topics.add(topic)
        return success
    
    async def unsubscribe_from_topic(self, topic: str) -> bool:
        """Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            
        Returns:
            Whether the unsubscription was successful
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return False
        
        success = await self.broker.unsubscribe_from_topic(self.agent_name, topic)
        if success:
            self.subscribed_topics.discard(topic)
        return success
    
    async def register_message_handler(
        self,
        callback: T_MessageCallback,
        sender: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        topic: Optional[str] = None,
        workflow_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Register a message handler.
        
        Args:
            callback: Callback function for matching messages
            sender: Optional sender filter
            message_type: Optional message type filter
            topic: Optional topic filter
            workflow_id: Optional workflow ID filter
            description: Optional description of the handler
            
        Returns:
            Handler ID for later reference
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return ""
        
        # Create filter
        filter_ = MessageFilter(
            recipient=self.agent_name,  # Always filter for this agent
            sender=sender,
            type=message_type,
            topic=topic,
            workflow_id=workflow_id
        )
        
        # Create handler
        handler = MessageHandler(
            callback=callback,
            filter_=filter_,
            description=description or f"Handler for {self.agent_name}"
        )
        
        # Register with broker
        handler_id = await self.broker.register_handler(handler)
        
        # Store locally
        self.registered_handlers[handler_id] = handler
        
        return handler_id
    
    async def unregister_message_handler(self, handler_id: str) -> bool:
        """Unregister a message handler.
        
        Args:
            handler_id: ID of the handler to unregister
            
        Returns:
            Whether the handler was unregistered
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return False
        
        success = await self.broker.unregister_handler(handler_id)
        if success and handler_id in self.registered_handlers:
            del self.registered_handlers[handler_id]
        return success
    
    async def get_message_history(
        self,
        sender: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        topic: Optional[str] = None,
        workflow_id: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None
    ) -> List[Message]:
        """Get message history filtered by criteria.
        
        Args:
            sender: Optional sender filter
            message_type: Optional message type filter
            topic: Optional topic filter
            workflow_id: Optional workflow ID filter
            since: Optional start time
            until: Optional end time
            
        Returns:
            List of matching messages
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return []
        
        # Create filter (recipient can be None to get all messages)
        filter_ = MessageFilter(
            recipient=self.agent_name,
            sender=sender,
            type=message_type,
            topic=topic,
            workflow_id=workflow_id,
            since=since,
            until=until
        )
        
        return await self.broker.get_messages(filter_)
    
    async def clear_message_queue(self) -> int:
        """Clear the agent's message queue.
        
        Returns:
            Number of messages cleared
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return 0
        
        return await self.broker.clear_agent_queue(self.agent_name)
    
    async def get_messaging_stats(self) -> Dict[str, Any]:
        """Get messaging statistics for this agent.
        
        Returns:
            Dictionary of statistics
        """
        if not self.active:
            logger.warning(f"Messaging for agent {self.agent_name} is not active")
            return {}
        
        agent_stats = await self.broker.get_agent_stats(self.agent_name)
        if not agent_stats:
            return {}
        
        return {
            "sent_count": agent_stats.sent_count,
            "received_count": agent_stats.received_count,
            "last_sent_at": agent_stats.last_sent_at,
            "last_received_at": agent_stats.last_received_at,
            "subscribed_topics": agent_stats.subscribed_topics,
            "active_handlers": len(self.registered_handlers)
        }
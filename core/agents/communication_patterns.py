"""
Agent communication patterns module.

This module provides reusable communication patterns for agent interactions,
supporting complex workflows and collaboration scenarios.
"""

import asyncio
import logging
import traceback
from typing import Dict, List, Set, Any, Optional, Union, Callable, TypeVar, Awaitable
from datetime import datetime, timedelta
import uuid
import json

from core.tools.message_broker import (
    message_broker,
    Message,
    MessageType,
    MessagePriority,
    MessageStatus
)
from .messaging import MessagingCapability

logger = logging.getLogger(__name__)

# Type definitions
T_ProcessFunc = Callable[[Message], Awaitable[Any]]
T_ConditionFunc = Callable[[Message], Awaitable[bool]]
T = TypeVar('T')


class RequestResponse:
    """Request-response pattern for synchronous communication."""
    
    def __init__(self, messaging: MessagingCapability, timeout: float = 30.0):
        """Initialize request-response pattern.
        
        Args:
            messaging: Messaging capability to use
            timeout: Default timeout for requests in seconds
        """
        self.messaging = messaging
        self.default_timeout = timeout
        self.pending_requests: Dict[str, asyncio.Future] = {}
    
    async def initialize(self):
        """Initialize the pattern."""
        # Register handler for responses
        await self.messaging.register_message_handler(
            callback=self._handle_response,
            message_type=MessageType.RESPONSE,
            description="Request-Response handler"
        )
    
    async def _handle_response(self, message: Message):
        """Handle response messages.
        
        Args:
            message: Response message
        """
        # Check if this is a response to a pending request
        if message.reply_to and message.reply_to in self.pending_requests:
            future = self.pending_requests[message.reply_to]
            if not future.done():
                future.set_result(message)
    
    async def request(
        self,
        recipient: str,
        content: Any,
        timeout: Optional[float] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Optional[Message]:
        """Send a request and wait for a response.
        
        Args:
            recipient: Recipient agent name
            content: Request content
            timeout: Optional timeout in seconds (overrides default)
            priority: Message priority
            metadata: Additional metadata
            workflow_id: Optional workflow ID
            
        Returns:
            Response message or None if timeout occurs
        """
        # Create a future for the response
        response_future = asyncio.get_event_loop().create_future()
        
        # Send the request
        request_id = await self.messaging.send_message(
            recipient=recipient,
            content=content,
            message_type=MessageType.COMMAND,
            priority=priority,
            metadata=metadata,
            workflow_id=workflow_id
        )
        
        if not request_id:
            logger.error("Failed to send request")
            return None
        
        # Store the future
        self.pending_requests[request_id] = response_future
        
        try:
            # Wait for the response with timeout
            actual_timeout = timeout or self.default_timeout
            response = await asyncio.wait_for(response_future, actual_timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request {request_id} timed out after {actual_timeout}s")
            return None
        finally:
            # Clean up
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]


class PubSub:
    """Publish-subscribe pattern for topic-based messaging."""
    
    def __init__(self, messaging: MessagingCapability):
        """Initialize pub-sub pattern.
        
        Args:
            messaging: Messaging capability to use
        """
        self.messaging = messaging
        self.topic_handlers: Dict[str, List[T_ProcessFunc]] = {}
    
    async def initialize(self):
        """Initialize the pattern."""
        # Register handler for topic messages
        await self.messaging.register_message_handler(
            callback=self._handle_topic_message,
            description="PubSub topic handler"
        )
    
    async def _handle_topic_message(self, message: Message):
        """Handle topic messages.
        
        Args:
            message: Topic message
        """
        if not message.topic:
            return
        
        # Check if we have handlers for this topic
        if message.topic in self.topic_handlers:
            for handler in self.topic_handlers[message.topic]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in topic handler: {e}")
    
    async def subscribe(self, topic: str, handler: T_ProcessFunc) -> bool:
        """Subscribe to a topic with a handler.
        
        Args:
            topic: Topic to subscribe to
            handler: Handler function for messages
            
        Returns:
            Whether the subscription was successful
        """
        # Subscribe to the topic
        success = await self.messaging.subscribe_to_topic(topic)
        if not success:
            return False
        
        # Register the handler
        if topic not in self.topic_handlers:
            self.topic_handlers[topic] = []
        
        self.topic_handlers[topic].append(handler)
        return True
    
    async def unsubscribe(self, topic: str, handler: Optional[T_ProcessFunc] = None) -> bool:
        """Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            handler: Optional specific handler to remove (if None, removes all)
            
        Returns:
            Whether the unsubscription was successful
        """
        # Remove specific handler or all handlers
        if topic in self.topic_handlers:
            if handler:
                if handler in self.topic_handlers[topic]:
                    self.topic_handlers[topic].remove(handler)
            else:
                self.topic_handlers[topic] = []
        
        # If no handlers left, unsubscribe from topic
        if topic not in self.topic_handlers or not self.topic_handlers[topic]:
            return await self.messaging.unsubscribe_from_topic(topic)
        
        return True
    
    async def publish(
        self,
        topic: str,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None
    ) -> Optional[str]:
        """Publish a message to a topic.
        
        Args:
            topic: Topic to publish to
            content: Message content
            priority: Message priority
            metadata: Additional metadata
            workflow_id: Optional workflow ID
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        return await self.messaging.publish_to_topic(
            topic=topic,
            content=content,
            priority=priority,
            metadata=metadata,
            workflow_id=workflow_id
        )


class EventBus:
    """Event bus pattern for decoupled event handling."""
    
    def __init__(self, messaging: MessagingCapability):
        """Initialize event bus pattern.
        
        Args:
            messaging: Messaging capability to use
        """
        self.messaging = messaging
        self.event_handlers: Dict[str, List[T_ProcessFunc]] = {}
    
    async def initialize(self):
        """Initialize the pattern."""
        # Register handler for event messages
        await self.messaging.register_message_handler(
            callback=self._handle_event,
            message_type=MessageType.EVENT,
            description="EventBus handler"
        )
    
    async def _handle_event(self, message: Message):
        """Handle event messages.
        
        Args:
            message: Event message
        """
        # Extract event type from metadata
        event_type = message.metadata.get("event_type")
        if not event_type:
            return
        
        # Check if we have handlers for this event type
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    await handler(message)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
    
    async def register_handler(self, event_type: str, handler: T_ProcessFunc) -> bool:
        """Register a handler for an event type.
        
        Args:
            event_type: Event type to handle
            handler: Handler function
            
        Returns:
            Whether the registration was successful
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
        return True
    
    async def unregister_handler(self, event_type: str, handler: T_ProcessFunc) -> bool:
        """Unregister a handler for an event type.
        
        Args:
            event_type: Event type
            handler: Handler function
            
        Returns:
            Whether the unregistration was successful
        """
        if event_type in self.event_handlers and handler in self.event_handlers[event_type]:
            self.event_handlers[event_type].remove(handler)
            return True
        return False
    
    async def emit_event(
        self,
        event_type: str,
        data: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        workflow_id: Optional[str] = None
    ) -> Optional[str]:
        """Emit an event.
        
        Args:
            event_type: Event type
            data: Event data
            priority: Event priority
            workflow_id: Optional workflow ID
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        # Create metadata with event type
        metadata = {"event_type": event_type}
        
        return await self.messaging.broadcast_message(
            content=data,
            message_type=MessageType.EVENT,
            priority=priority,
            metadata=metadata,
            workflow_id=workflow_id
        )


class WorkflowMessaging:
    """Workflow-oriented messaging pattern."""
    
    def __init__(self, messaging: MessagingCapability):
        """Initialize workflow messaging pattern.
        
        Args:
            messaging: Messaging capability to use
        """
        self.messaging = messaging
        self.workflow_handlers: Dict[str, T_ProcessFunc] = {}
        self.step_handlers: Dict[str, Dict[str, T_ProcessFunc]] = {}
    
    async def initialize(self):
        """Initialize the pattern."""
        # Register handler for workflow messages
        await self.messaging.register_message_handler(
            callback=self._handle_workflow_message,
            message_type=MessageType.WORKFLOW,
            description="Workflow message handler"
        )
    
    async def _handle_workflow_message(self, message: Message):
        """Handle workflow messages.
        
        Args:
            message: Workflow message
        """
        if not message.workflow_id:
            return
        
        # Extract step ID from metadata
        step_id = message.metadata.get("step_id")
        
        # Call step handler if available
        if step_id and message.workflow_id in self.step_handlers:
            if step_id in self.step_handlers[message.workflow_id]:
                try:
                    await self.step_handlers[message.workflow_id][step_id](message)
                except Exception as e:
                    logger.error(f"Error in step handler: {e}")
        
        # Call workflow handler if available
        if message.workflow_id in self.workflow_handlers:
            try:
                await self.workflow_handlers[message.workflow_id](message)
            except Exception as e:
                logger.error(f"Error in workflow handler: {e}")
    
    async def register_workflow_handler(self, workflow_id: str, handler: T_ProcessFunc) -> bool:
        """Register a handler for a workflow.
        
        Args:
            workflow_id: Workflow ID
            handler: Handler function
            
        Returns:
            Whether the registration was successful
        """
        self.workflow_handlers[workflow_id] = handler
        return True
    
    async def register_step_handler(self, workflow_id: str, step_id: str, handler: T_ProcessFunc) -> bool:
        """Register a handler for a workflow step.
        
        Args:
            workflow_id: Workflow ID
            step_id: Step ID
            handler: Handler function
            
        Returns:
            Whether the registration was successful
        """
        if workflow_id not in self.step_handlers:
            self.step_handlers[workflow_id] = {}
        
        self.step_handlers[workflow_id][step_id] = handler
        return True
    
    async def send_workflow_message(
        self,
        recipient: str,
        workflow_id: str,
        content: Any,
        step_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Send a workflow message.
        
        Args:
            recipient: Recipient agent
            workflow_id: Workflow ID
            content: Message content
            step_id: Optional step ID
            priority: Message priority
            metadata: Additional metadata
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        # Prepare metadata
        actual_metadata = metadata or {}
        if step_id:
            actual_metadata["step_id"] = step_id
        
        return await self.messaging.send_message(
            recipient=recipient,
            content=content,
            message_type=MessageType.WORKFLOW,
            priority=priority,
            metadata=actual_metadata,
            workflow_id=workflow_id
        )
    
    async def broadcast_workflow_message(
        self,
        workflow_id: str,
        content: Any,
        step_id: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Broadcast a workflow message to all participants.
        
        Args:
            workflow_id: Workflow ID
            content: Message content
            step_id: Optional step ID
            priority: Message priority
            metadata: Additional metadata
            
        Returns:
            Message ID if sent successfully, None otherwise
        """
        # Prepare metadata
        actual_metadata = metadata or {}
        if step_id:
            actual_metadata["step_id"] = step_id
        
        return await self.messaging.broadcast_message(
            content=content,
            message_type=MessageType.WORKFLOW,
            priority=priority,
            metadata=actual_metadata,
            workflow_id=workflow_id
        )


class ConditionalRouter:
    """Conditional message routing pattern."""
    
    def __init__(self, messaging: MessagingCapability):
        """Initialize conditional router pattern.
        
        Args:
            messaging: Messaging capability to use
        """
        self.messaging = messaging
        self.routes: List[Dict[str, Any]] = []
    
    async def initialize(self):
        """Initialize the pattern."""
        # Register handler for messages
        await self.messaging.register_message_handler(
            callback=self._handle_message,
            description="Conditional router handler"
        )
    
    async def _handle_message(self, message: Message):
        """Handle and route messages.
        
        Args:
            message: Message to route
        """
        # Check each route
        for route in self.routes:
            condition = route["condition"]
            try:
                # Evaluate condition
                matches = await condition(message)
                if matches:
                    # Route to destination
                    await route["handler"](message)
                    
                    # Stop at first match if exclusive
                    if route.get("exclusive", True):
                        break
            except Exception as e:
                logger.error(f"Error in conditional route: {e}")
    
    async def add_route(
        self,
        condition: T_ConditionFunc,
        handler: T_ProcessFunc,
        exclusive: bool = True,
        description: Optional[str] = None
    ) -> int:
        """Add a conditional route.
        
        Args:
            condition: Condition function that returns True if route should be taken
            handler: Handler function for matching messages
            exclusive: Whether to stop routing after this route is taken
            description: Optional description of the route
            
        Returns:
            Route ID (index in routes list)
        """
        route = {
            "condition": condition,
            "handler": handler,
            "exclusive": exclusive,
            "description": description or f"Route {len(self.routes)}"
        }
        
        self.routes.append(route)
        return len(self.routes) - 1
    
    async def remove_route(self, route_id: int) -> bool:
        """Remove a route.
        
        Args:
            route_id: ID of the route to remove
            
        Returns:
            Whether the removal was successful
        """
        if 0 <= route_id < len(self.routes):
            del self.routes[route_id]
            return True
        return False


class AgentPool:
    """Agent pool pattern for workload distribution."""
    
    def __init__(self, messaging: MessagingCapability, pool_name: str):
        """Initialize agent pool pattern.
        
        Args:
            messaging: Messaging capability to use
            pool_name: Name of the pool (used as topic)
        """
        self.messaging = messaging
        self.pool_name = pool_name
        self.pool_topic = f"pool:{pool_name}"
        self.is_worker = False
        self.work_handler: Optional[T_ProcessFunc] = None
    
    async def initialize(self):
        """Initialize the pattern."""
        # Subscribe to the pool topic
        await self.messaging.subscribe_to_topic(self.pool_topic)
    
    async def join_as_worker(self, work_handler: T_ProcessFunc) -> bool:
        """Join the pool as a worker.
        
        Args:
            work_handler: Handler for work items
            
        Returns:
            Whether joining was successful
        """
        self.work_handler = work_handler
        self.is_worker = True
        
        # Register handler for work messages
        await self.messaging.register_message_handler(
            callback=self._handle_work_item,
            topic=self.pool_topic,
            description=f"Worker for pool {self.pool_name}"
        )
        
        # Announce joining the pool
        await self.messaging.publish_to_topic(
            topic=self.pool_topic,
            content={"action": "join", "agent": self.messaging.agent_name},
            message_type=MessageType.SYSTEM,
            metadata={"pool": self.pool_name}
        )
        
        return True
    
    async def leave_pool(self) -> bool:
        """Leave the pool.
        
        Returns:
            Whether leaving was successful
        """
        if self.is_worker:
            # Announce leaving the pool
            await self.messaging.publish_to_topic(
                topic=self.pool_topic,
                content={"action": "leave", "agent": self.messaging.agent_name},
                message_type=MessageType.SYSTEM,
                metadata={"pool": self.pool_name}
            )
            
            self.is_worker = False
            self.work_handler = None
        
        # Unsubscribe from the pool topic
        await self.messaging.unsubscribe_from_topic(self.pool_topic)
        
        return True
    
    async def _handle_work_item(self, message: Message):
        """Handle a work item message.
        
        Args:
            message: Work item message
        """
        if not self.is_worker or not self.work_handler:
            return
        
        # Check if this is a work item
        if message.metadata.get("message_type") == "work_item":
            try:
                # Process the work item
                result = await self.work_handler(message)
                
                # Send result back to requester
                if message.reply_to:
                    await self.messaging.reply_to_message(
                        original_message=message,
                        content=result
                    )
            except Exception as e:
                logger.error(f"Error processing work item: {e}")
                
                # Send error back to requester
                if message.reply_to:
                    await self.messaging.reply_to_message(
                        original_message=message,
                        content={"error": str(e), "traceback": traceback.format_exc()},
                        message_type=MessageType.ERROR
                    )
    
    async def submit_work(
        self,
        work_item: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        timeout: Optional[float] = 30.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Submit a work item to the pool.
        
        Args:
            work_item: Work item to process
            priority: Priority of the work item
            timeout: Timeout for waiting for result
            metadata: Additional metadata
            
        Returns:
            Work result or None if timeout occurs
        """
        # Create request/response pattern for getting the result
        request_response = RequestResponse(self.messaging, timeout)
        await request_response.initialize()
        
        # Prepare metadata
        actual_metadata = metadata or {}
        actual_metadata["message_type"] = "work_item"
        actual_metadata["pool"] = self.pool_name
        
        # Send work item to the pool
        message = await self.messaging.publish_to_topic(
            topic=self.pool_topic,
            content=work_item,
            priority=priority,
            metadata=actual_metadata
        )
        
        if not message:
            logger.error("Failed to submit work item")
            return None
        
        # Wait for the result
        response = await request_response.pending_requests.get(message, None)
        if response:
            return response.content
        
        return None


# Export patterns
__all__ = [
    "RequestResponse",
    "PubSub",
    "EventBus",
    "WorkflowMessaging",
    "ConditionalRouter",
    "AgentPool"
]
"""WebSocket Client for the WrenchAI Streamlit application.

This module provides a WebSocket client for real-time communication with the
WrenchAI backend services.
"""

import json
import asyncio
import logging
from typing import Dict, List, Any, Optional, Union, Callable, Set, TypeVar
from datetime import datetime
from enum import Enum
from urllib.parse import urlparse, urlunparse

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
import streamlit as st

from streamlit_app.utils.session_state import StateKey, get_state, set_state
from streamlit_app.utils.config_manager import get_config
from streamlit_app.utils.user_preferences import get_api_credentials, get_api_state, update_api_state

logger = logging.getLogger(__name__)

# Default WebSocket configuration
DEFAULT_RECONNECT_ATTEMPTS = 5
DEFAULT_RECONNECT_DELAY = 1.0
DEFAULT_RECONNECT_BACKOFF = 1.5
DEFAULT_PING_INTERVAL = 30.0
DEFAULT_PING_TIMEOUT = 10.0

# Event types
class WebSocketEventType(str, Enum):
    """Enum for WebSocket event types."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    MESSAGE = "message"
    ERROR = "error"
    RECONNECTING = "reconnecting"
    RECONNECTED = "reconnected"
    SUBSCRIBING = "subscribing"
    SUBSCRIBED = "subscribed"
    UNSUBSCRIBING = "unsubscribing"
    UNSUBSCRIBED = "unsubscribed"


class WebSocketEvent:
    """Event object for WebSocket events."""
    
    def __init__(
        self,
        event_type: WebSocketEventType,
        data: Optional[Any] = None,
        timestamp: Optional[datetime] = None,
        error: Optional[Exception] = None,
    ):
        """Initialize the event.
        
        Args:
            event_type: Type of event
            data: Event data
            timestamp: Event timestamp
            error: Exception if event is an error
        """
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or datetime.now()
        self.error = error
    
    def __str__(self) -> str:
        """String representation of the event."""
        if self.error:
            return f"{self.event_type.value} at {self.timestamp.isoformat()}: {str(self.error)}"
        elif self.data:
            if isinstance(self.data, dict) or isinstance(self.data, list):
                try:
                    data_str = json.dumps(self.data, indent=2)
                except Exception:
                    data_str = str(self.data)
                return f"{self.event_type.value} at {self.timestamp.isoformat()}: {data_str}"
            else:
                return f"{self.event_type.value} at {self.timestamp.isoformat()}: {str(self.data)}"
        else:
            return f"{self.event_type.value} at {self.timestamp.isoformat()}"


class WebSocketClient:
    """WebSocket client for real-time communication with the backend."""
    
    def __init__(
        self,
        websocket_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        reconnect_attempts: int = DEFAULT_RECONNECT_ATTEMPTS,
        reconnect_delay: float = DEFAULT_RECONNECT_DELAY,
        reconnect_backoff: float = DEFAULT_RECONNECT_BACKOFF,
        ping_interval: float = DEFAULT_PING_INTERVAL,
        ping_timeout: float = DEFAULT_PING_TIMEOUT,
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_event: Optional[Callable[[WebSocketEvent], None]] = None,
    ):
        """Initialize the WebSocket client.
        
        Args:
            websocket_url: WebSocket URL (defaults to config value)
            auth_token: Authentication token (defaults to stored credentials)
            reconnect_attempts: Maximum number of reconnection attempts
            reconnect_delay: Initial delay between reconnection attempts
            reconnect_backoff: Backoff multiplier for subsequent reconnection attempts
            ping_interval: Interval between ping messages
            ping_timeout: Timeout for ping responses
            on_message: Callback for received messages
            on_event: Callback for WebSocket events
        """
        # Get configuration
        config = get_config()
        
        # Set up WebSocket URL
        self.websocket_url = websocket_url or config.api.websocket_url
        
        # Get credentials if not provided
        if auth_token is None and config.api.auth_enabled:
            credentials = get_api_credentials()
            self.auth_token = credentials.token
        else:
            self.auth_token = auth_token
        
        # Set up connection parameters
        self.reconnect_attempts = reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_backoff = reconnect_backoff
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        
        # Set up callbacks
        self.on_message = on_message
        self.on_event = on_event
        
        # Set up state
        self.connection = None
        self.connected = False
        self.connecting = False
        self.reconnecting = False
        self.should_reconnect = True
        self.subscriptions: Set[str] = set()
        self.last_ping = None
        self.last_pong = None
        self.receive_task = None
        self.ping_task = None
        self.events: List[WebSocketEvent] = []
        self.max_events = 100  # Maximum number of events to keep
    
    def _add_event(self, event: WebSocketEvent) -> None:
        """Add an event to the event history.
        
        Args:
            event: Event to add
        """
        self.events.append(event)
        # Trim events if necessary
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Call event callback if provided
        if self.on_event:
            try:
                self.on_event(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")
        
        # Update WebSocket connection state in session
        api_state = get_api_state()
        
        if event.event_type == WebSocketEventType.CONNECTED:
            api_state.update_websocket_status(True)
        elif event.event_type == WebSocketEventType.DISCONNECTED:
            api_state.update_websocket_status(False, error=str(event.error) if event.error else None)
        elif event.event_type == WebSocketEventType.MESSAGE:
            api_state.ws_last_message_time = event.timestamp
        
        update_api_state(api_state)
    
    def _build_connection_url(self) -> str:
        """Build the WebSocket connection URL with authentication.
        
        Returns:
            WebSocket URL with authentication parameters
        """
        parsed_url = urlparse(self.websocket_url)
        
        # Add authentication token as query parameter if available
        query = parsed_url.query
        if self.auth_token:
            if query:
                query = f"{query}&token={self.auth_token}"
            else:
                query = f"token={self.auth_token}"
        
        # Reconstruct the URL
        return urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            query,
            parsed_url.fragment
        ))
    
    async def connect(self) -> bool:
        """Connect to the WebSocket server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self.connected:
            logger.info("WebSocket already connected")
            return True
        
        if self.connecting:
            logger.info("WebSocket connection already in progress")
            return False
        
        self.connecting = True
        self.should_reconnect = True
        
        try:
            # Build connection URL with authentication
            connection_url = self._build_connection_url()
            
            # Connect to the WebSocket server
            logger.info(f"Connecting to WebSocket at {connection_url}")
            self._add_event(WebSocketEvent(WebSocketEventType.CONNECTING))
            
            self.connection = await websockets.connect(
                connection_url,
                ping_interval=self.ping_interval,
                ping_timeout=self.ping_timeout,
            )
            
            # Update state
            self.connected = True
            self.connecting = False
            self.reconnecting = False
            
            # Start receive and ping tasks
            self.receive_task = asyncio.create_task(self._receive_messages())
            self.ping_task = asyncio.create_task(self._send_pings())
            
            # Add connected event
            self._add_event(WebSocketEvent(WebSocketEventType.CONNECTED))
            
            # Resubscribe to existing subscriptions
            for topic in self.subscriptions:
                await self.subscribe(topic)
            
            logger.info("WebSocket connected successfully")
            return True
            
        except Exception as e:
            self.connected = False
            self.connecting = False
            logger.error(f"WebSocket connection failed: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.DISCONNECTED,
                error=e
            ))
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        self.should_reconnect = False
        
        if not self.connected or not self.connection:
            logger.info("WebSocket not connected")
            return
        
        try:
            # Cancel tasks
            if self.receive_task and not self.receive_task.done():
                self.receive_task.cancel()
            
            if self.ping_task and not self.ping_task.done():
                self.ping_task.cancel()
            
            # Close the connection
            await self.connection.close()
            
            # Update state
            self.connected = False
            self._add_event(WebSocketEvent(WebSocketEventType.DISCONNECTED))
            logger.info("WebSocket disconnected")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
        
        # Always ensure we are marked as disconnected
        self.connected = False
    
    async def reconnect(self) -> bool:
        """Attempt to reconnect to the WebSocket server.
        
        Returns:
            True if reconnected successfully, False otherwise
        """
        if self.reconnecting:
            logger.info("Reconnection already in progress")
            return False
        
        self.reconnecting = True
        self._add_event(WebSocketEvent(WebSocketEventType.RECONNECTING))
        
        # Disconnect if currently connected
        if self.connected:
            await self.disconnect()
        
        # Try to reconnect with backoff
        attempts = 0
        delay = self.reconnect_delay
        
        while attempts < self.reconnect_attempts and self.should_reconnect:
            logger.info(f"Reconnection attempt {attempts + 1}/{self.reconnect_attempts}")
            
            # Wait before attempting to reconnect
            await asyncio.sleep(delay)
            
            # Attempt to connect
            if await self.connect():
                self.reconnecting = False
                self._add_event(WebSocketEvent(WebSocketEventType.RECONNECTED))
                return True
            
            # Increase backoff delay
            delay *= self.reconnect_backoff
            attempts += 1
        
        self.reconnecting = False
        logger.error(f"Failed to reconnect after {attempts} attempts")
        return False
    
    async def _receive_messages(self) -> None:
        """Background task to receive messages from the WebSocket."""
        if not self.connection:
            logger.error("Cannot receive messages: WebSocket not connected")
            return
        
        try:
            async for message in self.connection:
                try:
                    # Parse the message as JSON
                    data = json.loads(message)
                    
                    # Add message event
                    self._add_event(WebSocketEvent(
                        event_type=WebSocketEventType.MESSAGE,
                        data=data
                    ))
                    
                    # Call message callback if provided
                    if self.on_message:
                        await asyncio.create_task(self._call_message_callback(data))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Received non-JSON message: {message}")
                    # Still add as a message event with raw data
                    self._add_event(WebSocketEvent(
                        event_type=WebSocketEventType.MESSAGE,
                        data={"raw": message}
                    ))
                
        except ConnectionClosed as e:
            logger.info(f"WebSocket connection closed: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.DISCONNECTED,
                error=e
            ))
            self.connected = False
            
            # Attempt to reconnect if configured
            if self.should_reconnect:
                await self.reconnect()
                
        except Exception as e:
            logger.error(f"Error in WebSocket receive loop: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
            self.connected = False
            
            # Attempt to reconnect if configured
            if self.should_reconnect:
                await self.reconnect()
    
    async def _call_message_callback(self, data: Dict[str, Any]) -> None:
        """Call the message callback with error handling.
        
        Args:
            data: Message data
        """
        try:
            # Call the callback
            if asyncio.iscoroutinefunction(self.on_message):
                await self.on_message(data)
            else:
                self.on_message(data)
        except Exception as e:
            logger.error(f"Error in message callback: {e}")
    
    async def _send_pings(self) -> None:
        """Send periodic ping messages to keep the connection alive."""
        while self.connected and self.connection:
            try:
                # Send ping message
                await self.connection.ping()
                self.last_ping = datetime.now()
                
                # Wait for ping interval
                await asyncio.sleep(self.ping_interval)
                
            except Exception as e:
                logger.error(f"Error sending ping: {e}")
                break
    
    async def send(self, data: Dict[str, Any]) -> bool:
        """Send a message to the WebSocket server.
        
        Args:
            data: Message data as dictionary
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected or not self.connection:
            logger.error("Cannot send message: WebSocket not connected")
            return False
        
        try:
            # Convert data to JSON
            message = json.dumps(data)
            
            # Send the message
            await self.connection.send(message)
            return True
            
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
            return False
    
    async def subscribe(self, topic: str) -> bool:
        """Subscribe to a topic.
        
        Args:
            topic: Topic to subscribe to
            
        Returns:
            True if subscribed successfully, False otherwise
        """
        if not self.connected:
            logger.warning(f"Cannot subscribe to {topic}: WebSocket not connected")
            self.subscriptions.add(topic)  # Remember for later when we connect
            return False
        
        try:
            # Add subscription event
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.SUBSCRIBING,
                data={"topic": topic}
            ))
            
            # Send subscription message
            success = await self.send({
                "type": "subscribe",
                "topic": topic
            })
            
            if success:
                self.subscriptions.add(topic)
                self._add_event(WebSocketEvent(
                    event_type=WebSocketEventType.SUBSCRIBED,
                    data={"topic": topic}
                ))
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error subscribing to {topic}: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
            return False
    
    async def unsubscribe(self, topic: str) -> bool:
        """Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            
        Returns:
            True if unsubscribed successfully, False otherwise
        """
        if not self.connected:
            logger.warning(f"Cannot unsubscribe from {topic}: WebSocket not connected")
            self.subscriptions.discard(topic)  # Remove from remembered subscriptions
            return False
        
        try:
            # Add unsubscription event
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.UNSUBSCRIBING,
                data={"topic": topic}
            ))
            
            # Send unsubscription message
            success = await self.send({
                "type": "unsubscribe",
                "topic": topic
            })
            
            if success:
                self.subscriptions.discard(topic)
                self._add_event(WebSocketEvent(
                    event_type=WebSocketEventType.UNSUBSCRIBED,
                    data={"topic": topic}
                ))
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"Error unsubscribing from {topic}: {e}")
            self._add_event(WebSocketEvent(
                event_type=WebSocketEventType.ERROR,
                error=e
            ))
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the WebSocket connection.
        
        Returns:
            Dictionary with status information
        """
        return {
            "connected": self.connected,
            "connecting": self.connecting,
            "reconnecting": self.reconnecting,
            "subscriptions": list(self.subscriptions),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "last_pong": self.last_pong.isoformat() if self.last_pong else None,
            "last_event": str(self.events[-1]) if self.events else None,
            "event_count": len(self.events)
        }
    
    def get_events(self, limit: int = 10) -> List[WebSocketEvent]:
        """Get recent WebSocket events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of WebSocket events
        """
        return self.events[-limit:] if self.events else []
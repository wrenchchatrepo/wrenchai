"""Client Factory for the WrenchAI Streamlit application.

This module provides factory functions for creating API and WebSocket clients
with the appropriate configuration.
"""

import logging
from typing import Dict, List, Any, Optional, Union, Callable

import streamlit as st

from streamlit_app.utils.config_manager import get_config
from streamlit_app.utils.user_preferences import get_api_credentials, get_api_state, update_api_state
from streamlit_app.services.api_client import ApiClient
from streamlit_app.services.websocket_client import WebSocketClient, WebSocketEvent

logger = logging.getLogger(__name__)


def create_api_client(use_session: bool = True) -> ApiClient:
    """Create an API client with the appropriate configuration.
    
    Args:
        use_session: Whether to store the client in the session state
        
    Returns:
        Configured ApiClient instance
    """
    # Check if client already exists in session state
    if use_session and 'api_client' in st.session_state:
        logger.debug("Using existing API client from session state")
        return st.session_state.api_client
    
    # Get configuration
    config = get_config()
    
    # Get authentication token if needed
    auth_token = None
    if config.api.auth_enabled:
        credentials = get_api_credentials()
        auth_token = credentials.token
    
    # Create client
    client = ApiClient(
        base_url=config.api.base_url,
        timeout=config.api.timeout,
        verify_ssl=config.api.verify_ssl,
        auth_token=auth_token,
        max_retries=3,
        retry_delay=1.0,
        retry_backoff=2.0,
    )
    
    # Store in session state if requested
    if use_session:
        st.session_state.api_client = client
    
    return client


async def initialize_api_client(use_session: bool = True) -> ApiClient:
    """Initialize an API client and check the connection.
    
    Args:
        use_session: Whether to store the client in the session state
        
    Returns:
        Configured and initialized ApiClient instance
    """
    # Create the client
    client = create_api_client(use_session)
    
    # Get API state
    api_state = get_api_state()
    
    # Check connection
    try:
        # Get API version
        version = await client.get_api_version()
        logger.info(f"Connected to API version {version}")
        
        # Update API state
        api_state.update_connection_status(connected=True)
        api_state.api_version = version
        
        # Try to get API features
        try:
            features = await client.get_api_features()
            api_state.update_api_features(features)
        except Exception as e:
            logger.warning(f"Failed to get API features: {e}")
        
        # Update API state
        update_api_state(api_state)
        
    except Exception as e:
        logger.error(f"Failed to initialize API client: {e}")
        api_state.update_connection_status(connected=False, error=str(e))
        update_api_state(api_state)
    
    return client


async def create_websocket_client(
        on_message: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_event: Optional[Callable[[WebSocketEvent], None]] = None,
        auto_connect: bool = True,
        use_session: bool = True
) -> WebSocketClient:
    """Create a WebSocket client with the appropriate configuration.
    
    Args:
        on_message: Callback for received messages
        on_event: Callback for WebSocket events
        auto_connect: Whether to automatically connect the client
        use_session: Whether to store the client in the session state
        
    Returns:
        Configured WebSocketClient instance
    """
    # Check if client already exists in session state
    if use_session and 'ws_client' in st.session_state:
        logger.debug("Using existing WebSocket client from session state")
        client = st.session_state.ws_client
        
        # Update callbacks if provided
        if on_message is not None:
            client.on_message = on_message
        if on_event is not None:
            client.on_event = on_event
        
        # Connect if needed
        if auto_connect and not client.connected:
            await client.connect()
        
        return client
    
    # Get configuration
    config = get_config()
    
    # Get authentication token if needed
    auth_token = None
    if config.api.auth_enabled:
        credentials = get_api_credentials()
        auth_token = credentials.token
    
    # Create client
    client = WebSocketClient(
        websocket_url=config.api.websocket_url,
        auth_token=auth_token,
        reconnect_attempts=5,
        reconnect_delay=1.0,
        reconnect_backoff=1.5,
        ping_interval=30.0,
        ping_timeout=10.0,
        on_message=on_message,
        on_event=on_event,
    )
    
    # Connect if requested
    if auto_connect:
        await client.connect()
    
    # Store in session state if requested
    if use_session:
        st.session_state.ws_client = client
    
    return client
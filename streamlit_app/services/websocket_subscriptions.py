"""WebSocket subscription utilities for the WrenchAI Streamlit application.

This module provides utilities for subscribing to WebSocket events for various
playbook operations.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime

import streamlit as st

from streamlit_app.services.websocket_client import WebSocketClient, WebSocketEvent, WebSocketEventType
from streamlit_app.utils.session_state import StateKey, get_state, set_state

logger = logging.getLogger(__name__)


async def subscribe_to_execution(ws_client: WebSocketClient, execution_id: str) -> bool:
    """Subscribe to updates for a specific execution.
    
    Args:
        ws_client: WebSocket client
        execution_id: Execution ID to subscribe to
        
    Returns:
        True if subscribed successfully, False otherwise
    """
    # Create topic ID for the execution
    topic = f"execution:{execution_id}"
    
    # Subscribe to the topic
    return await ws_client.subscribe(topic)


async def subscribe_to_playbook(ws_client: WebSocketClient, playbook_id: str) -> bool:
    """Subscribe to updates for a specific playbook.
    
    Args:
        ws_client: WebSocket client
        playbook_id: Playbook ID to subscribe to
        
    Returns:
        True if subscribed successfully, False otherwise
    """
    # Create topic ID for the playbook
    topic = f"playbook:{playbook_id}"
    
    # Subscribe to the topic
    return await ws_client.subscribe(topic)


async def subscribe_to_executions(ws_client: WebSocketClient) -> bool:
    """Subscribe to all execution updates.
    
    Args:
        ws_client: WebSocket client
        
    Returns:
        True if subscribed successfully, False otherwise
    """
    # Create topic for all executions
    topic = "executions"
    
    # Subscribe to the topic
    return await ws_client.subscribe(topic)


async def subscribe_to_playbooks(ws_client: WebSocketClient) -> bool:
    """Subscribe to all playbook updates.
    
    Args:
        ws_client: WebSocket client
        
    Returns:
        True if subscribed successfully, False otherwise
    """
    # Create topic for all playbooks
    topic = "playbooks"
    
    # Subscribe to the topic
    return await ws_client.subscribe(topic)


def handle_execution_message(message: Dict[str, Any]) -> None:
    """Handle execution update message from WebSocket.
    
    Args:
        message: WebSocket message
    """
    # Check if the message is for an execution
    if message.get("type") != "execution-update":
        return
    
    # Get the execution data
    execution_data = message.get("data", {})
    if not execution_data:
        return
    
    # Get the execution ID
    execution_id = execution_data.get("execution_id")
    if not execution_id:
        return
    
    # Check if we're tracking this execution
    current_execution_id = get_state(StateKey.EXECUTION_ID)
    if current_execution_id and current_execution_id == execution_id:
        # Update the execution state
        set_state(StateKey.EXECUTION_STATE, execution_data.get("state"))
        
        # Update execution results if available
        if "outputs" in execution_data:
            set_state(StateKey.EXECUTION_RESULTS, execution_data.get("outputs", {}))
        
        # Update execution logs if available
        if "logs" in execution_data:
            logs = get_state(StateKey.EXECUTION_LOGS, [])
            new_logs = execution_data.get("logs", [])
            
            # Append new logs
            for log in new_logs:
                if log not in logs:
                    logs.append(log)
            
            set_state(StateKey.EXECUTION_LOGS, logs)
    
    # Update execution history
    execution_history = get_state(StateKey.EXECUTION_HISTORY, [])
    
    # Check if this execution is already in the history
    for i, history_item in enumerate(execution_history):
        if history_item.get("execution_id") == execution_id:
            # Update the history item
            execution_history[i].update({
                "state": execution_data.get("state"),
                "end_time": execution_data.get("end_time"),
                "success": execution_data.get("success", False),
            })
            set_state(StateKey.EXECUTION_HISTORY, execution_history)
            return
    
    # If not in history, add a new entry
    if len(execution_history) >= 20:
        execution_history = execution_history[1:]  # Remove oldest entry
    
    execution_history.append({
        "execution_id": execution_id,
        "playbook_id": execution_data.get("playbook_id"),
        "state": execution_data.get("state"),
        "timestamp": datetime.now().isoformat(),
        "start_time": execution_data.get("start_time"),
        "end_time": execution_data.get("end_time"),
        "success": execution_data.get("success", False),
    })
    
    set_state(StateKey.EXECUTION_HISTORY, execution_history)


def handle_playbook_message(message: Dict[str, Any]) -> None:
    """Handle playbook update message from WebSocket.
    
    Args:
        message: WebSocket message
    """
    # Check if the message is for a playbook
    if message.get("type") != "playbook-update":
        return
    
    # Get the playbook data
    playbook_data = message.get("data", {})
    if not playbook_data:
        return
    
    # Get the playbook ID
    playbook_id = playbook_data.get("id")
    if not playbook_id:
        return
    
    # Check if we're tracking this playbook
    current_playbook_id = get_state(StateKey.SELECTED_PLAYBOOK)
    if current_playbook_id and current_playbook_id == playbook_id:
        # Update the selected playbook
        set_state("playbook_details", playbook_data)
    
    # Update playbook list
    playbook_list = get_state(StateKey.PLAYBOOK_LIST, [])
    
    # Check if this playbook is already in the list
    for i, playbook in enumerate(playbook_list):
        if playbook.get("id") == playbook_id:
            # Update the playbook
            playbook_list[i] = playbook_data
            set_state(StateKey.PLAYBOOK_LIST, playbook_list)
            return
    
    # If not in list, add it
    playbook_list.append(playbook_data)
    set_state(StateKey.PLAYBOOK_LIST, playbook_list)


def setup_websocket_handler(client: WebSocketClient) -> None:
    """Set up message handler for WebSocket client.
    
    Args:
        client: WebSocket client to set up
    """
    # Define the message handler
    async def handle_message(message: Dict[str, Any]) -> None:
        try:
            # Handle different message types
            message_type = message.get("type")
            
            if "execution" in message_type:
                handle_execution_message(message)
            elif "playbook" in message_type:
                handle_playbook_message(message)
                
        except Exception as e:
            logger.error(f"Error handling WebSocket message: {e}")
    
    # Set the message handler
    client.on_message = handle_message
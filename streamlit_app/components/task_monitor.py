"""Streamlit component for real-time task monitoring."""

import json
import asyncio
import websockets
from typing import Optional, Dict, Any
import streamlit as st
from datetime import datetime
from .error_handler import ErrorHandler, with_error_handling

class TaskMonitor:
    """Real-time task monitor component."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initializes the TaskMonitor with a WebSocket URL and error handler.
        
        Args:
            api_url: The base API URL to connect for task monitoring. Defaults to "http://localhost:8000".
        """
        self.api_url = api_url.replace("http", "ws")
        self.ws = None
        self.error_handler = ErrorHandler()
        
    @with_error_handling()
    async def connect_task(self, task_id: str):
        """
        Establishes an asynchronous WebSocket connection for real-time updates of a specific task.
        
        Args:
            task_id: The unique identifier of the task to monitor.
        
        Returns:
            True if the WebSocket connection is successfully established.
        """
        self.ws = await websockets.connect(
            f"{self.api_url}/api/v1/ws/tasks/{task_id}"
        )
        return True
            
    @with_error_handling()
    async def connect_agent_tasks(self, agent_id: str):
        """
        Asynchronously connects to the WebSocket endpoint for monitoring all tasks of a specific agent.
        
        Args:
            agent_id: The unique identifier of the agent whose tasks will be monitored.
        
        Returns:
            True if the connection is successfully established.
        """
        self.ws = await websockets.connect(
            f"{self.api_url}/api/v1/ws/agents/{agent_id}/tasks"
        )
        return True
            
    async def disconnect(self):
        """
        Closes the active WebSocket connection and resets the connection state.
        
        If an error occurs during disconnection, it is handled by the error handler.
        """
        if self.ws:
            try:
                await self.ws.close()
            except Exception as e:
                self.error_handler.handle_websocket_error(e)
            finally:
                self.ws = None
            
    @with_error_handling()
    async def send_ping(self):
        """
        Sends a ping message over the WebSocket connection to keep it alive.
        
        Returns:
            True if a pong response is received, False otherwise.
        """
        if self.ws:
            await self.ws.send(json.dumps({"type": "ping"}))
            response = await self.ws.recv()
            return json.loads(response).get("type") == "pong"
        return False
        
    def render_task_progress(self, task: Dict[str, Any]):
        """
        Displays the progress and details of a task in the Streamlit UI.
        
        Shows task type, ID, progress percentage, status with color-coded icon, optional message, and expandable sections for result or error details.
        """
        try:
            with st.container():
                # Header
                col1, col2 = st.columns([3, 1])
                with col1:
                    task_type = task.get('type', 'Unknown')
                    st.subheader(f"Task: {task_type}")
                    st.caption(f"ID: {task['task_id']}")
                with col2:
                    st.metric("Progress", f"{task['progress']}%")
                    
                # Progress bar
                st.progress(task["progress"] / 100.0)
                
                # Status and message
                status_color = {
                    "pending": "🟡",
                    "running": "🔵",
                    "completed": "🟢",
                    "failed": "🔴"
                }.get(task["status"], "⚪")
                st.write(f"Status: {status_color} {task['status']}")
                
                if task.get("message"):
                    st.info(task["message"])
                    
                # Step details if available
                if task.get("step_details"):
                    with st.expander("Current Step Details", expanded=False):
                        step_details = task["step_details"]
                        if isinstance(step_details, dict):
                            st.markdown(f"**Step Name:** {step_details.get('name', 'N/A')}")
                            st.markdown(f"**Action:** {step_details.get('action', 'N/A')}")
                            
                            # Parameters
                            if step_details.get('params'):
                                st.markdown("**Parameters:**")
                                st.json(step_details['params'])
                    
                # Results or errors
                if task.get("result"):
                    with st.expander("Result"):
                        st.json(task["result"])
                        
                if task.get("error"):
                    with st.expander("Error", expanded=True):
                        st.error(task["error"])
        except Exception as e:
            st.error(f"Error rendering task progress: {str(e)}")
                    
    @with_error_handling()
    async def monitor_task(self, task_id: str, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Asynchronously monitors a single task, receiving real-time updates via WebSocket and rendering progress in the Streamlit UI.
        
        Continuously listens for task status updates, updates the UI accordingly, and exits when the task is completed or failed. Handles connection closures with retry logic and ensures clean disconnection on exit.
        
        Args:
            task_id: The unique identifier of the task to monitor.
            max_retries: Maximum number of reconnection attempts on failure
            retry_delay: Delay in seconds between reconnection attempts
        """
        retries = 0
        placeholder = st.empty()
        reconnect_msg = st.empty()
        
        # Set up ping timer task
        ping_task = None
        
        async def send_ping_periodically():
            """Send periodic ping messages to keep connection alive"""
            while True:
                try:
                    if self.ws and not self.ws.closed:
                        await self.ws.send(json.dumps({"type": "ping"}))
                    await asyncio.sleep(25)  # Ping every 25 seconds
                except Exception:
                    # Just exit on any error
                    break
        
        while retries <= max_retries:
            try:
                if not self.ws or self.ws.closed:
                    if retries > 0:
                        reconnect_msg.info(f"Reconnecting... (Attempt {retries}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                    await self.connect_task(task_id)
                    reconnect_msg.empty()
                    
                    # Start ping task after connection
                    if ping_task:
                        ping_task.cancel()
                    ping_task = asyncio.create_task(send_ping_periodically())
                    
                while True:
                    # Receive update
                    data = await self.ws.recv()
                    update = json.loads(data)
                    
                    # Handle pong messages
                    if update.get("type") == "pong":
                        continue
                    
                    # Handle ping messages
                    if update.get("type") == "ping":
                        if self.ws and not self.ws.closed:
                            await self.ws.send(json.dumps({"type": "pong"}))
                        continue
                    
                    # Update UI
                    with placeholder.container():
                        self.render_task_progress(update)
                        
                    # Exit if task is done
                    if update["status"] in ["completed", "failed"]:
                        if ping_task:
                            ping_task.cancel()
                        return  # Exit function completely
                        
            except websockets.exceptions.ConnectionClosed:
                retries += 1
                # Don't show error on first retry
                if retries > 1:
                    self.error_handler.handle_websocket_error(Exception("Connection closed"))
                # Cancel ping task on disconnect
                if ping_task:
                    ping_task.cancel()
                continue
            except Exception as e:
                self.error_handler.handle_websocket_error(e)
                retries += 1
                # Cancel ping task on error
                if ping_task:
                    ping_task.cancel()
                continue
                
        # Max retries reached
        st.error(f"Failed to monitor task {task_id} after {max_retries} attempts")
        if ping_task:
            ping_task.cancel()
        await self.disconnect()
                
    @with_error_handling()
    async def monitor_agent_tasks(self, agent_id: str, max_retries: int = 3, retry_delay: float = 2.0):
        """
        Monitors all tasks for a given agent in real time via WebSocket and updates the UI.
        
        Continuously receives task updates for the specified agent, maintains the latest state for each task, and renders their progress in the Streamlit interface. Handles connection closures with retry logic and ensures clean disconnection on exit.
        
        Args:
            agent_id: The unique identifier of the agent whose tasks will be monitored.
            max_retries: Maximum number of reconnection attempts on failure
            retry_delay: Delay in seconds between reconnection attempts
        """
        retries = 0
        tasks_state = {}
        reconnect_msg = st.empty()
        tasks_container = st.empty()
        
        # Set up ping timer task
        ping_task = None
        
        async def send_ping_periodically():
            """Send periodic ping messages to keep connection alive"""
            while True:
                try:
                    if self.ws and not self.ws.closed:
                        await self.ws.send(json.dumps({"type": "ping"}))
                    await asyncio.sleep(25)  # Ping every 25 seconds
                except Exception:
                    # Just exit on any error
                    break
        
        while retries <= max_retries:
            try:
                if not self.ws or self.ws.closed:
                    if retries > 0:
                        reconnect_msg.info(f"Reconnecting... (Attempt {retries}/{max_retries})")
                        await asyncio.sleep(retry_delay)
                    await self.connect_agent_tasks(agent_id)
                    reconnect_msg.empty()
                    
                    # Start ping task after connection
                    if ping_task:
                        ping_task.cancel()
                    ping_task = asyncio.create_task(send_ping_periodically())
                    
                while True:
                    # Receive update
                    data = await self.ws.recv()
                    update = json.loads(data)
                    
                    # Handle pong messages
                    if update.get("type") == "pong":
                        continue
                    
                    # Handle ping messages
                    if update.get("type") == "ping":
                        if self.ws and not self.ws.closed:
                            await self.ws.send(json.dumps({"type": "pong"}))
                        continue
                    
                    # Update tasks state
                    task_id = update["task_id"]
                    tasks_state[task_id] = update
                    
                    # Clear and redraw all tasks
                    with tasks_container.container():
                        for task in sorted(
                            tasks_state.values(),
                            key=lambda x: x.get("timestamp", ""),
                            reverse=True
                        ):
                            self.render_task_progress(task)
                            
                    # Check if all tasks are completed
                    all_completed = all(
                        task["status"] in ["completed", "failed"]
                        for task in tasks_state.values()
                    )
                    if all_completed and tasks_state:  # Ensure we have at least one task
                        if ping_task:
                            ping_task.cancel()
                        return  # Exit the function
                        
            except websockets.exceptions.ConnectionClosed:
                retries += 1
                # Don't show error on first retry
                if retries > 1:
                    self.error_handler.handle_websocket_error(Exception("Connection closed"))
                # Cancel ping task on disconnect
                if ping_task:
                    ping_task.cancel()
                continue
            except Exception as e:
                self.error_handler.handle_websocket_error(e)
                retries += 1
                # Cancel ping task on error
                if ping_task:
                    ping_task.cancel()
                continue
                
        # Max retries reached
        st.error(f"Failed to monitor agent {agent_id} tasks after {max_retries} attempts")
        if ping_task:
            ping_task.cancel()
        await self.disconnect()

def render_task_monitor(task_id: Optional[str] = None, agent_id: Optional[str] = None, max_retries: int = 3, retry_delay: float = 2.0):
    """
    Renders the real-time task monitoring component in Streamlit for a specific task or agent.
    
    If a task ID is provided, displays live progress for that task. If an agent ID is provided,
    displays live progress for all tasks associated with the agent.
    
    Args:
        task_id: The unique identifier of the task to monitor.
        agent_id: The unique identifier of the agent whose tasks will be monitored.
        max_retries: Maximum number of reconnection attempts on failure.
        retry_delay: Delay in seconds between reconnection attempts.
    """
    monitor = TaskMonitor(st.session_state.get("api_url", "http://localhost:8000"))
    
    if task_id:
        asyncio.run(monitor.monitor_task(task_id, max_retries, retry_delay))
    elif agent_id:
        asyncio.run(monitor.monitor_agent_tasks(agent_id, max_retries, retry_delay)) 
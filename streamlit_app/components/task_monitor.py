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
            api_url: The base HTTP API URL to be converted for WebSocket connections. Defaults to "http://localhost:8000".
        """
        self.api_url = api_url.replace("http", "ws")
        self.ws = None
        self.error_handler = ErrorHandler()
        
    @with_error_handling()
    async def connect_task(self, task_id: str):
        """
        Establishes a WebSocket connection to monitor a specific task in real time.
        
        Args:
            task_id: The unique identifier of the task to connect to.
        
        Returns:
            True if the connection is successfully established.
        """
        self.ws = await websockets.connect(
            f"{self.api_url}/api/v1/ws/tasks/{task_id}"
        )
        return True
            
    @with_error_handling()
    async def connect_agent_tasks(self, agent_id: str):
        """
        Asynchronously connects to the WebSocket endpoint for monitoring all tasks of a given agent.
        
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
        Closes the WebSocket connection if it is open and resets the connection state.
        
        Handles any exceptions during disconnection using the error handler.
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
        Displays the progress and status of a task in the Streamlit UI.
        
        Shows task type, ID, progress percentage, status with a colored icon, optional message, and expandable sections for result or error details.
        """
        try:
            with st.container():
                # Header
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader(f"Task: {task['type']}")
                    st.caption(f"ID: {task['id']}")
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
    async def monitor_task(self, task_id: str):
        """
        Monitors a single task in real time, updating the UI with progress and status.
        
        Continuously receives updates for the specified task via WebSocket, rendering progress in the Streamlit UI until the task is completed or failed. Handles connection closures and retries as determined by the error handler.
        """
        if await self.connect_task(task_id):
            try:
                placeholder = st.empty()
                while True:
                    try:
                        # Receive update
                        data = await self.ws.recv()
                        update = json.loads(data)
                        
                        # Update UI
                        with placeholder.container():
                            self.render_task_progress(update)
                            
                        # Exit if task is done
                        if update["status"] in ["completed", "failed"]:
                            break
                            
                    except websockets.exceptions.ConnectionClosed:
                        self.error_handler.handle_websocket_error(Exception("Connection closed"))
                        if self.error_handler.should_retry():
                            await self.connect_task(task_id)
                        else:
                            break
                        
            finally:
                await self.disconnect()
                
    @with_error_handling()
    async def monitor_agent_tasks(self, agent_id: str):
        """
        Asynchronously monitors all tasks for a given agent, displaying real-time updates in the UI.
        
        Continuously receives task updates over a WebSocket connection, maintains the latest state for each task, and renders all tasks sorted by timestamp. Handles connection closures with error management and retry logic, and disconnects when monitoring ends.
        """
        if await self.connect_agent_tasks(agent_id):
            try:
                tasks_state = {}
                while True:
                    try:
                        # Receive update
                        data = await self.ws.recv()
                        update = json.loads(data)
                        
                        # Update tasks state
                        task_id = update["task_id"]
                        tasks_state[task_id] = update
                        
                        # Clear and redraw all tasks
                        st.empty()
                        for task in sorted(
                            tasks_state.values(),
                            key=lambda x: x.get("timestamp", ""),
                            reverse=True
                        ):
                            self.render_task_progress(task)
                            
                    except websockets.exceptions.ConnectionClosed:
                        self.error_handler.handle_websocket_error(Exception("Connection closed"))
                        if self.error_handler.should_retry():
                            await self.connect_agent_tasks(agent_id)
                        else:
                            break
                        
            finally:
                await self.disconnect()

def render_task_monitor(task_id: Optional[str] = None, agent_id: Optional[str] = None):
    """
    Renders the real-time task monitoring component in the Streamlit app.
    
    Depending on the provided arguments, monitors and displays progress for either a single task or all tasks associated with a specific agent by establishing a WebSocket connection and updating the UI in real time.
    
    Args:
        task_id: The ID of the task to monitor. If provided, monitors only this task.
        agent_id: The ID of the agent whose tasks to monitor. If provided and task_id is not set, monitors all tasks for this agent.
    """
    monitor = TaskMonitor(st.session_state.get("api_url", "http://localhost:8000"))
    
    if task_id:
        asyncio.run(monitor.monitor_task(task_id))
    elif agent_id:
        asyncio.run(monitor.monitor_agent_tasks(agent_id)) 
"""Streamlit page for managing agents and tasks."""

import os
import json
import httpx
import asyncio
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

class AgentManager:
    """Manages agents and tasks via FastAPI backend."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initializes the AgentManager with the specified FastAPI backend URL.
        
        Args:
            api_url: The base URL of the FastAPI backend to connect to. Defaults to "http://localhost:8000".
        """
        self.api_url = api_url
        self.session = httpx.AsyncClient()
        
    async def list_agents(self) -> Dict[str, Any]:
        """
        Retrieves the list of all agents from the backend API.
        
        Returns:
            A dictionary containing the agents data on success, or an error message on failure.
        """
        try:
            response = await self.session.get(
                f"{self.api_url}/api/v1/agents",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch agents: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def create_agent(self, agent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously creates a new agent by sending agent data to the backend API.
        
        Args:
            agent_data: Dictionary containing the agent's configuration and type.
        
        Returns:
            The JSON response from the backend if successful, or a dictionary with
            success status and error message if the request fails.
        """
        try:
            response = await self.session.post(
                f"{self.api_url}/api/v1/agents",
                json=agent_data,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to create agent: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def get_agent_tasks(self, agent_id: UUID) -> Dict[str, Any]:
        """
        Retrieves the list of tasks assigned to a specific agent.
        
        Args:
            agent_id: The unique identifier of the agent whose tasks are to be fetched.
        
        Returns:
            A dictionary containing the agent's tasks on success, or an error message if the request fails.
        """
        try:
            response = await self.session.get(
                f"{self.api_url}/api/v1/agents/{agent_id}/tasks",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to fetch agent tasks: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def create_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new task by sending task data to the backend API.
        
        Args:
            task_data: A dictionary containing the task's configuration and parameters.
        
        Returns:
            The JSON response from the backend if successful, or a dictionary with
            'success': False and an 'error' message if the request fails.
        """
        try:
            response = await self.session.post(
                f"{self.api_url}/api/v1/tasks",
                json=task_data,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to create task: {str(e)}")
            return {"success": False, "error": str(e)}

def render_agent_card(agent: Dict[str, Any]):
    """
    Displays an agent's information and status in a Streamlit card with action controls.
    
    Args:
        agent: Dictionary containing agent details, including type, ID, status, and configuration.
    """
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.subheader(f"Agent: {agent['type']}")
            st.caption(f"ID: {agent['id']}")
            
        with col2:
            status_color = {
                "active": "🟢",
                "inactive": "🔴",
                "busy": "🟡"
            }.get(agent["status"], "⚪")
            st.write(f"Status: {status_color} {agent['status']}")
            
        with col3:
            if st.button("View Tasks", key=f"tasks_{agent['id']}"):
                st.session_state.selected_agent = agent["id"]
                
        st.json(agent["config"])
        st.divider()

def render_task_list(tasks: List[Dict[str, Any]]):
    """
    Displays a list of tasks with their type, ID, progress, status, and optional result or error details.
    
    Args:
        tasks: A list of task dictionaries, each containing task information such as type, ID, progress, status, and optionally result or error data.
    """
    for task in tasks:
        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"Task: {task['type']}")
                st.caption(f"ID: {task['id']}")
                
            with col2:
                st.progress(task["progress"])
                
            with col3:
                st.write(f"Status: {task['status']}")
                
            if task.get("result"):
                with st.expander("Result"):
                    st.json(task["result"])
                    
            if task.get("error"):
                with st.expander("Error", expanded=True):
                    st.error(task["error"])
                    
            st.divider()

def main():
    """
    Runs the Streamlit application for managing agents and tasks via a FastAPI backend.
    
    The app allows users to configure the backend URL, create new agents with custom configurations,
    view all active agents, select an agent to view its tasks, and create new tasks for the selected agent.
    All interactions are performed through asynchronous API calls with real-time feedback and error handling.
    """
    st.title("Agent & Task Manager")
    
    # Initialize session state
    if "selected_agent" not in st.session_state:
        st.session_state.selected_agent = None
        
    # Sidebar configuration
    st.sidebar.header("Configuration")
    api_url = st.sidebar.text_input(
        "FastAPI URL",
        value="http://localhost:8000",
        help="URL of the FastAPI backend"
    )
    
    # Initialize manager
    manager = AgentManager(api_url)
    
    # Create new agent section
    with st.expander("Create New Agent"):
        with st.form("create_agent"):
            agent_type = st.selectbox(
                "Agent Type",
                ["super", "inspector", "journey"]
            )
            config = st.text_area(
                "Agent Configuration (JSON)",
                value="{}"
            )
            
            if st.form_submit_button("Create Agent"):
                try:
                    config_dict = json.loads(config)
                    result = asyncio.run(manager.create_agent({
                        "type": agent_type,
                        "config": config_dict
                    }))
                    
                    if result.get("success"):
                        st.success("Agent created successfully!")
                    else:
                        st.error(f"Failed to create agent: {result.get('error')}")
                except json.JSONDecodeError:
                    st.error("Invalid JSON configuration")
                    
    # List agents
    st.header("Active Agents")
    agents = asyncio.run(manager.list_agents())
    
    if agents.get("success"):
        for agent in agents["data"]:
            render_agent_card(agent)
    else:
        st.error("Failed to fetch agents")
        
    # Show selected agent's tasks
    if st.session_state.selected_agent:
        st.header("Agent Tasks")
        tasks = asyncio.run(manager.get_agent_tasks(st.session_state.selected_agent))
        
        if tasks.get("success"):
            render_task_list(tasks["data"])
        else:
            st.error("Failed to fetch tasks")
            
        # Create new task section
        with st.expander("Create New Task"):
            with st.form("create_task"):
                task_type = st.text_input("Task Type")
                input_data = st.text_area(
                    "Input Data (JSON)",
                    value="{}"
                )
                
                if st.form_submit_button("Create Task"):
                    try:
                        input_dict = json.loads(input_data)
                        result = asyncio.run(manager.create_task({
                            "type": task_type,
                            "input_data": input_dict,
                            "agent_id": st.session_state.selected_agent
                        }))
                        
                        if result.get("success"):
                            st.success("Task created successfully!")
                        else:
                            st.error(f"Failed to create task: {result.get('error')}")
                    except json.JSONDecodeError:
                        st.error("Invalid JSON input data")

if __name__ == "__main__":
    main() 
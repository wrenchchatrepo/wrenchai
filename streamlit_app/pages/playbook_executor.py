"""Streamlit page for executing Docusaurus portfolio playbook."""

import os
import yaml
import httpx
import asyncio
import json
import streamlit as st
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from streamlit_app.components.task_monitor import render_task_monitor
from streamlit_app.components.playbook_results import render_playbook_results
from streamlit_app.components.midnight_theme import apply_midnight_theme
from streamlit_app.components.ui_components import code_block
from streamlit_app.components.progress_indicators import progress_bar

# Apply the midnight theme
apply_midnight_theme()

class DocusaurusPlaybookExecutor:
    """Executes Docusaurus portfolio playbook via FastAPI."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initializes the executor with the specified FastAPI backend URL.
        
        Args:
            api_url: The base URL of the FastAPI backend to use for playbook execution.
        """
        self.api_url = api_url
        self.session = httpx.AsyncClient()
        
    async def execute_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """
        Executes a Docusaurus playbook by validating the YAML file and submitting it to the FastAPI backend.
        
        Args:
            playbook_path: Path to the YAML playbook file to execute.
        
        Returns:
            A dictionary containing the execution result, including a 'success' flag and any error messages or API response details.
        """
        try:
            # Use the new playbook validator
            from core.playbook_validator import perform_full_validation
            from core.playbook_schema import Playbook
            
            valid, error, playbook = perform_full_validation(playbook_path)
            
            if not valid:
                st.error(f"Invalid playbook: {error}")
                return {"success": False, "error": error}
                
            # Convert to API format and execute
            api_payload = playbook.to_api_format()
            response = await self.session.post(
                f"{self.api_url}/api/playbooks/run",  # Using the correct endpoint path
                json=api_payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if result.get("status") == "started":
                st.success("Playbook execution started successfully")
                result["success"] = True
                return result
            else:
                st.error(f"Playbook execution failed: {result.get('error')}")
                result["success"] = False
                return result
                
        except httpx.TimeoutException:
            error_msg = "API request timed out"
            st.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except httpx.HTTPError as e:
            error_msg = f"HTTP error occurred: {str(e)}"
            st.error(error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            st.error(error_msg)
            return {"success": False, "error": error_msg}
            
        finally:
            await self.session.aclose()
            
    async def get_execution_results(self, playbook_id: str) -> Dict[str, Any]:
        """
        Fetches the latest execution results for a playbook from the API.
        
        Args:
            playbook_id: The ID of the playbook execution to fetch results for.
            
        Returns:
            A dictionary containing the execution results, or None if the fetch fails.
        """
        try:
            response = await self.session.get(
                f"{self.api_url}/api/playbooks/status/{playbook_id}",
                timeout=10.0
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if result.get("success"):
                return result.get("data")
            else:
                st.error(f"Failed to fetch results: {result.get('error')}")
                return None
                
        except httpx.TimeoutException:
            st.error("API request timed out when fetching results")
            return None
            
        except httpx.HTTPError as e:
            st.error(f"HTTP error occurred when fetching results: {str(e)}")
            return None
            
        except Exception as e:
            st.error(f"Unexpected error when fetching results: {str(e)}")
            return None


def get_playbooks_from_directory(directory_path: str) -> List[Dict[str, Any]]:
    """
    Get all playbook files from a directory with their metadata.
    
    Args:
        directory_path: The path to the directory containing playbook files
        
    Returns:
        A list of dictionaries containing playbook information
    """
    playbooks = []
    
    try:
        # Ensure the directory exists
        if not os.path.exists(directory_path):
            st.warning(f"Directory not found: {directory_path}")
            return playbooks
        
        # Iterate through files in the directory
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            
            # Check if it's a YAML file
            if os.path.isfile(file_path) and (filename.endswith(".yaml") or filename.endswith(".yml")):
                try:
                    # Read YAML content
                    with open(file_path, 'r') as f:
                        content = yaml.safe_load(f)
                    
                    # Extract basic metadata
                    playbook_info = {
                        "filename": filename,
                        "path": file_path,
                        "name": content.get("name", filename),
                        "description": content.get("description", "No description available"),
                        "content": content
                    }
                    
                    playbooks.append(playbook_info)
                except Exception as e:
                    st.warning(f"Error reading {filename}: {str(e)}")
    except Exception as e:
        st.error(f"Error accessing playbooks directory: {str(e)}")
    
    return playbooks


def display_playbook_content(playbook: Dict[str, Any]):
    """
    Display the content of a playbook.
    
    Args:
        playbook: Dictionary containing playbook information
    """
    # Display basic metadata
    st.subheader(playbook["name"])
    st.write(playbook["description"])
    
    # Display file info
    st.caption(f"File: {playbook['filename']}")
    
    # Display YAML content
    with st.expander("View Playbook Content", expanded=True):
        yaml_content = yaml.dump(playbook["content"], sort_keys=False, default_flow_style=False)
        code_block(yaml_content, language="yaml")
    
    # Display additional metadata if available
    if "agents" in playbook["content"]:
        st.write("**Agents:**")
        for agent in playbook["content"]["agents"]:
            agent_type = agent.get("type", "Unknown")
            st.markdown(f"- {agent_type}")
    
    if "steps" in playbook["content"]:
        st.write("**Steps:**")
        for i, step in enumerate(playbook["content"]["steps"]):
            step_name = step.get("name", f"Step {i+1}")
            step_action = step.get("action", "Unknown action")
            st.markdown(f"- {step_name} ({step_action})")


def main():
    """
    Runs the Streamlit user interface for selecting and executing a Docusaurus playbook.
    
    Provides configuration for the FastAPI backend URL, playbook selection from a directory,
    and controls to trigger playbook execution. Displays progress, results, and playbook details.
    """
    st.title("ud83dudcc2 Docusaurus Portfolio Playbook Executor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    api_url = st.sidebar.text_input(
        "FastAPI URL",
        value="http://localhost:8000",
        help="URL of the FastAPI backend"
    )
    
    playbooks_directory = st.sidebar.text_input(
        "Playbooks Directory",
        value="/Users/dionedge/dev/wrenchai/core/playbooks",
        help="Path to the directory containing playbook files"
    )
    
    # Load playbooks from directory
    playbooks = get_playbooks_from_directory(playbooks_directory)
    
    # Main content
    if not playbooks:
        st.warning("No playbooks found in the specified directory.")
        
        # File uploader as fallback
        st.write("Upload a playbook file instead:")
        playbook_file = st.file_uploader(
            "Upload Playbook YAML",
            type=["yaml", "yml"],
            help="Upload your Docusaurus portfolio playbook YAML file"
        )
        
        if playbook_file:
            # Save uploaded file temporarily
            temp_path = Path("temp_playbook.yaml")
            temp_path.write_bytes(playbook_file.getvalue())
            
            selected_playbook_path = str(temp_path)
            try:
                # Display content of uploaded playbook
                with open(selected_playbook_path, 'r') as f:
                    content = yaml.safe_load(f)
                
                playbook_info = {
                    "filename": playbook_file.name,
                    "path": selected_playbook_path,
                    "name": content.get("name", playbook_file.name),
                    "description": content.get("description", "No description available"),
                    "content": content
                }
                
                display_playbook_content(playbook_info)
            except Exception as e:
                st.error(f"Error reading playbook: {str(e)}")
    else:
        # Display playbook selection
        st.write(f"Found {len(playbooks)} playbooks in the directory.")
        
        # Create a selection box with playbook names
        playbook_names = [p["name"] for p in playbooks]
        selected_name = st.selectbox("Select a playbook to execute", playbook_names)
        
        # Find the selected playbook
        selected_playbook = next((p for p in playbooks if p["name"] == selected_name), None)
        selected_playbook_path = selected_playbook["path"]
        
        # Display playbook details
        if selected_playbook:
            display_playbook_content(selected_playbook)
    
    # Execution section
    st.markdown("---")
    st.subheader("Execute Playbook")
    
    if st.button("Execute Selected Playbook", key="execute_button", type="primary"):
        executor = DocusaurusPlaybookExecutor(api_url)
        
        # Show progress
        st.markdown("### Execution Progress")
        execution_progress = st.empty()
        with execution_progress.container():
            progress_value = 0.1  # Start with 10% to show something is happening
            progress_bar(progress_value, "Initializing execution...")
        
        # Execute playbook
        with st.spinner("Executing playbook..."):
            result = asyncio.run(executor.execute_playbook(selected_playbook_path))
            
            if result.get("success"):
                playbook_id = result.get("playbook_id")
                st.success(f"Playbook execution started! ID: {playbook_id}")
                
                # Update progress
                with execution_progress.container():
                    progress_bar(0.3, "Playbook submitted successfully")
                
                # Create tabs for different views
                result_tab, progress_tab, raw_tab = st.tabs(["Results", "Live Progress", "Raw Response"])
                
                with raw_tab:
                    st.json(result)
                    
                with progress_tab:
                    # Start real-time progress tracking
                    with execution_progress.container():
                        progress_bar(0.5, "Monitoring execution progress...")
                    render_task_monitor(task_id=playbook_id)
                    
                with result_tab:
                    # Check if we have execution results
                    if st.session_state.get("execution_results"):
                        with execution_progress.container():
                            progress_bar(1.0, "Execution complete")
                        render_playbook_results(st.session_state.execution_results)
                    else:
                        st.info("Results will appear here once execution is complete")
                        # Add a refresh button
                        if st.button("Refresh Results"):
                            # Fetch latest results from API
                            st.info("Refreshing results...")
                            executor = DocusaurusPlaybookExecutor(api_url)
                            results = asyncio.run(executor.get_execution_results(playbook_id))
                            if results:
                                # Store results in session state
                                st.session_state.execution_results = results
                                # Update progress
                                with execution_progress.container():
                                    progress_bar(1.0, "Results updated")
                                # Force rerun to update the UI
                                st.rerun()
            else:
                st.error("Failed to execute playbook")
                st.json(result)
                # Update progress
                with execution_progress.container():
                    progress_bar(1.0, "Execution failed", color="#FF453A")


if __name__ == "__main__":
    main()
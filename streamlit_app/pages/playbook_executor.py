"""Streamlit page for executing Docusaurus portfolio playbook."""

import os
import yaml
import httpx
import asyncio
import json
import streamlit as st
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from pathlib import Path

from streamlit_app.components.midnight_theme import apply_midnight_theme
from streamlit_app.components.ui_components import code_block, info_card, warning_card, error_card, success_card
from streamlit_app.components.progress_indicators import progress_bar, task_progress
from streamlit_app.components.task_monitor import render_task_monitor
from streamlit_app.components.playbook_results import render_playbook_results
from streamlit_app.components.playbook_schema_integration import (
    PlaybookSchemaManager, playbook_schema_browser, playbook_schema_editor
)

# Apply the midnight theme
apply_midnight_theme()

class PlaybookExecutor:
    """Executes playbooks via FastAPI."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initializes the executor with the specified FastAPI backend URL.
        
        Args:
            api_url: The base URL of the FastAPI backend to use for playbook execution.
        """
        self.api_url = api_url
        self.session = httpx.AsyncClient()
        
    async def execute_playbook(self, playbook_path: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a playbook by validating the file and submitting it to the FastAPI backend.
        
        Args:
            playbook_path: Path to the playbook file to execute
            parameters: Optional parameters to override in the playbook
        
        Returns:
            A dictionary containing the execution result
        """
        from core.playbook_validator import perform_full_validation
        
        try:
            # Validate the playbook first
            valid, error, playbook = perform_full_validation(playbook_path)
            
            if not valid:
                error_card("Invalid Playbook", error)
                return {"success": False, "error": error}
            
            # Apply parameters if provided
            if parameters and playbook:
                playbook = playbook.merge_user_config(parameters)
            
            # Convert to API format and execute
            api_payload = playbook.to_api_format() if playbook else {}
            response = await self.session.post(
                f"{self.api_url}/api/playbooks/run",
                json=api_payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if result.get("status") == "started":
                success_card("Playbook Execution Started", "The playbook execution has been initiated successfully.")
                result["success"] = True
                return result
            else:
                error_card("Execution Failed", result.get("error", "Unknown error"))
                result["success"] = False
                return result
                
        except httpx.TimeoutException:
            error_msg = "API request timed out"
            error_card("Timeout Error", error_msg)
            return {"success": False, "error": error_msg}
            
        except httpx.HTTPError as e:
            error_msg = f"HTTP error occurred: {str(e)}"
            error_card("HTTP Error", error_msg)
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            error_card("Error", error_msg)
            return {"success": False, "error": error_msg}
            
        finally:
            await self.session.aclose()
            
    async def get_execution_status(self, playbook_id: str) -> Dict[str, Any]:
        """
        Fetches the status of a playbook execution.
        
        Args:
            playbook_id: The ID of the playbook execution
            
        Returns:
            Status information for the execution
        """
        try:
            response = await self.session.get(
                f"{self.api_url}/api/playbooks/status/{playbook_id}",
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            error_card("Status Check Failed", str(e))
            return {"success": False, "error": str(e)}
            
    async def get_execution_results(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches the results of a playbook execution.
        
        Args:
            playbook_id: The ID of the playbook execution
            
        Returns:
            Execution results or None if fetch failed
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
                error_card("Failed to Fetch Results", result.get("error", "Unknown error"))
                return None
                
        except Exception as e:
            error_card("Result Fetch Failed", str(e))
            return None


def main():
    """Main function for the playbook executor page."""
    st.title("ud83dudcc2 Playbook Executor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    api_url = st.sidebar.text_input(
        "FastAPI URL",
        value="http://localhost:8000",
        help="URL of the FastAPI backend"
    )
    
    playbooks_dir = st.sidebar.text_input(
        "Playbooks Directory",
        value="/Users/dionedge/dev/wrenchai/core/playbooks",
        help="Path to the directory containing playbook files"
    )
    
    # Create playbooks manager
    playbook_manager = PlaybookSchemaManager(playbooks_dir)
    
    # Main content tabs
    browse_tab, create_tab, execute_tab = st.tabs(["Browse Playbooks", "Create Playbook", "Execute Playbook"])
    
    # Browse playbooks tab
    with browse_tab:
        st.subheader("Available Playbooks")
        
        # Check if directory exists
        if not os.path.exists(playbooks_dir):
            warning_card("Directory Not Found", f"The directory {playbooks_dir} does not exist. Please create it or specify a different directory.")
        else:
            # Browse playbooks
            selected_playbook = playbook_schema_browser(playbooks_dir)
            
            if selected_playbook:
                st.markdown("---")
                playbook_path = selected_playbook["path"]
                
                # Display playbook details
                st.subheader(f"Selected Playbook: {selected_playbook['name']}")
                st.write(selected_playbook["description"])
                
                # Create buttons for actions
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("Execute", type="primary"):
                        st.session_state.selected_playbook = selected_playbook
                        st.session_state.active_tab = "execute_tab"
                        st.rerun()
                
                with col2:
                    if st.button("Edit"):
                        st.session_state.selected_playbook = selected_playbook
                        st.session_state.active_tab = "create_tab"
                        st.rerun()
                
                with col3:
                    if st.button("View YAML"):
                        st.markdown("### Playbook YAML")
                        with open(playbook_path, 'r') as f:
                            yaml_content = f.read()
                        code_block(yaml_content, language="yaml")
    
    # Create playbook tab
    with create_tab:
        st.subheader("Create or Edit Playbook")
        
        # Check if we're editing an existing playbook
        editing_playbook = None
        if st.session_state.get("selected_playbook") and st.session_state.get("active_tab") == "create_tab":
            editing_playbook = st.session_state.selected_playbook
            st.write(f"Editing playbook: {editing_playbook['name']}")
        
        # Create/edit playbook form
        saved_playbook = playbook_schema_editor(playbooks_dir, editing_playbook)
        
        if saved_playbook:
            success_card("Playbook Saved", "Your playbook has been saved successfully.")
            # Reset editing state
            if "selected_playbook" in st.session_state:
                del st.session_state.selected_playbook
            if "active_tab" in st.session_state:
                del st.session_state.active_tab
    
    # Execute playbook tab
    with execute_tab:
        st.subheader("Execute Playbook")
        
        # Check if a playbook is selected for execution
        playbook_to_execute = None
        if st.session_state.get("selected_playbook") and st.session_state.get("active_tab") == "execute_tab":
            playbook_to_execute = st.session_state.selected_playbook
            st.write(f"Ready to execute: {playbook_to_execute['name']}")
            st.write(playbook_to_execute["description"])
            
            # Parameters section
            st.markdown("### Execution Parameters")
            
            # Extract parameters from playbook
            parameters = {}
            if "steps" in playbook_to_execute["content"]:
                for step in playbook_to_execute["content"]["steps"]:
                    if "parameters" in step:
                        st.write(f"Parameters for step: {step.get('description', step.get('step_id', 'unknown'))}")
                        for param_name, param_value in step["parameters"].items():
                            # Create input fields for each parameter
                            if isinstance(param_value, bool):
                                parameters[param_name] = st.checkbox(param_name, value=param_value)
                            elif isinstance(param_value, int):
                                parameters[param_name] = st.number_input(param_name, value=param_value)
                            elif isinstance(param_value, float):
                                parameters[param_name] = st.number_input(param_name, value=param_value, step=0.1)
                            elif isinstance(param_value, list):
                                parameters[param_name] = st.multiselect(param_name, options=param_value, default=param_value)
                            else:
                                parameters[param_name] = st.text_input(param_name, value=str(param_value))
            
            # Execute button
            if st.button("Execute Playbook", type="primary"):
                executor = PlaybookExecutor(api_url)
                
                # Progress tracking
                execution_progress = st.empty()
                with execution_progress.container():
                    progress_bar(0.2, "Preparing to execute...")
                
                # Execute playbook
                with st.spinner("Executing playbook..."):
                    # Update progress
                    with execution_progress.container():
                        progress_bar(0.4, "Submitting playbook...")
                    
                    result = asyncio.run(executor.execute_playbook(
                        playbook_to_execute["path"], 
                        parameters
                    ))
                    
                    if result.get("success"):
                        playbook_id = result.get("playbook_id")
                        
                        # Update progress
                        with execution_progress.container():
                            progress_bar(0.6, "Playbook submitted successfully")
                        
                        # Create tabs for tracking execution
                        monitor_tab, results_tab, logs_tab = st.tabs(["Monitor Progress", "Results", "Logs"])
                        
                        with monitor_tab:
                            # Update progress
                            with execution_progress.container():
                                progress_bar(0.8, "Monitoring execution...")
                            
                            # Display real-time monitoring
                            render_task_monitor(task_id=playbook_id)
                        
                        with results_tab:
                            # Check for results
                            st.markdown("### Execution Results")
                            if st.button("Refresh Results"):
                                # Fetch latest results
                                executor = PlaybookExecutor(api_url)
                                results = asyncio.run(executor.get_execution_results(playbook_id))
                                
                                if results:
                                    # Store in session state
                                    st.session_state.execution_results = results
                                    # Update progress to complete
                                    with execution_progress.container():
                                        progress_bar(1.0, "Execution complete")
                                    # Display results
                                    render_playbook_results(results)
                                else:
                                    info_card("No Results Yet", "The execution is still in progress or has not produced results yet.")
                        
                        with logs_tab:
                            st.markdown("### Execution Logs")
                            st.text_area("Log Output", "Logs will appear here...", height=300, disabled=True)
                    else:
                        # Update progress to error state
                        with execution_progress.container():
                            progress_bar(1.0, "Execution failed", color="#FF453A")
                        
                        error_card("Execution Failed", result.get("error", "Unknown error occurred during execution"))
        else:
            info_card("No Playbook Selected", "Please select a playbook from the Browse tab to execute.")
            
            # Option to go to browse tab
            if st.button("Browse Playbooks"):
                st.session_state.active_tab = "browse_tab"
                st.rerun()
    
    # Set active tab if specified
    if st.session_state.get("active_tab") == "browse_tab":
        st.session_state.active = 0  # Browse tab index
    elif st.session_state.get("active_tab") == "create_tab":
        st.session_state.active = 1  # Create tab index
    elif st.session_state.get("active_tab") == "execute_tab":
        st.session_state.active = 2  # Execute tab index


if __name__ == "__main__":
    main()
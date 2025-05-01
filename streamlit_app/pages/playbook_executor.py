"""Streamlit page for executing Docusaurus portfolio playbook."""

import os
import yaml
import httpx
import asyncio
import json
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from streamlit_app.components.task_monitor import render_task_monitor
from streamlit_app.components.playbook_results import render_playbook_results

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
            
def main():
    """
    Runs the Streamlit user interface for uploading and executing a Docusaurus playbook.
    
    Provides configuration for the FastAPI backend URL, file upload for playbook YAML files,
    and controls to trigger playbook execution. Displays progress, results, and example
    playbook format for user guidance.
    """
    st.title("Docusaurus Portfolio Playbook Executor")
    
    # Sidebar configuration
    st.sidebar.header("Configuration")
    api_url = st.sidebar.text_input(
        "FastAPI URL",
        value="http://localhost:8000",
        help="URL of the FastAPI backend"
    )
    
    # Main content
    st.write("Execute your Docusaurus portfolio playbook")
    
    # File uploader for playbook
    playbook_file = st.file_uploader(
        "Upload Playbook YAML",
        type=["yaml", "yml"],
        help="Upload your Docusaurus portfolio playbook YAML file"
    )
    
    if playbook_file:
        # Save uploaded file temporarily
        temp_path = Path("temp_playbook.yaml")
        temp_path.write_bytes(playbook_file.getvalue())
        
        # Execute button
        if st.button("Execute Playbook"):
            executor = DocusaurusPlaybookExecutor(api_url)
            
            # Create progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Execute playbook
            with st.spinner("Executing playbook..."):
                result = asyncio.run(executor.execute_playbook(str(temp_path)))
                
                if result.get("success"):
                    playbook_id = result.get("playbook_id")
                    st.success(f"Playbook execution started! ID: {playbook_id}")
                    
                    # Create tabs for different views
                    result_tab, progress_tab, raw_tab = st.tabs(["Results", "Live Progress", "Raw Response"])
                    
                    with raw_tab:
                        st.json(result)
                        
                    with progress_tab:
                        # Start real-time progress tracking
                        render_task_monitor(task_id=playbook_id)
                        
                    with result_tab:
                        # Check if we have execution results
                        if st.session_state.get("execution_results"):
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
                                    # Force rerun to update the UI
                                    st.experimental_rerun()
                else:
                    st.error("Failed to execute playbook")
                    st.json(result)
                    
        # Cleanup temp file
        if temp_path.exists():
            temp_path.unlink()
            
    # Display example playbook format
    with st.expander("Show Example Playbook Format"):
        st.code("""
name: Docusaurus Portfolio
description: Generate a Docusaurus portfolio site
agents:
  - type: ux_designer
    config:
      style: modern
  - type: code_generator
    config:
      framework: docusaurus
steps:
  - name: Initialize Project
    action: init_docusaurus
    params:
      template: portfolio
  - name: Generate Content
    action: generate_content
    params:
      sections: [about, projects, blog]
""", language="yaml")

if __name__ == "__main__":
    main() 
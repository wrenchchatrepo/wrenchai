"""Streamlit page for executing Docusaurus portfolio playbook."""

import os
import yaml
import httpx
import asyncio
import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

class DocusaurusPlaybookExecutor:
    """Executes Docusaurus portfolio playbook via FastAPI."""
    
    def __init__(self, api_url: str = "http://localhost:8000"):
        """
        Initializes the executor with the specified FastAPI backend URL.
        
        Args:
            api_url: The base URL of the FastAPI service to use for playbook execution.
        """
        self.api_url = api_url
        self.session = httpx.AsyncClient()
        
    async def execute_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """
        Executes a Docusaurus playbook by validating the YAML file and submitting it to the FastAPI backend.
        
        Validates the playbook file, converts it to the required API format, and sends it to the backend for execution. Handles validation errors, HTTP errors, timeouts, and unexpected exceptions, returning a dictionary indicating success or failure along with relevant details.
        
        Args:
            playbook_path: Path to the playbook YAML file.
        
        Returns:
            A dictionary containing the execution result, including a success flag and any error messages or response data from the backend.
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
            
def main():
    """
    Launches the Streamlit app for uploading and executing a Docusaurus portfolio playbook.
    
    Provides a user interface to configure the FastAPI backend URL, upload a playbook YAML file, and trigger its execution. Displays progress, success or error messages, and execution details. Also shows an example playbook format for user reference.
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
                    
                    # Add execution details
                    st.json(result)
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
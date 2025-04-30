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
        """Initialize executor with API URL."""
        self.api_url = api_url
        self.session = httpx.AsyncClient()
        
    async def execute_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """Execute playbook with proper error handling and progress tracking."""
        try:
            # Load and validate playbook
            playbook = self._load_playbook(playbook_path)
            if not self._validate_playbook_format(playbook):
                st.error("Invalid playbook format")
                return {"success": False, "error": "Invalid playbook format"}
                
            # Convert to API format and execute
            api_payload = self._convert_to_api_format(playbook)
            response = await self.session.post(
                f"{self.api_url}/api/v1/playbooks/execute",
                json=api_payload,
                timeout=30.0
            )
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            if result.get("success"):
                st.success("Playbook execution started successfully")
                return result
            else:
                st.error(f"Playbook execution failed: {result.get('error')}")
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
            
    def _load_playbook(self, playbook_path: str) -> Dict[str, Any]:
        """Load playbook YAML file."""
        with open(playbook_path) as f:
            return yaml.safe_load(f)
            
    def _validate_playbook_format(self, playbook: Dict[str, Any]) -> bool:
        """Validate playbook has required fields."""
        required_fields = ["name", "description", "steps", "agents"]
        return all(field in playbook for field in required_fields)
        
    def _convert_to_api_format(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Convert playbook to API payload format."""
        return {
            "name": playbook["name"],
            "description": playbook["description"],
            "steps": playbook["steps"],
            "agents": playbook["agents"],
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "source": "streamlit"
            }
        }

def main():
    """Main Streamlit app."""
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
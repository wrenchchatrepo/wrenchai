"""Playbook Configuration Components.

This module provides specialized components for handling playbook configuration
using Pydantic models for validation and streamlit-pydantic for UI generation.
"""

import streamlit as st
from typing import Type, Dict, Any, Optional, List, Callable, Union, TypeVar, Generic
from pydantic import BaseModel, Field, create_model, ValidationError
import yaml
import json
import os
from pathlib import Path

from streamlit_app.components.form_components import model_form, FormBuilder
from streamlit_app.components.ui_components import info_card, warning_card, error_card, success_card, code_block
from streamlit_app.components.config_components import ConfigManager

T = TypeVar('T', bound=BaseModel)

class PlaybookManager(Generic[T]):
    """Manager for playbook configurations based on Pydantic models."""
    
    def __init__(self, 
                 playbook_model: Type[T],
                 playbooks_dir: Union[str, Path], 
                 template_playbook: Optional[Dict[str, Any]] = None):
        """
        Initialize the playbook manager.
        
        Args:
            playbook_model: Pydantic model class for playbooks
            playbooks_dir: Directory containing playbook files
            template_playbook: Template for new playbooks
        """
        self.playbook_model = playbook_model
        self.playbooks_dir = Path(playbooks_dir)
        self.template_playbook = template_playbook or {}
        
        # Create directory if it doesn't exist
        os.makedirs(self.playbooks_dir, exist_ok=True)
    
    def get_available_playbooks(self) -> List[Dict[str, Any]]:
        """Get list of available playbooks with metadata.
        
        Returns:
            List of dictionaries with playbook metadata
        """
        playbooks = []
        
        # Scan playbooks directory
        for file_path in self.playbooks_dir.glob("*.{yaml,yml,json}"):
            try:
                # Load the playbook
                if file_path.suffix.lower() in [".yaml", ".yml"]:
                    with open(file_path, 'r') as f:
                        playbook_dict = yaml.safe_load(f)
                elif file_path.suffix.lower() == ".json":
                    with open(file_path, 'r') as f:
                        playbook_dict = json.load(f)
                else:
                    continue
                
                # Create playbook model to validate
                playbook = self.playbook_model(**playbook_dict)
                
                # Add to list with metadata
                playbooks.append({
                    "name": playbook_dict.get("name", file_path.stem),
                    "description": playbook_dict.get("description", "No description"),
                    "path": str(file_path),
                    "filename": file_path.name,
                    "last_modified": file_path.stat().st_mtime,
                    "content": playbook_dict
                })
            except Exception as e:
                # Skip invalid playbooks
                st.warning(f"Error loading playbook {file_path.name}: {str(e)}")
        
        # Sort by name
        playbooks.sort(key=lambda p: p["name"])
        return playbooks
    
    def load_playbook(self, playbook_path: Union[str, Path]) -> Optional[T]:
        """Load a playbook from file.
        
        Args:
            playbook_path: Path to the playbook file
            
        Returns:
            Playbook model instance or None if loading failed
        """
        try:
            path = Path(playbook_path)
            
            # Load based on file extension
            if path.suffix.lower() in [".yaml", ".yml"]:
                with open(path, 'r') as f:
                    playbook_dict = yaml.safe_load(f)
            elif path.suffix.lower() == ".json":
                with open(path, 'r') as f:
                    playbook_dict = json.load(f)
            else:
                st.error(f"Unsupported file format: {path.suffix}")
                return None
            
            # Create and validate playbook model
            return self.playbook_model(**playbook_dict)
        except Exception as e:
            st.error(f"Error loading playbook: {str(e)}")
            return None
    
    def save_playbook(self, playbook: T, filename: Optional[str] = None) -> Optional[Path]:
        """Save playbook to file.
        
        Args:
            playbook: Playbook model instance
            filename: Optional filename, defaults to playbook name
            
        Returns:
            Path to saved file or None if saving failed
        """
        try:
            # Get playbook data
            playbook_dict = playbook.model_dump()
            
            # Generate filename if not provided
            if filename is None:
                # Use playbook name or a default
                name = playbook_dict.get("name", "playbook")
                # Sanitize filename
                filename = f"{name.lower().replace(' ', '_')}.yaml"
            
            # Ensure extension
            if not filename.endswith((".yaml", ".yml", ".json")):
                filename += ".yaml"
            
            # Create full path
            file_path = self.playbooks_dir / filename
            
            # Save based on extension
            if filename.endswith((".yaml", ".yml")):
                with open(file_path, 'w') as f:
                    yaml.dump(playbook_dict, f, default_flow_style=False)
            elif filename.endswith(".json"):
                with open(file_path, 'w') as f:
                    json.dump(playbook_dict, f, indent=2)
            
            return file_path
        except Exception as e:
            st.error(f"Error saving playbook: {str(e)}")
            return None
    
    def delete_playbook(self, playbook_path: Union[str, Path]) -> bool:
        """Delete a playbook file.
        
        Args:
            playbook_path: Path to the playbook file
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            path = Path(playbook_path)
            
            # Ensure the file exists and is within playbooks directory
            if not path.exists():
                st.error(f"Playbook file not found: {path}")
                return False
            
            if self.playbooks_dir not in path.parents and self.playbooks_dir != path.parent:
                st.error(f"Cannot delete file outside playbooks directory: {path}")
                return False
            
            # Delete the file
            path.unlink()
            return True
        except Exception as e:
            st.error(f"Error deleting playbook: {str(e)}")
            return False
    
    def create_template(self) -> T:
        """Create a template playbook.
        
        Returns:
            Template playbook model instance
        """
        return self.playbook_model(**self.template_playbook)


def playbook_browser(playbook_manager: PlaybookManager,
                    on_select: Optional[Callable[[Dict[str, Any]], Any]] = None) -> Optional[Dict[str, Any]]:
    """Create a UI for browsing playbooks.
    
    Args:
        playbook_manager: PlaybookManager instance
        on_select: Optional callback when a playbook is selected
        
    Returns:
        Selected playbook metadata or None if no selection
    """
    # Get available playbooks
    playbooks = playbook_manager.get_available_playbooks()
    
    if not playbooks:
        st.info("No playbooks found. Create a new one to get started.")
        return None
    
    # Create playbook selector
    st.subheader("Available Playbooks")
    
    # Create a grid of playbook cards for selection
    cols = st.columns(3)
    selected_playbook = None
    
    for i, playbook in enumerate(playbooks):
        with cols[i % 3]:
            # Create styled card
            with st.container():
                st.markdown(f"""
                <div style="
                    border: 1px solid #2A2A2A;
                    border-radius: 5px;
                    padding: 15px;
                    margin-bottom: 15px;
                    background-color: #1E1E1E;
                    height: 180px;
                    position: relative;
                    overflow: hidden;
                ">
                    <h3 style="margin-top: 0; color: #00CCFF;">{playbook['name']}</h3>
                    <p style="font-size: 0.9em; color: #BBBBBB; height: 60px; overflow: hidden;">{playbook['description']}</p>
                    <div style="font-size: 0.8em; color: #7B42F6; position: absolute; bottom: 15px;">{playbook['filename']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("Select", key=f"select_{i}"):
                    selected_playbook = playbook
    
    # Handle selection
    if selected_playbook:
        if on_select:
            on_select(selected_playbook)
        return selected_playbook
    
    return None


def playbook_details(playbook: Dict[str, Any]):
    """Display playbook details.
    
    Args:
        playbook: Playbook metadata dictionary
    """
    st.subheader(playbook["name"])
    st.write(playbook["description"])
    
    # Display file info
    st.caption(f"File: {playbook['filename']}")
    
    # Create tabs for different views
    content_tab, structure_tab = st.tabs(["Content", "Structure"])
    
    with content_tab:
        # Format YAML content
        yaml_content = yaml.dump(playbook["content"], default_flow_style=False)
        code_block(yaml_content, language="yaml")
    
    with structure_tab:
        # Display structure
        if "steps" in playbook["content"]:
            st.markdown("### Steps")
            for i, step in enumerate(playbook["content"]["steps"]):
                with st.expander(f"Step {i+1}: {step.get('name', 'Unnamed Step')}"):
                    st.json(step)
        
        if "agents" in playbook["content"]:
            st.markdown("### Agents")
            for i, agent in enumerate(playbook["content"]["agents"]):
                with st.expander(f"Agent {i+1}: {agent.get('type', 'Unknown Type')}"):
                    st.json(agent)


def playbook_editor(playbook_manager: PlaybookManager,
                   playbook: Optional[Union[BaseModel, Dict[str, Any]]] = None,
                   on_save: Optional[Callable[[BaseModel, str], Any]] = None) -> Optional[BaseModel]:
    """Create a UI for editing playbooks.
    
    Args:
        playbook_manager: PlaybookManager instance
        playbook: Optional playbook to edit (model or dict)
        on_save: Optional callback when a playbook is saved
        
    Returns:
        Saved playbook model instance or None if not saved
    """
    # Convert dict to model if needed
    if isinstance(playbook, dict):
        current_playbook = playbook_manager.playbook_model(**playbook.get("content", {}))
        playbook_path = playbook.get("path", None)
        playbook_name = playbook.get("name", "New Playbook")
    elif isinstance(playbook, BaseModel):
        current_playbook = playbook
        playbook_path = None
        playbook_name = getattr(playbook, "name", "New Playbook")
    else:
        # Create a template
        current_playbook = playbook_manager.create_template()
        playbook_path = None
        playbook_name = "New Playbook"
    
    st.subheader(f"Edit Playbook: {playbook_name}")
    
    # Create tabs for different sections of the editor
    basic_tab, advanced_tab, preview_tab = st.tabs(["Basic Settings", "Advanced Settings", "Preview"])
    
    with basic_tab:
        # Basic settings form
        updated_playbook = model_form(playbook_manager.playbook_model, key="playbook_editor")
        
    with advanced_tab:
        # Display JSON editor for advanced editing
        st.markdown("Edit the playbook YAML directly:")
        
        # Display current playbook YAML
        yaml_text = yaml.dump(current_playbook.model_dump(), default_flow_style=False)
        edited_yaml = st.text_area("YAML Editor", value=yaml_text, height=400)
        
        # Parse edited YAML
        if st.button("Parse YAML", key="parse_yaml"):
            try:
                # Parse YAML to dict
                parsed_dict = yaml.safe_load(edited_yaml)
                
                # Validate with model
                updated_playbook = playbook_manager.playbook_model(**parsed_dict)
                st.success("YAML parsed successfully!")
            except Exception as e:
                st.error(f"Error parsing YAML: {str(e)}")
    
    with preview_tab:
        # Preview current playbook
        st.json(current_playbook.model_dump_json(indent=2))
    
    # Save options
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        filename = st.text_input("Filename", value=playbook_path.split("/")[-1] if playbook_path else f"{playbook_name.lower().replace(' ', '_')}.yaml")
    
    with col2:
        if st.button("Save Playbook", type="primary"):
            if updated_playbook:
                # Save the playbook
                saved_path = playbook_manager.save_playbook(updated_playbook, filename)
                
                if saved_path:
                    st.success(f"Playbook saved to {saved_path}")
                    
                    # Call on_save callback if provided
                    if on_save:
                        on_save(updated_playbook, str(saved_path))
                        
                    return updated_playbook
    
    return None


def playbook_execution_form(playbook: Dict[str, Any], 
                          on_execute: Callable[[Dict[str, Any], Dict[str, Any]], Any]):
    """Create a form for executing a playbook with parameters.
    
    Args:
        playbook: Playbook metadata dictionary
        on_execute: Callback when execute button is pressed
    """
    st.subheader(f"Execute Playbook: {playbook['name']}")
    
    # Extract parameters from playbook steps if any
    parameters = {}
    
    # Get parameters from each step
    if "steps" in playbook["content"]:
        for step in playbook["content"]["steps"]:
            if "params" in step:
                for param_name, param_value in step["params"].items():
                    # Only add parameters with placeholders
                    if isinstance(param_value, str) and param_value.startswith("$"):
                        # Extract parameter name without the $ sign
                        clean_name = param_value[1:]
                        parameters[clean_name] = {
                            "name": clean_name,
                            "description": f"Parameter for step: {step.get('name', 'Unknown')}",
                            "default": ""
                        }
    
    # If no parameters found in steps, check if there's a parameters section
    if not parameters and "parameters" in playbook["content"]:
        for param_name, param_info in playbook["content"]["parameters"].items():
            parameters[param_name] = {
                "name": param_name,
                "description": param_info.get("description", ""),
                "default": param_info.get("default", "")
            }
    
    # Create parameter form
    with st.form("execution_params"):
        param_values = {}
        
        if parameters:
            st.markdown("### Parameters")
            
            for param_name, param_info in parameters.items():
                # Determine field type based on default value
                default_value = param_info.get("default", "")
                
                if isinstance(default_value, bool):
                    # Boolean parameter
                    param_values[param_name] = st.checkbox(
                        param_info.get("description", param_name),
                        value=default_value,
                        key=f"param_{param_name}"
                    )
                elif isinstance(default_value, int):
                    # Integer parameter
                    param_values[param_name] = st.number_input(
                        param_info.get("description", param_name),
                        value=default_value,
                        key=f"param_{param_name}"
                    )
                elif isinstance(default_value, float):
                    # Float parameter
                    param_values[param_name] = st.number_input(
                        param_info.get("description", param_name),
                        value=default_value,
                        step=0.1,
                        key=f"param_{param_name}"
                    )
                elif isinstance(default_value, list):
                    # List parameter - use multiselect
                    options = param_info.get("options", default_value)
                    param_values[param_name] = st.multiselect(
                        param_info.get("description", param_name),
                        options=options,
                        default=default_value,
                        key=f"param_{param_name}"
                    )
                else:
                    # Default to string parameter
                    param_values[param_name] = st.text_input(
                        param_info.get("description", param_name),
                        value=str(default_value),
                        key=f"param_{param_name}"
                    )
        else:
            st.info("This playbook does not have any configurable parameters.")
        
        # Execution options
        st.markdown("### Execution Options")
        
        execute_options = {
            "debug_mode": st.checkbox("Debug Mode", value=False, key="debug_mode"),
            "async_execution": st.checkbox("Asynchronous Execution", value=True, key="async_execution"),
            "timeout": st.number_input("Timeout (seconds)", value=300, min_value=30, max_value=1800, step=30)
        }
        
        # Execute button
        if st.form_submit_button("Execute Playbook", type="primary"):
            # Call the execute callback
            on_execute(playbook, {
                "parameters": param_values,
                "options": execute_options
            })
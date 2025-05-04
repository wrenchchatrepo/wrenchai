"""Playbook Schema Integration.

This module integrates our UI components with the existing playbook schema.
"""

import streamlit as st
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
import os
import yaml

from streamlit_app.components.playbook_components import PlaybookManager, playbook_browser, playbook_details, playbook_editor
from core.playbook_schema import Playbook, PlaybookStep
from core.playbook_validator import perform_full_validation, validate_playbook

class PlaybookSchemaManager(PlaybookManager):
    """Playbook manager that uses the existing playbook schema."""
    
    def __init__(self, playbooks_dir: Union[str, Path]):
        """Initialize the manager with the core Playbook model.
        
        Args:
            playbooks_dir: Directory containing playbook files
        """
        super().__init__(
            playbook_model=Playbook,
            playbooks_dir=playbooks_dir,
            template_playbook=self._create_default_template()
        )
    
    def _create_default_template(self) -> Dict[str, Any]:
        """Create a default template for new playbooks."""
        return {
            "name": "New Playbook",
            "description": "A new WrenchAI playbook",
            "steps": [
                {
                    "step_id": "metadata",
                    "type": "standard",
                    "description": "Playbook metadata",
                    "metadata": {
                        "name": "New Playbook",
                        "description": "A new WrenchAI playbook",
                        "tools": ["core_tools"],
                        "agents": ["DefaultAgent"],
                        "agent_llms": {"DefaultAgent": "gpt-4"}
                    },
                    "next": "step1"
                },
                {
                    "step_id": "step1",
                    "type": "standard",
                    "description": "First step",
                    "agent": "DefaultAgent",
                    "operation": "default_operation",
                    "parameters": {}
                }
            ]
        }
    
    def validate_playbook(self, playbook_path: Union[str, Path]) -> Tuple[bool, Optional[str], Optional[Playbook]]:
        """Validate a playbook using the core validator.
        
        Args:
            playbook_path: Path to the playbook file
            
        Returns:
            Tuple of (is_valid, error_message, playbook_instance)
        """
        return perform_full_validation(playbook_path)
    
    def get_available_agents(self) -> List[str]:
        """Get a list of available agent types.
        
        Returns:
            List of agent type names
        """
        # TODO: Get this from a dynamic source
        return [
            "DefaultAgent",
            "CodeGeneratorAgent",
            "ContentWriterAgent",
            "DocusaurusAgent",
            "ResearchAgent",
            "SystemDesignAgent"
        ]
    
    def get_available_operations(self, agent_type: Optional[str] = None) -> List[str]:
        """Get a list of available operations.
        
        Args:
            agent_type: Optional agent type to filter operations
            
        Returns:
            List of operation names
        """
        # TODO: Get this from a dynamic source
        operations = {
            "DefaultAgent": ["default_operation", "analyze", "summarize"],
            "CodeGeneratorAgent": ["generate_code", "refactor", "test", "document"],
            "ContentWriterAgent": ["write_content", "edit_content", "translate"],
            "DocusaurusAgent": ["init_docusaurus", "generate_content", "deploy"],
            "ResearchAgent": ["research", "analyze", "summarize"],
            "SystemDesignAgent": ["design_system", "create_diagram", "document_architecture"]
        }
        
        if agent_type and agent_type in operations:
            return operations[agent_type]
        
        # Return all operations if no agent type specified
        all_ops = []
        for ops in operations.values():
            all_ops.extend(ops)
        return sorted(list(set(all_ops)))
    
    def get_available_tools(self) -> List[str]:
        """Get a list of available tools.
        
        Returns:
            List of tool names
        """
        # TODO: Get this from a dynamic source
        return [
            "core_tools",
            "web_search",
            "code_generation",
            "github_tool",
            "docusaurus_tool",
            "file_tool",
            "database_tool"
        ]
    
    def get_available_llms(self) -> Dict[str, List[str]]:
        """Get a mapping of available LLMs for each agent type.
        
        Returns:
            Dictionary mapping agent types to list of LLM identifiers
        """
        # TODO: Get this from a dynamic source
        return {
            "DefaultAgent": ["gpt-4", "gpt-3.5-turbo"],
            "CodeGeneratorAgent": ["gpt-4", "claude-2"],
            "ContentWriterAgent": ["gpt-4", "claude-2", "gpt-3.5-turbo"],
            "DocusaurusAgent": ["gpt-4"],
            "ResearchAgent": ["gpt-4", "claude-2"],
            "SystemDesignAgent": ["gpt-4"]
        }


def playbook_schema_browser(playbooks_dir: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Create a browser for playbooks using the core schema.
    
    Args:
        playbooks_dir: Directory containing playbook files
        
    Returns:
        Selected playbook metadata or None
    """
    manager = PlaybookSchemaManager(playbooks_dir)
    return playbook_browser(manager)


def playbook_schema_editor(playbooks_dir: Union[str, Path], 
                         playbook: Optional[Dict[str, Any]] = None) -> Optional[Playbook]:
    """Create an editor for playbooks using the core schema.
    
    Args:
        playbooks_dir: Directory containing playbook files
        playbook: Optional playbook metadata to edit
        
    Returns:
        Saved playbook instance or None
    """
    manager = PlaybookSchemaManager(playbooks_dir)
    
    # Define save callback to validate playbook
    def on_save(playbook_instance, path):
        # Validate the saved playbook
        valid, error, _ = manager.validate_playbook(path)
        if valid:
            st.success(f"Playbook saved and validated successfully!")
        else:
            st.warning(f"Playbook saved but has validation issues: {error}")
    
    return playbook_editor(manager, playbook, on_save=on_save)


def create_playbook_step_form(step_type: str, step_id: str, on_submit=None):
    """Create a form for a specific playbook step type.
    
    Args:
        step_type: Type of step (standard, work_in_parallel, etc.)
        step_id: ID for the step
        on_submit: Callback when form is submitted
        
    Returns:
        Form UI for the specified step type
    """
    manager = PlaybookSchemaManager("temp")
    agents = manager.get_available_agents()
    operations = manager.get_available_operations()
    tools = manager.get_available_tools()
    
    st.markdown(f"### Create {step_type.replace('_', ' ').title()} Step")
    
    with st.form(f"step_form_{step_id}"):
        # Common fields for all step types
        description = st.text_input("Description", key=f"description_{step_id}")
        next_step = st.text_input("Next Step ID (leave empty for final step)", key=f"next_{step_id}")
        
        # Type-specific fields
        if step_type == "standard":
            agent = st.selectbox("Agent", agents, key=f"agent_{step_id}")
            operation = st.selectbox("Operation", manager.get_available_operations(agent), key=f"operation_{step_id}")
            selected_tools = st.multiselect("Tools", tools, key=f"tools_{step_id}")
            
            # Parameters as JSON
            parameters_json = st.text_area("Parameters (JSON)", "{}", key=f"parameters_{step_id}")
            try:
                import json
                parameters = json.loads(parameters_json)
            except Exception:
                parameters = {}
        
        elif step_type == "metadata":
            st.write("Metadata fields:")
            name = st.text_input("Playbook Name", key=f"name_{step_id}")
            meta_description = st.text_area("Playbook Description", key=f"meta_description_{step_id}")
            meta_tools = st.multiselect("Tools", tools, key=f"meta_tools_{step_id}")
            meta_agents = st.multiselect("Agents", agents, key=f"meta_agents_{step_id}")
            
            # Agent LLMs
            st.write("Agent LLMs:")
            agent_llms = {}
            for agent in meta_agents:
                llms = manager.get_available_llms().get(agent, ["gpt-4"])
                agent_llms[agent] = st.selectbox(f"LLM for {agent}", llms, key=f"llm_{agent}_{step_id}")
        
        elif step_type == "partner_feedback_loop":
            st.write("Agent Roles:")
            roles = ["primary", "reviewer", "editor"]
            agents_dict = {}
            for role in roles:
                agents_dict[role] = st.selectbox(f"Agent for {role} role", agents, key=f"agent_{role}_{step_id}")
            
            st.write("Operations:")
            operations_list = []
            for i, role in enumerate(["primary", "reviewer"]):
                operation_name = st.text_input(f"Operation for {role}", key=f"operation_{role}_{step_id}")
                operations_list.append({"role": role, "name": operation_name})
            
            iterations = st.number_input("Number of iterations", min_value=1, max_value=10, value=2, key=f"iterations_{step_id}")
        
        # Submit button
        submitted = st.form_submit_button("Add Step")
        
        if submitted:
            # Create step dictionary based on type
            if step_type == "standard":
                step = {
                    "step_id": step_id,
                    "type": step_type,
                    "description": description,
                    "agent": agent,
                    "operation": operation,
                    "tools": selected_tools,
                    "parameters": parameters
                }
            elif step_type == "metadata":
                step = {
                    "step_id": step_id,
                    "type": "standard",
                    "description": description,
                    "metadata": {
                        "name": name,
                        "description": meta_description,
                        "tools": meta_tools,
                        "agents": meta_agents,
                        "agent_llms": agent_llms
                    }
                }
            elif step_type == "partner_feedback_loop":
                step = {
                    "step_id": step_id,
                    "type": step_type,
                    "description": description,
                    "agents": agents_dict,
                    "operations": operations_list,
                    "iterations": iterations
                }
            else:
                step = {
                    "step_id": step_id,
                    "type": step_type,
                    "description": description
                }
            
            # Add next step if provided
            if next_step:
                step["next"] = next_step
            
            # Call submit callback if provided
            if on_submit:
                on_submit(step)
            
            return step
    
    return None
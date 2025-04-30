"""Playbook validator for WrenchAI playbooks.

This module provides functions for validating playbooks against the
standardized schema and providing detailed error messages.
"""

from typing import Dict, List, Any, Tuple, Optional
from pydantic import ValidationError
import yaml
import logging
from pathlib import Path

from core.playbook_schema import Playbook, PlaybookStep, StepType

# Configure logging
logger = logging.getLogger(__name__)

def validate_playbook(playbook_dict: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate a playbook dictionary against the schema.
    
    Args:
        playbook_dict: The playbook as a dictionary
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        Playbook(**playbook_dict)
        return True, None
    except ValidationError as e:
        error_message = f"Playbook validation failed: {str(e)}"
        logger.error(error_message)
        return False, error_message

def validate_playbook_from_yaml(yaml_content: str) -> Tuple[bool, Optional[str]]:
    """Validate a playbook from YAML content.
    
    Args:
        yaml_content: The playbook content as YAML string
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        data = yaml.safe_load(yaml_content)
        if isinstance(data, list):
            # Handle list-based format (convert to dict with steps)
            playbook_dict = {"steps": data}
        else:
            playbook_dict = data
        
        return validate_playbook(playbook_dict)
    except yaml.YAMLError as e:
        error_message = f"Invalid YAML format: {str(e)}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Unexpected error during validation: {str(e)}"
        logger.error(error_message)
        return False, error_message

def validate_playbook_file(file_path: str) -> Tuple[bool, Optional[str]]:
    """Validate a playbook from a YAML file.
    
    Args:
        file_path: Path to the playbook YAML file
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        with open(file_path, 'r') as f:
            return validate_playbook_from_yaml(f.read())
    except FileNotFoundError:
        error_message = f"Playbook file not found: {file_path}"
        logger.error(error_message)
        return False, error_message
    except Exception as e:
        error_message = f"Failed to read playbook file: {str(e)}"
        logger.error(error_message)
        return False, error_message

def check_step_dependencies(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """Check that all step dependencies (next) refer to valid step IDs.
    
    Args:
        playbook: The validated Playbook object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    step_ids = {step.step_id for step in playbook.steps}
    for step in playbook.steps:
        if step.next and step.next not in step_ids:
            error_message = f"Step '{step.step_id}' references non-existent next step '{step.next}'"
            logger.error(error_message)
            return False, error_message
    
    return True, None

def check_agent_references(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """Check that all agent references are valid.
    
    Args:
        playbook: The validated Playbook object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    agents = set(playbook.agents or [])
    
    for step in playbook.steps:
        # Check standard agent reference
        if step.type == StepType.STANDARD and step.agent and step.agent not in agents:
            error_message = f"Step '{step.step_id}' references non-existent agent '{step.agent}'"
            logger.error(error_message)
            return False, error_message
        
        # Check partner feedback loop agents
        if step.type == StepType.PARTNER_FEEDBACK_LOOP and step.agents:
            for role, agent in step.agents.items():
                if agent not in agents:
                    error_message = f"Step '{step.step_id}' references non-existent agent '{agent}' for role '{role}'"
                    logger.error(error_message)
                    return False, error_message
        
        # Check handoff step agents
        if step.type == StepType.HANDOFF:
            if step.primary_agent and step.primary_agent not in agents:
                error_message = f"Step '{step.step_id}' references non-existent primary agent '{step.primary_agent}'"
                logger.error(error_message)
                return False, error_message
            
            if step.handoff_conditions:
                for condition in step.handoff_conditions:
                    if condition.target_agent not in agents:
                        error_message = f"Step '{step.step_id}' references non-existent target agent '{condition.target_agent}'"
                        logger.error(error_message)
                        return False, error_message
    
    return True, None

def check_tool_references(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """Check that all tool references are valid.
    
    Args:
        playbook: The validated Playbook object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    tools = set(playbook.tools or [])
    
    for step in playbook.steps:
        if step.tools:
            for tool in step.tools:
                if tool not in tools:
                    error_message = f"Step '{step.step_id}' references non-existent tool '{tool}'"
                    logger.error(error_message)
                    return False, error_message
    
    return True, None

def check_agent_llm_mappings(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """Check that all agent-LLM mappings are valid.
    
    Args:
        playbook: The validated Playbook object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Skip if no agent_llms defined
    if not hasattr(playbook, 'agent_llms') or not playbook.agent_llms:
        return True, None
        
    # Check that all agents are defined in the playbook
    agents = set(playbook.agents or [])
    
    for agent_name in playbook.agent_llms:
        if agent_name not in agents:
            error_message = f"Agent-LLM mapping references non-existent agent '{agent_name}'"
            logger.error(error_message)
            return False, error_message
    
    # Validate LLM IDs
    try:
        # Import here to avoid circular imports
        from core.agents.agent_definitions import LLMProvider
        
        # Get all known LLM IDs
        valid_llm_ids = set(provider.value for provider in LLMProvider)
        
        # Add any custom LLM IDs defined in config
        try:
            import os
            import yaml
            config_path = os.path.join("core", "configs", "llms.yaml")
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    llm_config = yaml.safe_load(f)
                    if llm_config and "llms" in llm_config:
                        for llm in llm_config["llms"]:
                            if "id" in llm:
                                valid_llm_ids.add(llm["id"])
        except Exception as e:
            logger.warning(f"Failed to load custom LLM IDs: {e}")
        
        # Check each LLM ID
        for agent_name, llm_id in playbook.agent_llms.items():
            if llm_id not in valid_llm_ids:
                logger.warning(f"Agent-LLM mapping for '{agent_name}' uses unknown LLM ID '{llm_id}'")
                # Don't fail validation, just warn - the ID might be valid in the runtime environment
    
    except ImportError:
        logger.warning("Could not import LLMProvider for validation, skipping LLM ID checks")
    
    return True, None

def validate_playbook_consistency(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """Validate the internal consistency of a playbook.
    
    Args:
        playbook: The validated Playbook object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check step dependencies
    valid, error = check_step_dependencies(playbook)
    if not valid:
        return False, error
    
    # Check agent references
    valid, error = check_agent_references(playbook)
    if not valid:
        return False, error
    
    # Check tool references
    valid, error = check_tool_references(playbook)
    if not valid:
        return False, error
    
    # Check agent-LLM mappings
    valid, error = check_agent_llm_mappings(playbook)
    if not valid:
        return False, error
    
    return True, None

def perform_full_validation(playbook_path: str) -> Tuple[bool, Optional[str], Optional[Playbook]]:
    """Perform full validation of a playbook file.
    
    Args:
        playbook_path: Path to the playbook YAML file
        
    Returns:
        Tuple of (is_valid, error_message, playbook_object)
    """
    # Validate file format
    valid, error = validate_playbook_file(playbook_path)
    if not valid:
        return False, error, None
    
    try:
        # Load as Playbook object
        playbook = Playbook.from_yaml_file(playbook_path)
        
        # Check internal consistency
        valid, error = validate_playbook_consistency(playbook)
        if not valid:
            return False, error, None
        
        return True, None, playbook
    except Exception as e:
        error_message = f"Error processing playbook: {str(e)}"
        logger.error(error_message)
        return False, error_message, None
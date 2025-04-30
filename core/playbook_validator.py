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
    """
    Validates a playbook dictionary against the Playbook schema.
    
    Attempts to instantiate a Playbook object using the provided dictionary. Returns (True, None) if the dictionary is valid; otherwise, returns (False, error_message) with details about the validation failure.
    """
    try:
        Playbook(**playbook_dict)
        return True, None
    except ValidationError as e:
        error_message = f"Playbook validation failed: {str(e)}"
        logger.error(error_message)
        return False, error_message

def validate_playbook_from_yaml(yaml_content: str) -> Tuple[bool, Optional[str]]:
    """
    Validates a playbook provided as a YAML string.
    
    Parses the YAML content and validates it against the playbook schema. Handles both dictionary and list-based YAML formats. Returns a tuple indicating validity and an error message if invalid.
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
    """
    Validates a playbook YAML file against the schema and reports errors.
    
    Attempts to read the specified YAML file, parse its contents, and validate it as a playbook. Returns a tuple indicating whether the playbook is valid and an error message if validation fails.
    
    Args:
        file_path: Path to the playbook YAML file.
    
    Returns:
        A tuple (is_valid, error_message), where is_valid is True if the playbook is valid, otherwise False. error_message contains details if validation fails, or None if successful.
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
    """
    Checks that all 'next' step references in the playbook point to valid step IDs.
    
    Returns:
        A tuple (is_valid, error_message), where is_valid is True if all step dependencies are valid, and error_message contains details if an invalid reference is found.
    """
    step_ids = {step.step_id for step in playbook.steps}
    for step in playbook.steps:
        if step.next and step.next not in step_ids:
            error_message = f"Step '{step.step_id}' references non-existent next step '{step.next}'"
            logger.error(error_message)
            return False, error_message
    
    return True, None

def check_agent_references(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """
    Validates that all agent references in the playbook steps exist in the declared agent list.
    
    Checks agent references in standard steps, partner feedback loop steps, and handoff steps. Returns a tuple indicating validity and an error message if an invalid agent reference is found.
    
    Returns:
        A tuple (is_valid, error_message), where is_valid is True if all agent references are valid, otherwise False with an error message.
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
    """
    Validates that all tools referenced in playbook steps exist in the playbook's tool list.
    
    Returns:
        A tuple containing a boolean indicating validity and an error message if an invalid tool reference is found; otherwise, (True, None).
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

def validate_playbook_consistency(playbook: Playbook) -> Tuple[bool, Optional[str]]:
    """
    Checks that a playbook's steps, agent references, and tool references are internally consistent.
    
    Performs dependency checks to ensure all referenced steps, agents, and tools exist within the playbook. Returns a tuple indicating validity and an error message if any inconsistency is found.
    
    Returns:
        A tuple (is_valid, error_message), where is_valid is True if the playbook is consistent, otherwise False with a descriptive error message.
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
    
    return True, None

def perform_full_validation(playbook_path: str) -> Tuple[bool, Optional[str], Optional[Playbook]]:
    """
    Performs comprehensive validation of a playbook YAML file.
    
    Validates the file format, loads the playbook as a Playbook object, and checks internal consistency. Returns a tuple indicating validity, an error message if invalid, and the loaded Playbook object if successful.
    
    Args:
        playbook_path: Path to the playbook YAML file.
    
    Returns:
        A tuple (is_valid, error_message, playbook_object), where is_valid is True if the playbook is valid, error_message contains details if invalid, and playbook_object is the loaded Playbook instance or None.
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
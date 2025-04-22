# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import yaml
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError, root_validator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("playbook-validator")

# Define validation models
class WorkflowStep(BaseModel):
    """Base model for a workflow step"""
    step_id: str
    type: str
    description: str
    next: Optional[str] = None
    
    @root_validator
    def validate_step(cls, values):
        step_type = values.get('type')
        
        # Validate type-specific fields
        if step_type == 'standard':
            assert 'agent' in values, f"Step {values.get('step_id')}: 'standard' type requires 'agent' field"
            assert 'operation' in values, f"Step {values.get('step_id')}: 'standard' type requires 'operation' field"
        
        elif step_type == 'work_in_parallel':
            assert 'agents' in values, f"Step {values.get('step_id')}: 'work_in_parallel' type requires 'agents' field"
        
        elif step_type == 'partner_feedback_loop':
            assert 'agents' in values, f"Step {values.get('step_id')}: 'partner_feedback_loop' type requires 'agents' field"
            assert 'operations' in values, f"Step {values.get('step_id')}: 'partner_feedback_loop' type requires 'operations' field"
            assert 'iterations' in values, f"Step {values.get('step_id')}: 'partner_feedback_loop' type requires 'iterations' field"
        
        elif step_type == 'self_feedback_loop':
            assert 'agent' in values, f"Step {values.get('step_id')}: 'self_feedback_loop' type requires 'agent' field"
            assert 'operations' in values, f"Step {values.get('step_id')}: 'self_feedback_loop' type requires 'operations' field"
            assert 'iterations' in values, f"Step {values.get('step_id')}: 'self_feedback_loop' type requires 'iterations' field"
            
        elif step_type == 'process':
            assert 'agent' in values, f"Step {values.get('step_id')}: 'process' type requires 'agent' field"
            assert 'process' in values, f"Step {values.get('step_id')}: 'process' type requires 'process' field"
        
        elif step_type == 'versus':
            assert 'agents' in values, f"Step {values.get('step_id')}: 'versus' type requires 'agents' field"
            assert 'evaluation_criteria' in values, f"Step {values.get('step_id')}: 'versus' type requires 'evaluation_criteria' field"
            assert 'judge' in values, f"Step {values.get('step_id')}: 'versus' type requires 'judge' field"
        
        elif step_type == 'handoff':
            assert 'primary_agent' in values, f"Step {values.get('step_id')}: 'handoff' type requires 'primary_agent' field"
            assert 'operation' in values, f"Step {values.get('step_id')}: 'handoff' type requires 'operation' field"
            assert 'handoff_conditions' in values, f"Step {values.get('step_id')}: 'handoff' type requires 'handoff_conditions' field"
        
        return values

class Playbook(BaseModel):
    """Validation model for a playbook"""
    name: str
    description: str
    workflow: List[Dict[str, Any]]
    tools_allowed: List[str]
    agents: List[str]
    
    @root_validator
    def validate_workflow(cls, values):
        workflow = values.get('workflow', [])
        
        # Check for missing next step references
        step_ids = set(step['step_id'] for step in workflow)
        last_step_index = len(workflow) - 1
        
        for i, step in enumerate(workflow):
            # Skip checking 'next' for the last step
            if i == last_step_index:
                continue
                
            if 'next' not in step:
                logger.warning(f"Step {step['step_id']} is not the last step but doesn't have a 'next' field")
            elif step['next'] not in step_ids:
                logger.error(f"Step {step['step_id']} references non-existent step '{step['next']}' in 'next' field")
        
        # Validate workflow steps
        for step in workflow:
            try:
                WorkflowStep(**step)
            except (ValidationError, AssertionError) as e:
                logger.error(f"Step {step.get('step_id', 'unknown')} validation failed: {str(e)}")
        
        return values

def validate_playbook(playbook_path: str) -> bool:
    """Validate a playbook configuration
    
    Args:
        playbook_path: Path to the playbook YAML file
        
    Returns:
        True if validation passed, False otherwise
    """
    if not os.path.exists(playbook_path):
        logger.error(f"Playbook file not found: {playbook_path}")
        return False
    
    try:
        # Load the playbook
        with open(playbook_path, 'r') as f:
            playbook_data = yaml.safe_load(f)
            
        # Check if it's standalone or part of a playbooks collection
        if 'playbooks' in playbook_data:
            # It's a collection
            for playbook in playbook_data['playbooks']:
                try:
                    Playbook(**playbook)
                    logger.info(f"Playbook '{playbook['name']}' is valid")
                except ValidationError as e:
                    logger.error(f"Playbook '{playbook.get('name', 'unknown')}' validation failed: {str(e)}")
                    return False
        else:
            # It's a standalone playbook
            try:
                Playbook(**playbook_data)
                logger.info(f"Playbook '{playbook_data['name']}' is valid")
            except ValidationError as e:
                logger.error(f"Playbook validation failed: {str(e)}")
                return False
        
        return True
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

def main():
    """Command-line entry point"""
    if len(sys.argv) < 2:
        print("Usage: python -m core.tools.validate_playbook <playbook_path.yaml>")
        sys.exit(1)
        
    playbook_path = sys.argv[1]
    success = validate_playbook(playbook_path)
    
    if success:
        logger.info("Playbook validation successful!")
        sys.exit(0)
    else:
        logger.error("Playbook validation failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
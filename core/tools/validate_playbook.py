# MIT License - Copyright (c) 2024 Wrench AI
# For full license information, see the LICENSE file in the repo root.

import os
import sys
import yaml
import logging
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field, ValidationError, model_validator

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger("playbook-validator")

# Define validation models
class WorkflowStep(BaseModel):
    """Base model for a workflow step"""
    step_id: str
    type: str
    description: str
    next: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_step(self) -> 'WorkflowStep':
        values = self.model_dump()
        step_type = values.get('type')
        step_id = values.get('step_id')
        
        # Validate type-specific fields
        if step_type == 'standard':
            if 'agent' not in values:
                logger.warning(f"Step {step_id}: 'standard' type typically requires 'agent' field")
            if 'operation' not in values:
                logger.warning(f"Step {step_id}: 'standard' type typically requires 'operation' field")
        
        elif step_type == 'work_in_parallel':
            if 'agents' not in values:
                logger.warning(f"Step {step_id}: 'work_in_parallel' type typically requires 'agents' field")
        
        elif step_type == 'partner_feedback_loop':
            if 'agents' not in values:
                logger.warning(f"Step {step_id}: 'partner_feedback_loop' type typically requires 'agents' field")
            if 'operations' not in values:
                logger.warning(f"Step {step_id}: 'partner_feedback_loop' type typically requires 'operations' field")
            if 'iterations' not in values:
                logger.warning(f"Step {step_id}: 'partner_feedback_loop' type typically requires 'iterations' field")
        
        elif step_type == 'self_feedback_loop':
            if 'agent' not in values:
                logger.warning(f"Step {step_id}: 'self_feedback_loop' type typically requires 'agent' field")
            if 'operations' not in values:
                logger.warning(f"Step {step_id}: 'self_feedback_loop' type typically requires 'operations' field")
            if 'iterations' not in values:
                logger.warning(f"Step {step_id}: 'self_feedback_loop' type typically requires 'iterations' field")
            
        elif step_type == 'process':
            if 'agent' not in values:
                logger.warning(f"Step {step_id}: 'process' type typically requires 'agent' field")
            if 'process' not in values:
                logger.warning(f"Step {step_id}: 'process' type typically requires 'process' field")
        
        elif step_type == 'versus':
            if 'agents' not in values:
                logger.warning(f"Step {step_id}: 'versus' type typically requires 'agents' field")
            if 'evaluation_criteria' not in values:
                logger.warning(f"Step {step_id}: 'versus' type typically requires 'evaluation_criteria' field")
            if 'judge' not in values:
                logger.warning(f"Step {step_id}: 'versus' type typically requires 'judge' field")
        
        elif step_type == 'handoff':
            if 'primary_agent' not in values:
                logger.warning(f"Step {step_id}: 'handoff' type typically requires 'primary_agent' field")
            if 'operation' not in values:
                logger.warning(f"Step {step_id}: 'handoff' type typically requires 'operation' field")
            if 'handoff_conditions' not in values:
                logger.warning(f"Step {step_id}: 'handoff' type typically requires 'handoff_conditions' field")
        
        return self

class Playbook(BaseModel):
    """Validation model for a playbook"""
    name: str
    description: str
    workflow: List[Dict[str, Any]]
    tools_allowed: List[str]
    agents: List[str]
    
    @model_validator(mode='after')
    def validate_workflow(self) -> 'Playbook':
        workflow = self.workflow
        
        # Check for missing next step references
        step_ids = set(step.get('step_id') for step in workflow)
        last_step_index = len(workflow) - 1
        
        for i, step in enumerate(workflow):
            # Skip checking 'next' for the last step
            if i == last_step_index:
                continue
                
            if 'next' not in step:
                logger.warning(f"Step {step.get('step_id')} is not the last step but doesn't have a 'next' field")
            elif step.get('next') not in step_ids:
                logger.error(f"Step {step.get('step_id')} references non-existent step '{step.get('next')}' in 'next' field")
        
        # Validate workflow steps
        for step in workflow:
            try:
                WorkflowStep(**step)
            except ValidationError as e:
                logger.error(f"Step {step.get('step_id', 'unknown')} validation failed: {str(e)}")
        
        return self

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
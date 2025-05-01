"""Standardized schema for WrenchAI playbooks.

This module defines a unified schema for playbooks that works with both 
validation and execution code. It uses Pydantic for validation and
provides utilities for converting between different formats.
"""

from typing import Dict, List, Union, Optional, Any, Literal, Set
from pydantic import BaseModel, Field, validator, root_validator
from datetime import datetime
import yaml
from enum import Enum
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Define enums for constrained fields
class StepType(str, Enum):
    STANDARD = "standard"
    WORK_IN_PARALLEL = "work_in_parallel"
    SELF_FEEDBACK_LOOP = "self_feedback_loop"
    PARTNER_FEEDBACK_LOOP = "partner_feedback_loop"
    PROCESS = "process"
    VERSUS = "versus"
    HANDOFF = "handoff"

class AggregatioType(str, Enum):
    MERGE = "merge"
    APPEND = "append"
    FILTER = "filter"

class DistributionType(str, Enum):
    SPLIT = "split"
    DUPLICATE = "duplicate"
    ROUND_ROBIN = "round_robin"

# Step-specific models
class StepMetadata(BaseModel):
    """Metadata for the playbook, usually in the first step."""
    name: str
    description: str
    sections: Optional[List[str]] = None
    tools: List[str]
    agents: List[str]
    agent_llms: Dict[str, str]

class Operation(BaseModel):
    """Operation definition for partner feedback loops and other multi-operation steps."""
    role: str
    name: str

class InputDistribution(BaseModel):
    """Input distribution configuration for parallel steps."""
    type: DistributionType
    field: Optional[str] = None

class OutputAggregation(BaseModel):
    """Output aggregation configuration for parallel steps."""
    type: AggregatioType
    strategy: str

class ProcessOperation(BaseModel):
    """Operation definition for process steps with conditions."""
    operation: str
    condition: Optional[str] = None
    failure_action: Optional[str] = None
    
    @validator('condition')
    def validate_condition(cls, v):
        """Validate condition syntax if present."""
        if v is not None:
            from core.condition_evaluator import validate_condition
            valid, error = validate_condition(v)
            if not valid:
                raise ValueError(f"Invalid condition syntax: {error}")
        return v

class HandoffCondition(BaseModel):
    """Condition for handoff steps."""
    condition: str
    target_agent: str
    operation: str
    
    @validator('condition')
    def validate_condition(cls, v):
        """Validate condition syntax."""
        from core.condition_evaluator import validate_condition
        valid, error = validate_condition(v)
        if not valid:
            raise ValueError(f"Invalid condition syntax: {error}")
        return v

class InputConfig(BaseModel):
    """Input configuration for steps."""
    source: str

class OutputConfig(BaseModel):
    """Output configuration for steps."""
    destination: str

# Main step model with conditional fields based on type
class PlaybookStep(BaseModel):
    """Unified model for all step types in a playbook."""
    step_id: str
    type: StepType
    description: str
    next: Optional[str] = None
    
    # Fields for standard steps
    agent: Optional[str] = None
    operation: Optional[str] = None
    tools: Optional[List[str]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Fields for metadata steps
    metadata: Optional[StepMetadata] = None
    
    # Fields for partner_feedback_loop
    agents: Optional[Dict[str, str]] = None  # Maps roles to agent names
    operations: Optional[List[Operation]] = None
    iterations: Optional[int] = None
    
    # Fields for work_in_parallel
    input_distribution: Optional[InputDistribution] = None
    output_aggregation: Optional[OutputAggregation] = None
    
    # Fields for process steps
    input: Optional[InputConfig] = None
    process: Optional[List[ProcessOperation]] = None
    output: Optional[OutputConfig] = None
    
    # Fields for handoff steps
    primary_agent: Optional[str] = None
    handoff_conditions: Optional[List[HandoffCondition]] = None
    completion_action: Optional[str] = None
    
    @validator('agent')
    def validate_agent_for_standard(cls, v, values):
        """
        Validates that the 'agent' field is present for standard step types.
        
        Raises:
            ValueError: If the step type is standard and the agent is not provided.
        """
        if values.get('type') == StepType.STANDARD and not v:
            raise ValueError("agent is required for standard steps")
        return v
    
    @validator('agents')
    def validate_agents_for_partner_loop(cls, v, values):
        """
        Ensures that the 'agents' field is provided for partner_feedback_loop steps.
        
        Raises:
            ValueError: If 'agents' is missing when the step type is partner_feedback_loop.
        """
        if values.get('type') == StepType.PARTNER_FEEDBACK_LOOP and not v:
            raise ValueError("agents is required for partner_feedback_loop steps")
        return v
    
    @validator('operations')
    def validate_operations_for_partner_loop(cls, v, values):
        """
        Validates that the operations field is provided for partner_feedback_loop steps.
        
        Raises:
            ValueError: If the step type is partner_feedback_loop and operations are missing.
        """
        if values.get('type') == StepType.PARTNER_FEEDBACK_LOOP and not v:
            raise ValueError("operations is required for partner_feedback_loop steps")
        return v
    
    @validator('process')
    def validate_process_for_process_step(cls, v, values):
        """
        Validates that the 'process' field is present for steps of type PROCESS.
        
        Raises:
            ValueError: If the step type is PROCESS and the 'process' field is missing or empty.
        """
        if values.get('type') == StepType.PROCESS and not v:
            raise ValueError("process is required for process steps")
        return v
    
    @validator('primary_agent')
    def validate_primary_agent_for_handoff(cls, v, values):
        """
        Validates that a primary agent is specified for handoff steps.
        
        Raises:
            ValueError: If the step type is 'HANDOFF' and no primary agent is provided.
        """
        if values.get('type') == StepType.HANDOFF and not v:
            raise ValueError("primary_agent is required for handoff steps")
        return v

class Playbook(BaseModel):
    """Main playbook model."""
    steps: List[PlaybookStep]
    
    # These fields are derived from the metadata step
    name: Optional[str] = None
    description: Optional[str] = None
    tools: Optional[List[str]] = None
    agents: Optional[List[str]] = None
    agent_llms: Optional[Dict[str, str]] = None
    sections: Optional[List[str]] = None
    
    class Config:
        schema_extra = {
            "example": {
                "name": "Docusaurus Portfolio",
                "description": "Generate a Docusaurus portfolio site",
                "steps": [
                    {
                        "step_id": "initialize_project",
                        "type": "standard",
                        "description": "Initialize the Docusaurus project",
                        "agent": "CodeGeneratorAgent",
                        "operation": "init_docusaurus",
                        "parameters": {"template": "portfolio"},
                        "next": "generate_content"
                    },
                    {
                        "step_id": "generate_content",
                        "type": "standard",
                        "description": "Generate content for the portfolio",
                        "agent": "CodeGeneratorAgent",
                        "operation": "generate_content",
                        "parameters": {"sections": ["about", "projects", "blog"]}
                    }
                ],
                "tools": ["code_generation", "github_tool"],
                "agents": ["CodeGeneratorAgent"]
            }
        }
    
    @root_validator(pre=True)
    def extract_metadata(cls, values):
        """
        Extracts playbook metadata fields from a step with step_id 'metadata', if present.
        
        If a metadata step exists within the steps list and contains a 'metadata' field,
        updates the playbook's top-level fields (name, description, tools, agents,
        agent_llms, sections) with values from the metadata.
        """
        steps = values.get('steps', [])
        if isinstance(steps, list) and steps:
            # Handle list-based playbook format (from YAML)
            metadata_step = next((step for step in steps if step.get('step_id') == 'metadata'), None)
            if metadata_step and 'metadata' in metadata_step:
                metadata = metadata_step['metadata']
                values['name'] = metadata.get('name', values.get('name'))
                values['description'] = metadata.get('description', values.get('description'))
                values['tools'] = metadata.get('tools', values.get('tools'))
                values['agents'] = metadata.get('agents', values.get('agents'))
                values['agent_llms'] = metadata.get('agent_llms', values.get('agent_llms'))
                values['sections'] = metadata.get('sections', values.get('sections'))
        return values

    def to_api_format(self) -> Dict[str, Any]:
        """
        Converts the playbook instance into a dictionary formatted for API execution.
        
        Returns:
            A dictionary containing the playbook name, input details (description, tools, agents, agent LLMs, sections, steps), and metadata with the current UTC timestamp and source.
        """
        return {
            "playbook": self.name,
            "input": {
                "description": self.description,
                "tools": self.tools,
                "agents": self.agents,
                "agent_llms": self.agent_llms,
                "sections": self.sections,
                "steps": [step.dict(exclude_none=True) for step in self.steps]
            },
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "source": "streamlit"
            }
        }

    @classmethod
    def from_yaml(cls, yaml_content: str) -> 'Playbook':
        """
        Parses YAML content and returns a Playbook instance.
        
        If the YAML represents a list, it is treated as the steps of the playbook; otherwise, the content is parsed as a dictionary of Playbook fields.
        
        Args:
            yaml_content: YAML string representing the playbook.
        
        Returns:
            A Playbook instance constructed from the provided YAML content.
        """
        data = yaml.safe_load(yaml_content)
        if isinstance(data, list):
            # Handle list-based playbook format
            return cls(steps=data)
        return cls(**data)
    
    @classmethod
    def from_yaml_file(cls, file_path: str) -> 'Playbook':
        """
        Creates a Playbook instance by loading and parsing a YAML file.
        
        Args:
            file_path: Path to the YAML file containing the playbook definition.
        
        Returns:
            A Playbook instance parsed from the specified YAML file.
        """
        with open(file_path, 'r') as f:
            return cls.from_yaml(f.read())
    
    def to_yaml(self) -> str:
        """
        Serializes the playbook instance to a YAML-formatted string.
        
        Returns:
            A YAML string representation of the playbook, excluding fields with None values.
        """
        return yaml.dump(self.dict(exclude_none=True))

    def merge_user_config(self, user_config: Dict[str, Any]) -> 'Playbook':
        """
        Merges user-provided configuration into the playbook and returns a new Playbook instance.
        
        Updates top-level fields such as name, description, tools, agents, and sections if present in the user configuration. If 'projects' is specified, it is injected into the parameters of the step with step_id 'generate_content'. Any additional fields in the user configuration are also added to the playbook.
        """
        # Create a copy of the current playbook
        playbook_dict = self.dict(exclude_none=True)
        
        # Update top-level fields if present in user_config
        for field in ['name', 'description', 'tools', 'agents']:
            if field in user_config:
                playbook_dict[field] = user_config[field]
        
        # Special handling for sections if present in user_config
        if 'sections' in user_config:
            playbook_dict['sections'] = user_config['sections']
        
        # Update parameters in relevant steps
        if 'projects' in user_config and playbook_dict.get('steps'):
            # Find the content generation step
            for step in playbook_dict['steps']:
                if step.get('step_id') == 'generate_content':
                    step.setdefault('parameters', {})['projects'] = user_config['projects']
        
        # Add any additional fields from user_config
        for key, value in user_config.items():
            if key not in ['name', 'description', 'tools', 'agents', 'sections', 'projects']:
                playbook_dict[key] = value
        
        return Playbook(**playbook_dict)
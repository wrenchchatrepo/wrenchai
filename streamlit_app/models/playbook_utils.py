"""Utilities for working with playbook configuration models.

This module provides helper functions for creating, validating, and transforming
playbook configuration models.
"""

import os
import yaml
import json
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path
import logging
from datetime import datetime

from pydantic import ValidationError

from streamlit_app.models.playbook_config import (
    PlaybookConfig,
    PlaybookMetadata,
    PlaybookStep,
    ExecutionConfig,
    AgentConfig,
    Parameter,
    DocusaurusPortfolioConfig,
    PlaybookType,
    StepType,
    AgentType,
    LLMType,
    ToolType
)

logger = logging.getLogger(__name__)


def load_playbook_config(file_path: Union[str, Path]) -> Tuple[Optional[PlaybookConfig], Optional[str]]:
    """
    Load a playbook configuration from a YAML or JSON file.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        Tuple of (config, error_message)
    """
    try:
        file_path = Path(file_path)
        if not file_path.exists():
            return None, f"File not found: {file_path}"
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse based on file extension
        if file_path.suffix.lower() in ('.yaml', '.yml'):
            data = yaml.safe_load(content)
        elif file_path.suffix.lower() == '.json':
            data = json.loads(content)
        else:
            return None, f"Unsupported file type: {file_path.suffix}"
        
        # Try to parse as PlaybookConfig
        try:
            config = PlaybookConfig.model_validate(data)
            return config, None
        except ValidationError as e:
            # If it fails, check if it's using the legacy format
            return convert_legacy_format(data)
        
    except Exception as e:
        logger.error(f"Error loading playbook config from {file_path}: {str(e)}")
        return None, str(e)


def convert_legacy_format(data: Dict[str, Any]) -> Tuple[Optional[PlaybookConfig], Optional[str]]:
    """
    Convert legacy playbook format to the new PlaybookConfig model.
    
    Args:
        data: Dictionary of playbook data in legacy format
        
    Returns:
        Tuple of (config, error_message)
    """
    try:
        # Check if it's the legacy format with 'steps' as a list
        if 'steps' in data and isinstance(data['steps'], list):
            # Extract metadata from first step if it's a metadata step
            metadata = {}
            for step in data['steps']:
                if step.get('step_id') == 'metadata' and 'metadata' in step:
                    metadata = step['metadata']
                    break
            
            # Create PlaybookMetadata
            playbook_metadata = PlaybookMetadata(
                name=metadata.get('name', data.get('name', 'Unnamed Playbook')),
                description=metadata.get('description', data.get('description', 'No description')),
                type=PlaybookType.CUSTOM,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Convert steps
            converted_steps = []
            for step in data['steps']:
                try:
                    # Convert step type to enum if it's a string
                    step_type = step.get('type', 'standard')
                    if isinstance(step_type, str):
                        step['type'] = StepType(step_type)
                    
                    # Convert agent to enum if it's a string
                    agent = step.get('agent')
                    if agent and isinstance(agent, str):
                        step['agent'] = AgentType(agent)
                    
                    # Convert tools to enums if they're strings
                    tools = step.get('tools', [])
                    if tools and isinstance(tools, list):
                        converted_tools = []
                        for tool in tools:
                            if isinstance(tool, str):
                                converted_tools.append(ToolType(tool))
                            else:
                                converted_tools.append(tool)
                        step['tools'] = converted_tools
                    
                    converted_step = PlaybookStep.model_validate(step)
                    converted_steps.append(converted_step)
                except ValidationError as e:
                    logger.warning(f"Error converting step {step.get('step_id')}: {str(e)}")
                except ValueError as e:
                    logger.warning(f"Invalid enum value in step {step.get('step_id')}: {str(e)}")
            
            # Create agent configs
            agent_configs = {}
            if metadata.get('agents') and metadata.get('agent_llms'):
                for agent_name in metadata.get('agents', []):
                    llm = metadata.get('agent_llms', {}).get(agent_name, 'gpt-4')
                    agent_configs[agent_name] = AgentConfig(
                        agent_type=AgentType(agent_name),
                        llm=LLMType(llm),
                        tools=metadata.get('tools', [])
                    )
            
            # Create PlaybookConfig
            config = PlaybookConfig(
                metadata=playbook_metadata,
                steps=converted_steps,
                agents=agent_configs,
                execution=ExecutionConfig()
            )
            
            return config, None
        else:
            return None, "Could not recognize playbook format"
        
    except Exception as e:
        logger.error(f"Error converting legacy format: {str(e)}")
        return None, f"Error converting format: {str(e)}"


def save_playbook_config(config: PlaybookConfig, file_path: Union[str, Path], format: str = 'yaml') -> Tuple[bool, Optional[str]]:
    """
    Save a playbook configuration to a file.
    
    Args:
        config: The PlaybookConfig to save
        file_path: Path where to save the configuration
        format: Format to save as ('yaml' or 'json')
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        file_path = Path(file_path)
        
        # Create directory if it doesn't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary
        data = config.model_dump(exclude_none=True)
        
        # Update timestamp
        data['metadata']['updated_at'] = datetime.now().isoformat()
        
        # Save in specified format
        with open(file_path, 'w') as f:
            if format.lower() == 'yaml':
                yaml.dump(data, f, sort_keys=False, default_flow_style=False)
            elif format.lower() == 'json':
                json.dump(data, f, indent=2)
            else:
                return False, f"Unsupported format: {format}"
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error saving playbook config to {file_path}: {str(e)}")
        return False, str(e)


def convert_to_core_format(config: PlaybookConfig) -> Dict[str, Any]:
    """
    Convert a PlaybookConfig to the core.playbook_schema format.
    
    Args:
        config: The PlaybookConfig to convert
        
    Returns:
        Dictionary in format compatible with core.playbook_schema.Playbook
    """
    # Extract metadata
    metadata = {
        "name": config.metadata.name,
        "description": config.metadata.description,
        "tools": [tool.value for agent_config in config.agents.values() for tool in agent_config.tools],
        "agents": [agent for agent in config.agents.keys()],
        "agent_llms": {agent: config.agents[agent].llm.value for agent in config.agents.keys()}
    }
    
    # Convert steps
    steps = []
    
    # Add metadata step
    metadata_step = {
        "step_id": "metadata",
        "type": "standard",
        "description": "Playbook metadata",
        "metadata": metadata
    }
    
    # Add next field to metadata step if there are other steps
    if config.steps and len(config.steps) > 0:
        metadata_step["next"] = config.steps[0].step_id
    
    steps.append(metadata_step)
    
    # Convert regular steps
    for i, step in enumerate(config.steps):
        step_dict = step.model_dump(exclude_none=True)
        
        # Convert enums to strings
        if 'type' in step_dict and not isinstance(step_dict['type'], str):
            step_dict['type'] = step_dict['type'].value
            
        if 'agent' in step_dict and not isinstance(step_dict['agent'], str):
            step_dict['agent'] = step_dict['agent'].value
            
        if 'tools' in step_dict and isinstance(step_dict['tools'], list):
            step_dict['tools'] = [t.value if not isinstance(t, str) else t for t in step_dict['tools']]
        
        # Add next step reference if not the last step
        if i < len(config.steps) - 1 and 'next' not in step_dict:
            step_dict['next'] = config.steps[i + 1].step_id
        
        steps.append(step_dict)
    
    # Create the final structure
    return {
        "name": config.metadata.name,
        "description": config.metadata.description,
        "steps": steps,
        "tools": metadata["tools"],
        "agents": metadata["agents"],
        "agent_llms": metadata["agent_llms"]
    }


def create_docusaurus_playbook() -> PlaybookConfig:
    """
    Create a default Docusaurus portfolio playbook configuration.
    
    Returns:
        A PlaybookConfig for the Docusaurus portfolio playbook
    """
    # Create metadata
    metadata = PlaybookMetadata(
        name="Docusaurus Portfolio Generator",
        description="Generate a beautiful portfolio website using Docusaurus",
        type=PlaybookType.PORTFOLIO,
        category=PlaybookCategory.PORTFOLIO,
        version="1.0.0",
        author="WrenchAI",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tags=["portfolio", "docusaurus", "website", "personal"],
        icon="ud83dudcbc",  # portfolio icon
        color="#25c2a0",  # Docusaurus default color
        featured=True
    )
    
    # Create execution config
    execution = ExecutionConfig(
        timeout_seconds=7200,  # 2 hours
        max_retries=3,
        retry_delay_seconds=10,
        logging_level="info"
    )
    
    # Create agent configs
    agents = {
        "DocusaurusAgent": AgentConfig(
            agent_type=AgentType.DOCUSAURUS,
            llm=LLMType.GPT4,
            tools=[
                ToolType.CORE,
                ToolType.CODE_GENERATION,
                ToolType.DOCUSAURUS_TOOL,
                ToolType.GITHUB
            ],
            temperature=0.7
        ),
        "ContentWriterAgent": AgentConfig(
            agent_type=AgentType.CONTENT_WRITER,
            llm=LLMType.GPT4,
            tools=[ToolType.CORE, ToolType.WEB_SEARCH],
            temperature=0.8
        )
    }
    
    # Create parameters
    parameters = [
        Parameter(
            name="title",
            type="string",
            description="The title of your portfolio website",
            default="My Portfolio",
            required=True
        ),
        Parameter(
            name="tagline",
            type="string",
            description="A short tagline that appears under the title",
            default="Software Developer & Designer",
            required=True
        ),
        Parameter(
            name="theme",
            type="string",
            description="The Docusaurus theme to use",
            default="classic",
            required=False,
            choices=["classic", "dark", "modern", "tech", "minimal"]
        ),
        Parameter(
            name="sections",
            type="list",
            description="Sections to include in your portfolio",
            default=["introduction", "skills", "projects", "experience"],
            required=True,
            choices=["introduction", "skills", "projects", "experience", "education", "contact", "blog"]
        ),
        Parameter(
            name="author_name",
            type="string",
            description="Your name",
            default="",
            required=True
        ),
        Parameter(
            name="github_repo",
            type="string",
            description="GitHub repository URL for deployment (optional)",
            default="",
            required=False
        ),
        Parameter(
            name="projects",
            type="list",
            description="List of projects to showcase",
            default=[],
            required=False
        )
    ]
    
    # Create steps
    steps = [
        PlaybookStep(
            step_id="initialize_project",
            type=StepType.STANDARD,
            description="Initialize the Docusaurus project",
            agent=AgentType.DOCUSAURUS,
            operation="init_docusaurus",
            parameters={
                "template": "portfolio"
            },
            next="generate_content"
        ),
        PlaybookStep(
            step_id="generate_content",
            type=StepType.STANDARD,
            description="Generate content for the portfolio",
            agent=AgentType.CONTENT_WRITER,
            operation="generate_content",
            parameters={
                "sections": ["introduction", "skills", "projects", "experience"]
            },
            next="customize_theme"
        ),
        PlaybookStep(
            step_id="customize_theme",
            type=StepType.STANDARD,
            description="Customize the Docusaurus theme",
            agent=AgentType.DOCUSAURUS,
            operation="customize_theme",
            parameters={
                "theme": "classic",
                "primary_color": "#25c2a0"
            },
            next="build_preview"
        ),
        PlaybookStep(
            step_id="build_preview",
            type=StepType.STANDARD,
            description="Build and preview the portfolio",
            agent=AgentType.DOCUSAURUS,
            operation="build_preview",
            parameters={
                "generate_screenshots": True
            },
            next="prepare_deployment"
        ),
        PlaybookStep(
            step_id="prepare_deployment",
            type=StepType.STANDARD,
            description="Prepare deployment options",
            agent=AgentType.DOCUSAURUS,
            operation="prepare_deployment",
            parameters={
                "platforms": ["github_pages", "vercel", "netlify"]
            }
        )
    ]
    
    # Create the full PlaybookConfig
    return PlaybookConfig(
        metadata=metadata,
        execution=execution,
        agents=agents,
        parameters=parameters,
        steps=steps,
        schema_version="1.0"
    )


def extract_parameters_for_ui(config: PlaybookConfig) -> List[Dict[str, Any]]:
    """
    Extract parameters from a playbook config in a format suitable for the UI.
    
    Args:
        config: The PlaybookConfig to extract parameters from
        
    Returns:
        List of parameter dictionaries with UI-friendly structure
    """
    ui_parameters = []
    
    for param in config.parameters:
        ui_param = {
            "id": param.name,
            "name": param.name.replace('_', ' ').title(),
            "description": param.description,
            "type": param.type,
            "default": param.default,
            "required": param.required,
        }
        
        # Add type-specific attributes
        if param.choices:
            ui_param["choices"] = param.choices
            
        if param.min_value is not None:
            ui_param["min_value"] = param.min_value
            
        if param.max_value is not None:
            ui_param["max_value"] = param.max_value
        
        ui_parameters.append(ui_param)
    
    return ui_parameters
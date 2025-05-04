# Playbook Configuration Models

## Overview

This package provides Pydantic models for configuring and executing playbooks in the WrenchAI Streamlit application. These models ensure type safety, validation, and proper structure for playbooks throughout the application.

## Key Components

### Core Models

- **PlaybookConfig**: The main configuration model for a playbook.
- **PlaybookMetadata**: Metadata about the playbook like name, description, and author.
- **ExecutionConfig**: Configuration for playbook execution like timeouts and retries.
- **AgentConfig**: Configuration for agents used in the playbook.
- **Parameter**: Model for configurable playbook parameters.
- **PlaybookStep**: Model for steps in a playbook.

### Enums

- **PlaybookType**: Types of playbooks (code_generation, documentation, etc.)
- **PlaybookCategory**: Categories for organizing playbooks
- **ToolType**: Available tools for agents
- **AgentType**: Available agent types
- **LLMType**: LLM models that can be used with agents
- **StepType**: Types of playbook steps (standard, work_in_parallel, etc.)
- **ExecutionState**: States of playbook execution (running, completed, etc.)

### Docusaurus-specific Models

- **DocusaurusConfig**: Configuration for Docusaurus site generation
- **ProjectItem**: Model for projects to include in a portfolio
- **DocusaurusPortfolioConfig**: Full configuration for a Docusaurus portfolio

## Usage Examples

### Creating a Basic Playbook

```python
from streamlit_app.models.playbook_config import (
    PlaybookConfig, PlaybookMetadata, PlaybookStep, AgentConfig,
    Parameter, PlaybookType, StepType, AgentType, LLMType, ToolType
)

# Create a basic playbook config
config = PlaybookConfig(
    metadata=PlaybookMetadata(
        name="Code Generator",
        description="Generate code in various languages",
        type=PlaybookType.CODE_GENERATION
    ),
    agents={
        "CodeGenerator": AgentConfig(
            agent_type=AgentType.CODE_GENERATOR,
            llm=LLMType.GPT4,
            tools=[ToolType.CODE_GENERATION]
        )
    },
    parameters=[
        Parameter(
            name="language",
            type="string",
            description="Programming language",
            default="python",
            choices=["python", "javascript", "typescript"]
        )
    ],
    steps=[
        PlaybookStep(
            step_id="generate_code",
            type=StepType.STANDARD,
            description="Generate code",
            agent=AgentType.CODE_GENERATOR,
            operation="generate_code",
            parameters={"language": "python"}
        )
    ]
)
```

### Creating a Docusaurus Portfolio Configuration

```python
from streamlit_app.models.playbook_config import DocusaurusPortfolioConfig

portfolio_config = DocusaurusPortfolioConfig(
    basic_info={
        "title": "John Doe's Portfolio",
        "tagline": "Full Stack Developer",
        "author_name": "John Doe",
        "author_email": "john@example.com",
        "github_repo": "https://github.com/johndoe/portfolio",
        "social_links": {
            "github": "johndoe",
            "linkedin": "johndoe"
        }
    },
    projects=[
        {
            "name": "Project 1",
            "description": "A sample project",
            "github_url": "https://github.com/johndoe/project1",
            "technologies": ["Python", "React"]
        }
    ],
    skills={
        "Languages": ["Python", "JavaScript"],
        "Frameworks": ["React", "Django"]
    }
)
```

### Loading and Saving Playbook Configurations

```python
from streamlit_app.models.playbook_utils import load_playbook_config, save_playbook_config

# Load a playbook from file
config, error = load_playbook_config("playbooks/code_generator.yaml")
if error:
    print(f"Error loading playbook: {error}")
else:
    # Modify the playbook
    config.metadata.name = "Updated Code Generator"
    
    # Save the playbook
    success, error = save_playbook_config(config, "playbooks/updated_code_generator.yaml")
    if not success:
        print(f"Error saving playbook: {error}")
```

### Creating a Default Docusaurus Playbook

```python
from streamlit_app.models.playbook_utils import create_docusaurus_playbook

# Create a default Docusaurus playbook
docusaurus_playbook = create_docusaurus_playbook()

# Customize the playbook
docusaurus_playbook.metadata.name = "My Custom Portfolio Generator"
```

## Utility Functions

The `playbook_utils.py` module provides several utility functions:

- `load_playbook_config`: Load a playbook configuration from a YAML or JSON file
- `save_playbook_config`: Save a playbook configuration to a file
- `convert_to_core_format`: Convert a PlaybookConfig to the core.playbook_schema format
- `convert_legacy_format`: Convert legacy playbook format to the new PlaybookConfig model
- `create_docusaurus_playbook`: Create a default Docusaurus portfolio playbook configuration
- `extract_parameters_for_ui`: Extract parameters from a playbook config in a format suitable for the UI

## Validation

All models include validation to ensure the playbook configuration is valid:

- Required fields are enforced
- Field types are validated
- Enum values are restricted to defined options
- Complex validation ensures steps reference valid agents
- URLs are validated for proper format

## Integration with Core Schema

These models are designed to work with the existing `core.playbook_schema` module. The `convert_to_core_format` function in `playbook_utils.py` can convert a `PlaybookConfig` to the format expected by the core schema.
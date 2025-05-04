"""Test script for playbook configuration models.

This script tests the creation and validation of playbook configuration models.
"""

import os
import sys
import json
import yaml
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

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
from streamlit_app.models.playbook_utils import (
    create_docusaurus_playbook,
    save_playbook_config,
    convert_to_core_format
)


def test_create_playbook():
    """Test creating a playbook configuration."""
    print("\n=== Creating a basic playbook configuration ===")
    
    # Create a basic playbook config
    config = PlaybookConfig(
        metadata=PlaybookMetadata(
            name="Test Playbook",
            description="A test playbook",
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
    
    # Print the config as JSON
    print(json.dumps(config.model_dump(exclude_none=True), indent=2))
    print("\nPlaybook created successfully!")
    return config


def test_docusaurus_playbook():
    """Test creating a Docusaurus portfolio playbook."""
    print("\n=== Creating a Docusaurus portfolio playbook ===")
    
    # Create a Docusaurus playbook
    config = create_docusaurus_playbook()
    
    # Print the config as YAML
    print(yaml.dump(config.model_dump(exclude_none=True), default_flow_style=False))
    print("\nDocusaurus playbook created successfully!")
    return config


def test_save_playbook(config, output_dir="./test_output"):
    """Test saving a playbook to file."""
    print("\n=== Saving playbook to file ===")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save as YAML
    yaml_path = os.path.join(output_dir, f"{config.metadata.name.lower().replace(' ', '_')}.yaml")
    success, error = save_playbook_config(config, yaml_path, format="yaml")
    if success:
        print(f"Saved YAML to {yaml_path}")
    else:
        print(f"Error saving YAML: {error}")
    
    # Save as JSON
    json_path = os.path.join(output_dir, f"{config.metadata.name.lower().replace(' ', '_')}.json")
    success, error = save_playbook_config(config, json_path, format="json")
    if success:
        print(f"Saved JSON to {json_path}")
    else:
        print(f"Error saving JSON: {error}")


def test_convert_to_core_format(config):
    """Test converting to core playbook format."""
    print("\n=== Converting to core playbook format ===")
    
    # Convert to core format
    core_format = convert_to_core_format(config)
    
    # Print as YAML
    print(yaml.dump(core_format, default_flow_style=False))
    print("\nConverted to core format successfully!")


def test_docusaurus_portfolio_config():
    """Test creating a Docusaurus portfolio configuration."""
    print("\n=== Creating Docusaurus portfolio configuration ===")
    
    # Create a portfolio config
    portfolio_config = DocusaurusPortfolioConfig(
        basic_info={
            "title": "John Doe's Portfolio",
            "tagline": "Full Stack Developer",
            "author_name": "John Doe",
            "author_email": "john@example.com",
            "github_repo": "https://github.com/johndoe/portfolio",
            "social_links": {
                "github": "johndoe",
                "linkedin": "johndoe",
                "twitter": "johndoe"
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
            "Languages": ["Python", "JavaScript", "TypeScript"],
            "Frameworks": ["React", "Django", "Express"],
            "Tools": ["Git", "Docker", "AWS"]
        },
        experience=[
            {
                "company": "Acme Inc",
                "title": "Senior Developer",
                "start_date": "2020-01",
                "end_date": "2022-01",
                "description": "Led development of key features"
            }
        ],
        education=[
            {
                "institution": "University of Example",
                "degree": "BS",
                "field": "Computer Science",
                "start_date": "2014-01",
                "end_date": "2018-01"
            }
        ]
    )
    
    # Print as JSON
    print(json.dumps(portfolio_config.model_dump(exclude_none=True), indent=2))
    print("\nPortfolio config created successfully!")


if __name__ == "__main__":
    # Run tests
    basic_config = test_create_playbook()
    docusaurus_config = test_docusaurus_playbook()
    test_save_playbook(docusaurus_config)
    test_convert_to_core_format(docusaurus_config)
    test_docusaurus_portfolio_config()
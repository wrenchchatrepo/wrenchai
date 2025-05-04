"""Pydantic Models for Playbook Configuration.

This module provides a comprehensive set of Pydantic models for defining and validating
playbook configurations in the WrenchAI Streamlit application.
"""

from typing import Dict, List, Union, Optional, Any, Literal, Set, TypeVar, Generic
from enum import Enum, auto
from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, validator, root_validator, ConfigDict

# Define enums for various playbook types and configurations
class PlaybookType(str, Enum):
    """Enum for different types of playbooks."""
    CODE_GENERATION = "code_generation"
    DOCUMENTATION = "documentation"
    ANALYSIS = "analysis"
    DEPLOYMENT = "deployment"
    PORTFOLIO = "portfolio"
    CUSTOM = "custom"


class PlaybookCategory(str, Enum):
    """Enum for playbook categories."""
    ALL = "all"
    CODE = "code"
    DOCS = "docs"
    ANALYSIS = "analysis"
    DEPLOYMENT = "deployment"
    PORTFOLIO = "portfolio"


class ToolType(str, Enum):
    """Enum for different types of tools that can be used in playbooks."""
    CORE = "core_tools"
    WEB_SEARCH = "web_search"
    CODE_GENERATION = "code_generation"
    GITHUB = "github_tool"
    DOCUSAURUS = "docusaurus_tool"
    FILE = "file_tool"
    DATABASE = "database_tool"


class AgentType(str, Enum):
    """Enum for different types of agents that can be used in playbooks."""
    DEFAULT = "DefaultAgent"
    CODE_GENERATOR = "CodeGeneratorAgent"
    CONTENT_WRITER = "ContentWriterAgent"
    DOCUSAURUS = "DocusaurusAgent"
    RESEARCH = "ResearchAgent"
    SYSTEM_DESIGN = "SystemDesignAgent"


class LLMType(str, Enum):
    """Enum for different LLM models that can be used with agents."""
    GPT4 = "gpt-4"
    GPT35 = "gpt-3.5-turbo"
    CLAUDE2 = "claude-2"


class ExecutionState(str, Enum):
    """Enum for playbook execution states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    VALIDATING = "validating"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class StepType(str, Enum):
    """Enum for different types of playbook steps."""
    STANDARD = "standard"
    WORK_IN_PARALLEL = "work_in_parallel"
    SELF_FEEDBACK_LOOP = "self_feedback_loop"
    PARTNER_FEEDBACK_LOOP = "partner_feedback_loop"
    PROCESS = "process"
    VERSUS = "versus"
    HANDOFF = "handoff"


# Base models
class BaseConfig(BaseModel):
    """Base model for configuration with utility methods."""
    model_config = ConfigDict(populate_by_name=True)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        return self.model_dump(exclude_none=True)


class PlaybookMetadata(BaseConfig):
    """Metadata for a playbook."""
    name: str
    description: str
    type: PlaybookType = Field(default=PlaybookType.CUSTOM)
    category: PlaybookCategory = Field(default=PlaybookCategory.ALL)
    version: str = Field(default="1.0.0")
    author: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    icon: Optional[str] = None
    color: Optional[str] = None
    featured: bool = Field(default=False)
    
    @validator('updated_at', always=True)
    def set_updated_time(cls, v, values):
        """Set updated_at to current time if not provided."""
        return v or datetime.now()


class ExecutionConfig(BaseConfig):
    """Configuration for playbook execution."""
    timeout_seconds: int = Field(default=3600)  # Default 1 hour timeout
    max_retries: int = Field(default=3)
    retry_delay_seconds: int = Field(default=5)
    parallel_executions: bool = Field(default=False)
    execution_environment: str = Field(default="default")
    memory_allocation_mb: Optional[int] = None
    logging_level: str = Field(default="info")
    
    @validator('timeout_seconds')
    def validate_timeout(cls, v):
        """Validate timeout is within reasonable range."""
        if v < 1 or v > 86400:  # Between 1 second and 24 hours
            raise ValueError("Timeout must be between 1 second and 24 hours")
        return v


class AgentConfig(BaseConfig):
    """Configuration for a specific agent in a playbook."""
    agent_type: AgentType
    llm: LLMType
    tools: List[ToolType] = Field(default_factory=list)
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = None
    system_message: Optional[str] = None
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature is within valid range."""
        if v < 0 or v > 2:
            raise ValueError("Temperature must be between 0 and 2")
        return v


class Parameter(BaseConfig):
    """Model for a parameter that can be configured in a playbook."""
    name: str
    type: str  # string, integer, boolean, list, etc.
    description: str
    default: Any = None
    required: bool = Field(default=False)
    choices: Optional[List[Any]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    @validator('type')
    def validate_type(cls, v):
        """Validate parameter type."""
        valid_types = ["string", "integer", "float", "boolean", "list", "object"]
        if v not in valid_types:
            raise ValueError(f"Type must be one of {valid_types}")
        return v


class StepParameter(BaseConfig):
    """Parameter values for a specific step."""
    parameter_id: str
    value: Any


class StepMetadata(BaseConfig):
    """Metadata for a playbook step."""
    name: str
    description: str
    tools: List[ToolType] = Field(default_factory=list)
    agents: List[AgentType] = Field(default_factory=list)
    agent_llms: Dict[str, LLMType] = Field(default_factory=dict)
    sections: Optional[List[str]] = None


class Operation(BaseConfig):
    """Operation definition for steps."""
    role: str
    name: str


class PlaybookStep(BaseConfig):
    """Model for a step in a playbook."""
    step_id: str
    type: StepType
    description: str
    next: Optional[str] = None
    
    # Fields for standard steps
    agent: Optional[AgentType] = None
    operation: Optional[str] = None
    tools: Optional[List[ToolType]] = None
    parameters: Optional[Dict[str, Any]] = None
    
    # Fields for metadata steps
    metadata: Optional[StepMetadata] = None
    
    # Fields for partner_feedback_loop
    agents: Optional[Dict[str, str]] = None  # Maps roles to agent names
    operations: Optional[List[Operation]] = None
    iterations: Optional[int] = None
    
    @validator('agent')
    def validate_agent_for_standard(cls, v, values):
        """Validate agent is present for standard steps."""
        if values.get('type') == StepType.STANDARD and not v:
            raise ValueError("agent is required for standard steps")
        return v


class PlaybookConfig(BaseConfig):
    """Main configuration model for a playbook."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    metadata: PlaybookMetadata
    execution: ExecutionConfig = Field(default_factory=ExecutionConfig)
    agents: Dict[str, AgentConfig] = Field(default_factory=dict)
    parameters: List[Parameter] = Field(default_factory=list)
    steps: List[PlaybookStep]
    schema_version: str = Field(default="1.0")
    
    @root_validator
    def validate_steps_and_agents(cls, values):
        """Validate that all agent types referenced in steps are defined in agents."""
        steps = values.get('steps', [])
        agents_dict = values.get('agents', {})
        
        # No steps, nothing to validate
        if not steps:
            return values
        
        # Collect all agent types used in steps
        used_agents = set()
        for step in steps:
            if step.type == StepType.STANDARD and step.agent:
                used_agents.add(step.agent.value)
        
        # Check that all used agents are defined
        for agent in used_agents:
            if agent not in agents_dict:
                raise ValueError(f"Agent '{agent}' is used in steps but not defined in agents configuration")
        
        return values


class UserPlaybookParameter(BaseConfig):
    """User-provided value for a playbook parameter."""
    parameter_id: str
    value: Any


class PlaybookExecutionConfig(BaseConfig):
    """Configuration for a specific execution of a playbook."""
    playbook_id: str
    execution_id: str = Field(default_factory=lambda: str(uuid4()))
    parameters: List[UserPlaybookParameter] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    state: ExecutionState = Field(default=ExecutionState.IDLE)
    user_id: Optional[str] = None
    notes: Optional[str] = None


class ExecutionResult(BaseConfig):
    """Result of a playbook execution."""
    execution_id: str
    playbook_id: str
    state: ExecutionState
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    success: bool = Field(default=False)
    error: Optional[str] = None
    outputs: Dict[str, Any] = Field(default_factory=dict)
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    
    @validator('duration_seconds', always=True)
    def calculate_duration(cls, v, values):
        """Calculate duration if start_time and end_time are available."""
        start = values.get('start_time')
        end = values.get('end_time')
        
        if start and end:
            return (end - start).total_seconds()
        return v


# Docusaurus-specific models
class DocusaurusTheme(str, Enum):
    """Enum for Docusaurus themes."""
    CLASSIC = "classic"
    DARK = "dark"
    MODERN = "modern"
    TECH = "tech"
    MINIMAL = "minimal"


class DocusaurusSection(str, Enum):
    """Enum for Docusaurus portfolio sections."""
    INTRODUCTION = "introduction"
    SKILLS = "skills"
    PROJECTS = "projects"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CONTACT = "contact"
    BLOG = "blog"
    CUSTOM = "custom"


class DeploymentPlatform(str, Enum):
    """Enum for deployment platforms."""
    GITHUB_PAGES = "github_pages"
    VERCEL = "vercel"
    NETLIFY = "netlify"
    CUSTOM = "custom"


class DocusaurusConfig(BaseConfig):
    """Configuration for Docusaurus portfolio generation."""
    title: str
    tagline: str
    theme: DocusaurusTheme = Field(default=DocusaurusTheme.CLASSIC)
    sections: List[DocusaurusSection] = Field(
        default_factory=lambda: [
            DocusaurusSection.INTRODUCTION,
            DocusaurusSection.SKILLS,
            DocusaurusSection.PROJECTS,
            DocusaurusSection.EXPERIENCE
        ]
    )
    github_repo: Optional[str] = None
    base_url: str = Field(default="/")
    color_primary: str = Field(default="#2e8555")
    color_secondary: str = Field(default="#19216C")
    enable_dark_mode: bool = Field(default=True)
    author_name: str
    author_image: Optional[str] = None
    author_email: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)
    # Example format: {"github": "username", "linkedin": "username"}
    
    # Projects section configuration
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    # Example project format: {"name": "Project Name", "description": "...", "github": "url", "demo": "url", "image": "url"}
    
    # Deployment settings
    deployment_platform: Optional[DeploymentPlatform] = None
    deployment_credentials: Optional[Dict[str, str]] = None


class ProjectItem(BaseConfig):
    """Model for a project to include in a portfolio."""
    name: str
    description: str
    github_url: Optional[str] = None
    demo_url: Optional[str] = None
    image_url: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    featured: bool = Field(default=False)
    
    @validator('github_url', 'demo_url', 'image_url')
    def validate_urls(cls, v):
        """Validate URLs if they are provided."""
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")
        return v


class DocusaurusPortfolioConfig(BaseConfig):
    """Full configuration for Docusaurus portfolio generation playbook."""
    basic_info: DocusaurusConfig
    projects: List[ProjectItem] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict)
    # Example: {"Languages": ["Python", "JavaScript"], "Frameworks": ["React", "Django"]}
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    # Example: [{"company": "Company Name", "title": "Job Title", "start_date": "2020-01", "end_date": "2022-01", "description": "..."}]
    education: List[Dict[str, Any]] = Field(default_factory=list)
    # Example: [{"institution": "University Name", "degree": "Degree Name", "field": "Field of Study", "start_date": "2016-01", "end_date": "2020-01"}]
    custom_sections: List[Dict[str, Any]] = Field(default_factory=list)
    # Example: [{"title": "Section Title", "content": "Markdown content"}]
    
    # Build and deployment settings
    build_command: Optional[str] = None
    generate_screenshots: bool = Field(default=True)
    seo_optimization: bool = Field(default=True)
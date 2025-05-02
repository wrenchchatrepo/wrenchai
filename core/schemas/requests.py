"""
Standardized request schemas for WrenchAI API.

This module provides consistent input validation schemas for all API endpoints,
ensuring proper data validation and helpful error messages.
"""

from typing import Dict, List, Optional, Any, Union
<<<<<<< HEAD
# Using Pydantic v2 validators according to Pydantic AI guidelines
# Reference: https://ai.pydantic.dev/agents/
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic import validator  # For backward compatibility
=======
from pydantic import BaseModel, Field, validator, root_validator
>>>>>>> update-mvp-implementation-plan
from enum import Enum
from datetime import datetime
from uuid import UUID, uuid4

class AgentType(str, Enum):
    """Types of agents available in the system."""
    SUPER = "super"
    INSPECTOR = "inspector"
    JOURNEY = "journey"
    CODIFIER = "codifier"
    UX_DESIGNER = "ux_designer"
    TEST_ENGINEER = "test_engineer"
    COMPTROLLER = "comptroller"
    UAT = "uat"
    CUSTOM = "custom"

class ToolCategory(str, Enum):
    """Categories of tools available in the system."""
    WEB = "web"
    CODE = "code"
    DATA = "data"
    SYSTEM = "system"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    COMMUNICATION = "communication"
    CUSTOM = "custom"

class PlaybookStep(BaseModel):
    """Model for a playbook step."""
    name: str = Field(..., description="Step name")
    action: str = Field(..., description="Step action")
    params: Dict[str, Any] = Field(default_factory=dict, description="Step parameters")
    condition: Optional[str] = Field(None, description="Optional condition for execution")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern 
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('name')
=======
    @validator('name')
>>>>>>> update-mvp-implementation-plan
    def validate_name(cls, v):
        """Validate step name."""
        if len(v.strip()) == 0:
            raise ValueError("Step name cannot be empty")
        return v
    
    @validator('action')
    def validate_action(cls, v):
        """Validate step action."""
        if len(v.strip()) == 0:
            raise ValueError("Step action cannot be empty")
        return v

class PlaybookAgent(BaseModel):
    """Model for a playbook agent."""
    type: AgentType = Field(..., description="Agent type")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('type')
=======
    @validator('type')
>>>>>>> update-mvp-implementation-plan
    def validate_agent_type(cls, v):
        """Validate agent type."""
        if v == AgentType.CUSTOM and 'implementation' not in cls.config:
            raise ValueError("Custom agent type requires 'implementation' in config")
        return v

class Project(BaseModel):
    """Project configuration for playbook execution."""
    name: str = Field(..., description="Name of the project")
    description: Optional[str] = Field(None, description="Project description")
    repository_url: Optional[str] = Field(None, description="Git repository URL")
    branch: str = Field("main", description="Git branch to use")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('name')
=======
    @validator('name')
>>>>>>> update-mvp-implementation-plan
    def validate_name(cls, v):
        """Validate project name."""
        if len(v.strip()) == 0:
            raise ValueError("Project name cannot be empty")
        return v
    
    @validator('repository_url')
    def validate_repository_url(cls, v):
        """Validate repository URL if present."""
        if v is not None:
            if not (v.startswith('http://') or v.startswith('https://') or v.startswith('git@')):
                raise ValueError("Repository URL must be a valid HTTP/HTTPS/SSH URL")
        return v

class PlaybookExecuteRequest(BaseModel):
    """Request model for playbook execution."""
    playbook_name: str = Field(..., description="Name of the playbook to execute")
    project: Project = Field(..., description="Project configuration")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Playbook parameters")
    agents: List[PlaybookAgent] = Field(default_factory=list, description="Agents for execution")
    tools: List[str] = Field(default_factory=list, description="Tools to use during execution")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('playbook_name')
=======
    @validator('playbook_name')
>>>>>>> update-mvp-implementation-plan
    def validate_playbook_name(cls, v):
        """Validate playbook name."""
        if len(v.strip()) == 0:
            raise ValueError("Playbook name cannot be empty")
        return v
    
<<<<<<< HEAD
    # Using field_validator instead of validator according to Pydantic AI guidelines
    # Reference: https://ai.pydantic.dev/agents/
    @field_validator('agents')
=======
    @validator('agents')
>>>>>>> update-mvp-implementation-plan
    def validate_agents(cls, v):
        """Validate agents list."""
        if len(v) == 0:
            return [PlaybookAgent(type=AgentType.SUPER)]  # Default to super agent
        return v
    
<<<<<<< HEAD
    # Using model_validator according to Pydantic AI's model-level validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @model_validator(mode='after')
    def validate_tools_and_agents(self) -> 'PlaybookExecuteRequest':
        """Validate tools and agents compatibility."""
        if hasattr(self, 'tools') and self.tools and hasattr(self, 'agents'):
            # Check if all tools are supported by at least one agent
            # This is a placeholder for more complex validation logic
            pass
        return self
=======
    @root_validator
    def validate_tools_and_agents(cls, values):
        """Validate tools and agents compatibility."""
        if 'tools' in values and values['tools'] and 'agents' in values:
            # Check if all tools are supported by at least one agent
            # This is a placeholder for more complex validation logic
            pass
        return values
>>>>>>> update-mvp-implementation-plan

class TaskCreateRequest(BaseModel):
    """Request model for task creation."""
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Task description")
    priority: str = Field("medium", description="Task priority")
    due_date: Optional[datetime] = Field(None, description="Task due date")
    assignee: Optional[str] = Field(None, description="Task assignee")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('title')
=======
    @validator('title')
>>>>>>> update-mvp-implementation-plan
    def validate_title(cls, v):
        """Validate task title."""
        if len(v.strip()) == 0:
            raise ValueError("Task title cannot be empty")
        return v
    
    @validator('priority')
    def validate_priority(cls, v):
        """Validate task priority."""
        valid_priorities = ["low", "medium", "high", "critical"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
        return v.lower()

class AgentCreateRequest(BaseModel):
    """Request model for agent creation."""
    name: str = Field(..., description="Agent name")
    type: AgentType = Field(..., description="Agent type")
    description: Optional[str] = Field(None, description="Agent description")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    tools: List[str] = Field(default_factory=list, description="Tools for the agent to use")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('name')
=======
    @validator('name')
>>>>>>> update-mvp-implementation-plan
    def validate_name(cls, v):
        """Validate agent name."""
        if len(v.strip()) == 0:
            raise ValueError("Agent name cannot be empty")
        return v
    
    @validator('type')
    def validate_type(cls, v, values):
        """Validate agent type and configs."""
        if v == AgentType.CUSTOM and ('config' not in values or 'implementation' not in values['config']):
            raise ValueError("Custom agent type requires 'implementation' in config")
        return v

class ToolCreateRequest(BaseModel):
    """Request model for tool creation."""
    name: str = Field(..., description="Tool name")
    category: ToolCategory = Field(..., description="Tool category")
    description: str = Field(..., description="Tool description")
    implementation: str = Field(..., description="Tool implementation path")
    config: Dict[str, Any] = Field(default_factory=dict, description="Tool configuration")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('name')
=======
    @validator('name')
>>>>>>> update-mvp-implementation-plan
    def validate_name(cls, v):
        """Validate tool name."""
        if len(v.strip()) == 0:
            raise ValueError("Tool name cannot be empty")
        return v
    
    @validator('implementation')
    def validate_implementation(cls, v):
        """Validate implementation path."""
        if not v.strip():
            raise ValueError("Implementation path cannot be empty")
        return v

class ToolExecuteRequest(BaseModel):
    """Request model for tool execution."""
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool execution parameters")
    context: Optional[Dict[str, Any]] = Field(None, description="Execution context")
    timeout: Optional[int] = Field(None, description="Execution timeout in seconds")
    
<<<<<<< HEAD
    # Using field_validator according to Pydantic AI's field validation pattern
    # Reference: https://ai.pydantic.dev/agents/#type-safe-by-design
    @field_validator('tool_name')
=======
    @validator('tool_name')
>>>>>>> update-mvp-implementation-plan
    def validate_tool_name(cls, v):
        """Validate tool name."""
        if len(v.strip()) == 0:
            raise ValueError("Tool name cannot be empty")
        return v
    
    @validator('timeout')
    def validate_timeout(cls, v):
        """Validate timeout if provided."""
        if v is not None and v <= 0:
            raise ValueError("Timeout must be a positive integer")
        return v

# Export key types
__all__ = [
    'AgentType',
    'ToolCategory',
    'PlaybookStep',
    'PlaybookAgent',
    'Project',
    'PlaybookExecuteRequest',
    'TaskCreateRequest',
    'AgentCreateRequest',
    'ToolCreateRequest',
    'ToolExecuteRequest'
]
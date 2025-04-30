"""Agent schemas with AI-powered validation and capabilities."""
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID

from pydantic import Field, ConfigDict
from pydantic_ai import AIField, GraphField
from pydantic_ai.validators import SemanticValidator, ContentValidator
from pydantic_ai.types import AIStr, AIDict

from app.schemas.base import BaseAISchema, BaseResponse

class AgentConfig(BaseAISchema):
    """Configuration schema for agents with AI validation."""
    capabilities: List[str] = AIField(
        description="List of agent capabilities",
        validate_semantic=True,
        validate_relationships=True
    )
    llm_provider: str = AIField(
        description="LLM provider for the agent",
        validate_semantic=True,
        allowed_values=["claude", "gpt4", "gemini"]
    )
    parameters: AIDict = AIField(
        description="Agent-specific parameters",
        validate_schema=True
    )

class AgentBase(BaseAISchema):
    """Base schema for agent with AI-powered validation."""
    role: AIStr = AIField(
        description="Role of the agent",
        validate_semantic=True,
        min_length=3
    )
    config: AgentConfig
    is_active: bool = True
    
    # AI-powered content validation
    content_validator = ContentValidator(
        check_pii=True,
        check_sensitive_data=True,
        check_content_safety=True
    )
    
    # Graph-based relationship validation
    relationships = GraphField(
        validate_dependencies=True,
        validate_circular_refs=True
    )

class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    owner_id: UUID = AIField(
        description="ID of the agent owner",
        validate_relationships=True
    )

class AgentUpdate(BaseAISchema):
    """Schema for updating an agent."""
    role: Optional[AIStr] = AIField(
        description="Updated role of the agent",
        validate_semantic=True,
        min_length=3
    )
    config: Optional[AgentConfig] = None
    is_active: Optional[bool] = None

class Agent(AgentBase):
    """Complete agent schema with all fields."""
    id: UUID
    owner_id: UUID
    created_at: datetime
    updated_at: datetime
    
    # AI-powered relationship tracking
    tasks: List["Task"] = GraphField(
        description="Tasks assigned to the agent",
        validate_relationships=True,
        track_dependencies=True
    )
    
    # Metadata with AI validation
    metadata: Dict[str, AIStr] = AIField(
        description="Additional metadata",
        validate_schema=True,
        validate_content=True
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "role": "code_reviewer",
                "config": {
                    "capabilities": ["code_review", "quality_assurance"],
                    "llm_provider": "claude",
                    "parameters": {
                        "review_depth": "detailed",
                        "focus_areas": ["security", "performance"]
                    }
                },
                "is_active": True,
                "owner_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-03-21T12:00:00",
                "updated_at": "2024-03-21T12:00:00",
                "metadata": {
                    "version": "1.0",
                    "specialization": "python_backend"
                }
            }
        }
    )

class AgentResponse(BaseResponse[Agent]):
    """Response schema for agent operations."""
    pass

# Circular import resolution
from .task import Task  # noqa
Agent.model_rebuild()  # Update forward refs

# Task schemas
class TaskBase(BaseSchema):
    """Base schema for task data."""
    task_type: str = Field(..., description="Type of task (e.g., 'code_analysis', 'optimization')")
    input_data: Dict[str, Any] = Field(..., description="Input parameters and data for the task")
    config: Dict[str, Any] = Field(default_factory=dict, description="Task-specific configuration")

class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    agent_id: UUID = Field(..., description="ID of the agent assigned to this task")

class TaskUpdate(BaseSchema):
    """Schema for updating a task."""
    status: str | None = Field(None, description="Current task status")
    progress: float | None = Field(None, ge=0.0, le=100.0, description="Progress percentage (0-100)")
    message: str | None = Field(None, description="Current status message or description")
    result: Dict[str, Any] | None = Field(None, description="Task execution results")
    error: str | None = Field(None, description="Error message if task failed")

class TaskResponse(TaskBase, BaseAPISchema):
    """Schema for task information in API responses."""
    agent_id: UUID
    status: str = Field("pending", description="Current task status")
    progress: float = Field(0.0, ge=0.0, le=100.0, description="Progress percentage (0-100)")
    message: str | None = None
    result: Dict[str, Any] | None = None
    error: str | None = None

class TaskWithExecutions(TaskResponse):
    """Schema for task information including execution history."""
    executions: List["TaskExecutionResponse"]

# Task execution schemas
class TaskExecutionBase(BaseSchema):
    """Base schema for task execution data."""
    start_time: datetime
    end_time: datetime | None = None
    status: str = Field("running", description="Execution status")
    metrics: Dict[str, Any] | None = Field(None, description="Performance metrics and statistics")
    logs: str | None = Field(None, description="Execution logs and output")

class TaskExecutionCreate(TaskExecutionBase):
    """Schema for creating a new task execution."""
    task_id: UUID = Field(..., description="ID of the associated task")

class TaskExecutionUpdate(BaseSchema):
    """Schema for updating a task execution."""
    end_time: datetime | None = None
    status: str | None = None
    metrics: Dict[str, Any] | None = None
    logs: str | None = None

class TaskExecutionResponse(TaskExecutionBase, BaseAPISchema):
    """Schema for task execution information in API responses."""
    task_id: UUID

# Update forward references
AgentWithTasks.model_rebuild()
TaskWithExecutions.model_rebuild() 
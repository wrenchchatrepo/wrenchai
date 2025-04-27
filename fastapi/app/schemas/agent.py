"""Agent and task schemas for request/response handling."""
from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseAPISchema, BaseSchema

class AgentBase(BaseSchema):
    """Base schema for agent data."""
    role: str = Field(..., description="Agent's role/type (e.g., 'inspector', 'journey', 'dba')")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific configuration")
    is_active: bool = Field(True, description="Whether the agent is currently active")

    @field_validator("role")
    def validate_role(cls, v: str) -> str:
        """Validate agent role."""
        allowed_roles = {
            "inspector", "journey", "dba", "test_engineer",
            "devops", "infosec", "ux_designer", "paralegal",
            "codifier", "data_scientist", "gcp_architect",
            "web_researcher"
        }
        if v not in allowed_roles:
            raise ValueError(f"Invalid role. Must be one of: {', '.join(sorted(allowed_roles))}")
        return v

class AgentCreate(AgentBase):
    """Schema for creating a new agent."""
    owner_id: UUID = Field(..., description="ID of the user who owns this agent")

class AgentUpdate(BaseSchema):
    """Schema for updating an agent."""
    role: str | None = None
    config: Dict[str, Any] | None = None
    is_active: bool | None = None

class AgentResponse(AgentBase, BaseAPISchema):
    """Schema for agent information in API responses."""
    owner_id: UUID

class AgentWithTasks(AgentResponse):
    """Schema for agent information including assigned tasks."""
    tasks: List["TaskResponse"]

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
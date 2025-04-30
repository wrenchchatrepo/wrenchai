"""Task schemas with AI-powered validation and capabilities."""
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import Field, ConfigDict
from pydantic_ai import AIField, GraphField
from pydantic_ai.validators import SemanticValidator, ContentValidator
from pydantic_ai.types import AIStr, AIDict, AIFloat

from .base import BaseAISchema, BaseResponse

class TaskInput(BaseAISchema):
    """Schema for task input data with AI validation."""
    content: AIStr = AIField(
        description="Task content or description",
        validate_semantic=True,
        validate_content=True
    )
    parameters: AIDict = AIField(
        description="Task-specific parameters",
        validate_schema=True
    )
    context: Optional[Dict[str, Any]] = AIField(
        description="Additional context for the task",
        validate_schema=True
    )

class TaskBase(BaseAISchema):
    """Base schema for tasks with AI-powered validation."""
    task_type: AIStr = AIField(
        description="Type of task",
        validate_semantic=True,
        allowed_values=[
            "code_review", "documentation", "testing",
            "deployment", "security_audit", "optimization"
        ]
    )
    input_data: TaskInput
    config: AIDict = AIField(
        description="Task configuration",
        validate_schema=True
    )
    status: AIStr = AIField(
        description="Current task status",
        validate_semantic=True,
        allowed_values=[
            "pending", "in_progress", "completed",
            "failed", "cancelled"
        ],
        default="pending"
    )
    progress: AIFloat = AIField(
        description="Task progress percentage",
        ge=0.0,
        le=100.0,
        default=0.0
    )
    
    # AI-powered content validation
    content_validator = ContentValidator(
        check_pii=True,
        check_sensitive_data=True,
        check_content_safety=True
    )
    
    # Graph-based validation for task dependencies
    dependencies = GraphField(
        validate_dependencies=True,
        validate_circular_refs=True,
        track_changes=True
    )

class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    agent_id: UUID = AIField(
        description="ID of the agent assigned to the task",
        validate_relationships=True
    )

class TaskUpdate(BaseAISchema):
    """Schema for updating a task."""
    status: Optional[AIStr] = AIField(
        description="Updated task status",
        validate_semantic=True,
        allowed_values=[
            "pending", "in_progress", "completed",
            "failed", "cancelled"
        ]
    )
    progress: Optional[AIFloat] = AIField(
        description="Updated progress percentage",
        ge=0.0,
        le=100.0
    )
    message: Optional[AIStr] = AIField(
        description="Status message or update",
        validate_semantic=True,
        validate_content=True
    )
    result: Optional[AIDict] = AIField(
        description="Task result data",
        validate_schema=True
    )
    error: Optional[AIStr] = AIField(
        description="Error message if task failed",
        validate_semantic=True
    )

class Task(TaskBase):
    """Complete task schema with all fields."""
    id: UUID
    agent_id: UUID
    message: Optional[AIStr] = AIField(
        description="Status message or update",
        validate_semantic=True
    )
    result: Optional[AIDict] = AIField(
        description="Task result data",
        validate_schema=True
    )
    error: Optional[AIStr] = AIField(
        description="Error message if task failed",
        validate_semantic=True
    )
    created_at: datetime
    updated_at: datetime
    
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
                "task_type": "code_review",
                "input_data": {
                    "content": "Review pull request #123",
                    "parameters": {
                        "repository": "main",
                        "pr_number": 123
                    },
                    "context": {
                        "branch": "feature/new-api"
                    }
                },
                "config": {
                    "review_depth": "detailed",
                    "focus_areas": ["security", "performance"]
                },
                "status": "in_progress",
                "progress": 45.5,
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Reviewing code changes",
                "created_at": "2024-03-21T12:00:00",
                "updated_at": "2024-03-21T12:30:00",
                "metadata": {
                    "priority": "high",
                    "estimated_time": "2h"
                }
            }
        }
    )

class TaskResponse(BaseResponse[Task]):
    """Response schema for task operations."""
    pass 
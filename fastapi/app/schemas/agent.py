from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field

class AgentBase(BaseModel):
    """Base agent schema."""
    role: str = Field(..., description="Agent role/type")
    config: Dict = Field(default_factory=dict, description="Agent configuration")
    is_active: bool = Field(True, description="Whether agent is active")

class AgentCreate(AgentBase):
    """Schema for creating an agent."""
    pass

class AgentUpdate(BaseModel):
    """Schema for updating an agent."""
    role: Optional[str] = Field(None, description="Agent role/type")
    config: Optional[Dict] = Field(None, description="Agent configuration")
    is_active: Optional[bool] = Field(None, description="Whether agent is active")

class AgentResponse(AgentBase):
    """Schema for agent response."""
    id: str = Field(..., description="Agent ID")
    owner_id: str = Field(..., description="Owner user ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True

class TaskRequest(BaseModel):
    """Schema for task execution request."""
    task_id: str = Field(..., description="Task ID")
    task_type: str = Field(..., description="Type of task to execute")
    input_data: Dict = Field(..., description="Input data for task")
    config: Optional[Dict] = Field(default_factory=dict, description="Task configuration")

class TaskStatus(BaseModel):
    """Schema for task status."""
    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status")
    progress: float = Field(0.0, description="Task progress (0-100)")
    message: Optional[str] = Field(None, description="Status message")
    result: Optional[Dict] = Field(None, description="Task result")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last status update timestamp")

    class Config:
        from_attributes = True 
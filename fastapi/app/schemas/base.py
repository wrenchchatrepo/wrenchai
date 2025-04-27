"""Base schemas for common model attributes."""
from datetime import datetime
from typing import TypeVar, Generic
from uuid import UUID

from pydantic import BaseModel, ConfigDict

ModelType = TypeVar("ModelType")

class BaseSchema(BaseModel):
    """Base schema with common configuration."""
    model_config = ConfigDict(from_attributes=True)

class BaseAPISchema(BaseSchema):
    """Base schema for API responses with common fields."""
    id: UUID
    created_at: datetime
    updated_at: datetime

class BaseResponse(BaseSchema, Generic[ModelType]):
    """Standard API response format."""
    success: bool
    message: str
    data: ModelType | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None
            }
        }
    ) 
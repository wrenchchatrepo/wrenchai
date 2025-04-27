"""User schemas for request/response handling."""
from typing import List
from pydantic import BaseModel, EmailStr, Field

from app.schemas.base import BaseAPISchema, BaseSchema

class UserBase(BaseSchema):
    """Base schema for user data."""
    email: EmailStr = Field(..., description="User's email address")
    full_name: str | None = Field(None, description="User's full name")
    is_active: bool = Field(True, description="Whether the user account is active")
    is_superuser: bool = Field(False, description="Whether the user has superuser privileges")

class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(
        ...,
        min_length=8,
        description="User's password (min 8 characters)"
    )

class UserUpdate(BaseSchema):
    """Schema for updating a user."""
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(None, min_length=8)
    is_active: bool | None = None
    is_superuser: bool | None = None

class UserInDB(UserBase, BaseAPISchema):
    """Schema for user information stored in DB."""
    hashed_password: str

class UserResponse(UserBase, BaseAPISchema):
    """Schema for user information in API responses."""
    pass

class UserWithAgents(UserResponse):
    """Schema for user information including owned agents."""
    from app.schemas.agent import AgentResponse  # Avoid circular import
    agents: List[AgentResponse] 
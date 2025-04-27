from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

class UserBase(BaseModel):
    """Base user schema.
    
    Attributes:
        email: User email
        full_name: User's full name
        is_active: Whether user is active
        is_superuser: Whether user is superuser
    """
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False

class UserCreate(UserBase):
    """User creation schema.
    
    Attributes:
        email: User email (required)
        password: User password
    """
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserUpdate(UserBase):
    """User update schema.
    
    Attributes:
        password: Optional new password
    """
    password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    """User response schema.
    
    Attributes:
        id: User ID
        email: User email
        created_at: User creation timestamp
        updated_at: User last update timestamp
    """
    id: int
    email: EmailStr
    created_at: datetime
    updated_at: datetime
    
    class Config:
        """Pydantic config."""
        from_attributes = True 
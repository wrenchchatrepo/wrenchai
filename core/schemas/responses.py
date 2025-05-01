"""
Standardized response schemas for WrenchAI API.

This module provides a consistent response format for all API endpoints,
ensuring predictable and well-documented responses for consumers.
"""

from typing import Generic, TypeVar, Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, create_model, validator
from datetime import datetime

# Type variable for response data
T = TypeVar('T')

class ErrorDetails(BaseModel):
    """Detailed error information."""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    trace_id: Optional[str] = Field(None, description="Trace ID for error tracking")
    path: Optional[str] = Field(None, description="Path where the error occurred")

class ResponseMetadata(BaseModel):
    """Metadata for API responses."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field("1.0", description="API version")
    trace_id: Optional[str] = Field(None, description="Trace ID for request tracking")
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    server_id: Optional[str] = Field(None, description="Server identifier")
    
    @validator('timestamp', pre=True)
    def ensure_utc(cls, v):
        """Ensure timestamp is in UTC."""
        if isinstance(v, datetime):
            return v.replace(microsecond=0)
        return v

class APIResponse(Generic[T], BaseModel):
    """Standard API response model."""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable response message")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ErrorDetails] = Field(None, description="Error details, if applicable")
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata, description="Response metadata")
    
    @validator('error', always=True)
    def validate_error_with_success(cls, v, values):
        """Validate that error details are present only for failed operations."""
        if 'success' in values:
            if values['success'] and v is not None:
                raise ValueError("Error details should not be present for successful operations")
            if not values['success'] and v is None:
                raise ValueError("Error details must be present for failed operations")
        return v

class PaginatedResponseMetadata(BaseModel):
    """Metadata for paginated responses."""
    total_count: int = Field(..., description="Total number of items")
    page_size: int = Field(..., description="Number of items per page")
    page: int = Field(..., description="Current page number")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there is a next page")
    has_prev: bool = Field(..., description="Whether there is a previous page")

class PaginatedResponse(Generic[T], APIResponse[List[T]]):
    """Paginated API response model."""
    pagination: PaginatedResponseMetadata = Field(..., description="Pagination metadata")

def create_response(
    success: bool, 
    message: str, 
    data: Optional[Any] = None, 
    error: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized API response.
    
    Args:
        success: Whether the operation was successful
        message: Human-readable response message
        data: Response data
        error: Error details, if applicable
        metadata: Additional metadata
        
    Returns:
        Standardized response dictionary
    """
    response = {
        "success": success,
        "message": message,
        "data": data,
        "error": ErrorDetails(**error) if error else None,
        "metadata": ResponseMetadata(**(metadata or {}))
    }
    
    return response

def paginated_response(
    success: bool,
    message: str,
    items: List[Any],
    total_count: int,
    page: int,
    page_size: int,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized paginated API response.
    
    Args:
        success: Whether the operation was successful
        message: Human-readable response message
        items: List of items
        total_count: Total number of items
        page: Current page number
        page_size: Number of items per page
        metadata: Additional metadata
        
    Returns:
        Standardized paginated response dictionary
    """
    pages = (total_count + page_size - 1) // page_size if page_size > 0 else 0
    
    response = create_response(
        success=success,
        message=message,
        data=items,
        metadata=metadata
    )
    
    response["pagination"] = PaginatedResponseMetadata(
        total_count=total_count,
        page_size=page_size,
        page=page,
        pages=pages,
        has_next=page < pages,
        has_prev=page > 1
    )
    
    return response

def error_response(
    message: str,
    code: str = "INTERNAL_ERROR",
    details: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    path: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a standardized error response.
    
    Args:
        message: Error message
        code: Error code
        details: Additional error details
        trace_id: Trace ID for error tracking
        path: Path where the error occurred
        metadata: Additional metadata
        
    Returns:
        Standardized error response dictionary
    """
    error = {
        "code": code,
        "message": message,
        "details": details,
        "trace_id": trace_id,
        "path": path
    }
    
    return create_response(
        success=False,
        message=message,
        error=error,
        metadata=metadata
    )

# Export key types
__all__ = [
    'APIResponse',
    'PaginatedResponse',
    'ErrorDetails',
    'ResponseMetadata',
    'PaginatedResponseMetadata',
    'create_response',
    'paginated_response',
    'error_response'
]
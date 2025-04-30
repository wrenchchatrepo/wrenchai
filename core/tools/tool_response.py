"""Tool response standardization for WrenchAI.

This module provides standardized response format for tools, ensuring
consistent response structure across different tool implementations.
"""

from typing import Dict, Any, Optional, Union, List, TypeVar, Generic
from pydantic import BaseModel, Field
from datetime import datetime

T = TypeVar('T')  # Generic type for tool data

class ToolResponse(BaseModel, Generic[T]):
    """Standardized response format for all tools."""
    success: bool = Field(..., description="Whether the operation was successful")
    data: Optional[T] = Field(None, description="Operation result data")
    error: Optional[str] = Field(None, description="Error message if operation failed")
    meta: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        """Pydantic model configuration."""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

def format_success_response(data: Any = None, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format a successful tool response.
    
    Args:
        data: The operation result data
        meta: Additional metadata to include
        
    Returns:
        Standardized success response dictionary
    """
    response = ToolResponse[
        type(data) if data is not None else None  # Use the actual data type if available
    ](
        success=True,
        data=data,
        meta=meta or {},
        timestamp=datetime.utcnow()
    )
    return response.dict(exclude_unset=True)

def format_error_response(error_message: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Format an error tool response.
    
    Args:
        error_message: Error message describing what went wrong
        meta: Additional metadata to include
        
    Returns:
        Standardized error response dictionary
    """
    response = ToolResponse[
        None  # No data for error responses
    ](
        success=False,
        error=error_message,
        meta=meta or {},
        timestamp=datetime.utcnow()
    )
    return response.dict(exclude_unset=True)

def standardize_legacy_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a legacy tool response to the standardized format.
    
    Args:
        response: Legacy tool response dictionary
        
    Returns:
        Standardized response dictionary
    """
    # Check if response is already in the standardized format
    if all(k in response for k in ["success", "data"]) or \
       all(k in response for k in ["success", "error"]):
        # Add timestamp if missing
        if "timestamp" not in response:
            response["timestamp"] = datetime.utcnow().isoformat()
        return response
    
    # Handle legacy success responses
    if "error" not in response:
        # Extract data from legacy format
        data = response.copy()
        # Remove common status fields from data
        for field in ["success", "status", "message"]:
            if field in data:
                data.pop(field)
        
        return format_success_response(
            data=data,
            meta={
                "original_response": response,
                "converted_from_legacy": True
            }
        )
    
    # Handle legacy error responses
    error_message = response.get("error", "Unknown error")
    return format_error_response(
        error_message=error_message,
        meta={
            "original_response": response,
            "converted_from_legacy": True
        }
    )
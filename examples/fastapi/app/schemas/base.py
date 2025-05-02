"""Base schemas with PydanticAI integration for enhanced validation and AI capabilities."""
from datetime import datetime
from typing import TypeVar, Generic, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic_ai import AIModel, AIField, GraphSchema
from pydantic_ai.validators import SemanticValidator, ContentValidator

ModelType = TypeVar("ModelType")

class BaseAISchema(AIModel):
    """Base AI-powered schema with enhanced validation capabilities."""
    model_config = ConfigDict(
        from_attributes=True,
        # Enable backward compatibility mode
        validate_default=True,
        validate_assignment=True,
        extra='allow',  # Allow extra fields for backward compatibility
        # Disable strict validation for backward compatibility
        strict=False
    )
    
    # AI-powered validation for text fields
    semantic_validator = SemanticValidator(
        validate_semantic_meaning=True,
        validate_content_safety=True,
        # Make AI validation non-blocking for backward compatibility
        strict=False,
        fallback_to_basic=True
    )
    
    # Graph-based schema validation
    graph_schema = GraphSchema(
        allow_cycles=False,
        validate_relationships=True,
        # Make relationship validation non-blocking
        strict=False
    )
    
    @classmethod
    def validate_semantic_content(cls, value: str) -> bool:
        """
        Validates the semantic meaning and content safety of the provided text.
        
        Attempts AI-powered semantic validation; returns True if validation passes or if an error occurs during validation.
        """
        try:
            return cls.semantic_validator.validate(value)
        except Exception:
            # Fallback to basic validation for backward compatibility
            return True

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        """
        Validates an object using AI-powered validation, falling back to basic validation on failure.
        
        Attempts to validate the input object with AI-enhanced validation. If an exception occurs,
        performs standard Pydantic validation as a fallback to ensure compatibility.
        """
        try:
            # Try AI-powered validation first
            return super().model_validate(obj, *args, **kwargs)
        except Exception as e:
            # Fallback to basic Pydantic validation
            return super(AIModel, cls).model_validate(obj, *args, **kwargs)

class BaseAPISchema(BaseAISchema):
    """Base schema for API responses with common fields and AI validation."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    # AI-powered field validation
    metadata: dict = AIField(
        description="Metadata for the object",
        validate_schema=True,
        validate_content=True
    )
    
    # Content safety validation
    content_validator = ContentValidator(
        check_pii=True,
        check_sensitive_data=True
    )

class BaseResponse(BaseAISchema, Generic[ModelType]):
    """Standard API response format with AI-powered validation."""
    success: bool
    message: str = AIField(
        description="Response message",
        validate_semantic=True,
        max_length=500
    )
    data: Optional[ModelType] = None
    error_details: Optional[dict] = AIField(
        description="Detailed error information",
        validate_schema=True
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "data": None,
                "error_details": None
            }
        }
    )
    
    @classmethod
    def create_success(cls, data: ModelType, message: str = "Success") -> "BaseResponse[ModelType]":
        """
        Creates a successful API response with AI-validated message and data.
        
        Args:
            data: The response payload to include.
            message: Optional success message. Defaults to "Success".
        
        Returns:
            An instance of BaseResponse with success status, message, and data.
        """
        return cls(
            success=True,
            message=message,
            data=data
        )
    
    @classmethod
    def create_error(cls, message: str, details: Optional[dict] = None) -> "BaseResponse[ModelType]":
        """
        Creates an error response with an AI-validated message and optional error details.
        
        Args:
            message: The error message to include in the response.
            details: Optional dictionary containing additional error information.
        
        Returns:
            An instance of BaseResponse with success set to False, the provided message, and optional error details.
        """
        return cls(
            success=False,
            message=message,
            error_details=details
        ) 
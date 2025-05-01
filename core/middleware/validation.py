"""
API input validation middleware.

This module provides validation middleware for API requests
with consistent error formats and enhanced validation.
"""

import logging
from fastapi import Request, Response, FastAPI
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from typing import Dict, Any, Callable, Type, TypeVar, Optional, List, Union
import traceback
import uuid
import json
import time
from datetime import datetime

# Import response utilities
from core.schemas.responses import error_response

# Set up logging
logger = logging.getLogger(__name__)

# Type variables for validation
T = TypeVar('T')

class ValidationException(Exception):
    """Exception raised for validation errors."""
    
    def __init__(
        self, 
        message: str, 
        code: str = "VALIDATION_ERROR",
        details: Optional[Dict[str, Any]] = None,
        path: Optional[str] = None
    ):
        """Initialize a validation exception.
        
        Args:
            message: Error message
            code: Error code
            details: Additional error details
            path: Path where error occurred
        """
        self.message = message
        self.code = code
        self.details = details or {}
        self.path = path
        super().__init__(message)

def pydantic_error_to_detail(error: ValidationError) -> List[Dict[str, Any]]:
    """Convert Pydantic validation error to detailed error list.
    
    Args:
        error: Pydantic validation error
        
    Returns:
        List of detailed error dictionaries
    """
    return [
        {
            "location": [loc for loc in err["loc"]],
            "message": err["msg"],
            "type": err["type"]
        }
        for err in error.errors()
    ]

async def validate_request_body(
    request: Request, 
    model: Type[T]
) -> Union[T, Dict[str, Any]]:
    """Validate request body against Pydantic model.
    
    Args:
        request: FastAPI request
        model: Pydantic model for validation
        
    Returns:
        Validated model instance or error response
        
    Raises:
        ValidationException: If validation fails
    """
    try:
        # Read request body
        body = await request.json()
        
        # Validate against model
        validated_data = model.parse_obj(body)
        return validated_data
    
    except ValidationError as e:
        # Convert validation error to detailed format
        details = pydantic_error_to_detail(e)
        
        error = error_response(
            message="Validation error in request body",
            code="VALIDATION_ERROR",
            details={"validation_errors": details},
            path=request.url.path
        )
        
        logger.warning(f"Validation error in request to {request.url.path}: {details}")
        
        raise ValidationException(
            message="Validation error in request body",
            code="VALIDATION_ERROR",
            details={"validation_errors": details},
            path=request.url.path
        )
        
    except json.JSONDecodeError:
        # Handle invalid JSON
        logger.warning(f"Invalid JSON in request to {request.url.path}")
        
        raise ValidationException(
            message="Invalid JSON in request body",
            code="INVALID_JSON",
            path=request.url.path
        )
    
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error validating request to {request.url.path}: {str(e)}")
        
        raise ValidationException(
            message=f"Error validating request: {str(e)}",
            code="VALIDATION_ERROR",
            path=request.url.path
        )

class ValidationMiddleware:
    """Middleware for request validation and error handling."""
    
    def __init__(self, app: FastAPI):
        """Initialize validation middleware.
        
        Args:
            app: FastAPI application
        """
        self.app = app
    
    async def __call__(self, request: Request, call_next: Callable) -> Response:
        """Process request with validation.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
            
        Returns:
            FastAPI response
        """
        try:
            # Start timer for request processing
            start_time = time.time()
            
            # Generate request ID for tracking
            request_id = str(uuid.uuid4())
            request.state.request_id = request_id
            
            # Process request with next middleware
            response = await call_next(request)
            
            # Add request processing time to response headers
            processing_time = time.time() - start_time
            response.headers["X-Process-Time"] = str(processing_time)
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except ValidationException as e:
            # Handle validation exceptions
            return JSONResponse(
                status_code=400,
                content=error_response(
                    message=e.message,
                    code=e.code,
                    details=e.details,
                    trace_id=getattr(request.state, "request_id", None),
                    path=e.path or request.url.path
                )
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            logger.error(f"Unexpected error processing request: {str(e)}")
            logger.error(traceback.format_exc())
            
            return JSONResponse(
                status_code=500,
                content=error_response(
                    message="Internal server error",
                    code="INTERNAL_ERROR",
                    details={"error": str(e)} if logger.level <= logging.DEBUG else None,
                    trace_id=getattr(request.state, "request_id", None),
                    path=request.url.path
                )
            )

def add_validation_middleware(app: FastAPI) -> None:
    """Add validation middleware to FastAPI application.
    
    Args:
        app: FastAPI application
    """
    app.middleware("http")(ValidationMiddleware(app))
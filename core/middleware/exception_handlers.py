"""
Global exception handlers for API.

This module provides global exception handlers for FastAPI
to ensure consistent error responses throughout the API.
"""

import logging
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from typing import Dict, Any

from core.schemas.responses import error_response

# Set up logging
logger = logging.getLogger(__name__)

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions.
    
    Args:
        request: FastAPI request
        exc: HTTP exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.warning(f"HTTP exception ({exc.status_code}): {exc.detail} - Path: {request.url.path}")
    
    # Map HTTP status codes to error codes
    status_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE"
    }
    
    error_code = status_code_map.get(exc.status_code, f"ERROR_{exc.status_code}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=str(exc.detail),
            code=error_code,
            trace_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            details=exc.headers  # Include headers in details
        )
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation exceptions.
    
    Args:
        request: FastAPI request
        exc: Validation exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # Convert validation errors to detailed format
    error_details = []
    for error in exc.errors():
        location = error.get("loc", [])
        location_str = " -> ".join([str(loc) for loc in location if loc != "body"])
        
        error_details.append({
            "field": location_str or "request",
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "validation_error")
        })
    
    logger.warning(f"Validation error in request to {request.url.path}: {error_details}")
    
    return JSONResponse(
        status_code=422,
        content=error_response(
            message="Request validation error",
            code="VALIDATION_ERROR",
            details={"validation_errors": error_details},
            trace_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )
    )

async def pydantic_validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """Handle Pydantic validation exceptions.
    
    Args:
        request: FastAPI request
        exc: Validation exception
        
    Returns:
        JSONResponse with standardized error format
    """
    # Convert validation errors to detailed format
    error_details = []
    for error in exc.errors():
        location = error.get("loc", [])
        location_str = " -> ".join([str(loc) for loc in location])
        
        error_details.append({
            "field": location_str or "request",
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "validation_error")
        })
    
    logger.warning(f"Pydantic validation error: {error_details}")
    
    return JSONResponse(
        status_code=422,
        content=error_response(
            message="Data validation error",
            code="VALIDATION_ERROR",
            details={"validation_errors": error_details},
            trace_id=getattr(request.state, "request_id", None),
            path=request.url.path
        )
    )

async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle generic exceptions.
    
    Args:
        request: FastAPI request
        exc: Exception
        
    Returns:
        JSONResponse with standardized error format
    """
    logger.error(f"Unhandled exception in request to {request.url.path}: {str(exc)}")
    logger.error(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content=error_response(
            message="Internal server error",
            code="INTERNAL_ERROR",
            trace_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            # In production, don't expose error details to clients
            details={"error": str(exc)} if logger.level <= logging.DEBUG else None
        )
    )

def add_exception_handlers(app: FastAPI) -> None:
    """Add exception handlers to FastAPI application.
    
    Args:
        app: FastAPI application
    """
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, pydantic_validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
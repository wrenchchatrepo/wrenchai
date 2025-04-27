"""Request logging middleware for FastAPI."""
from fastapi import FastAPI, Request
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Awaitable, Callable
import time
import uuid

from core.tools.logger import logger

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Request]]
    ) -> Request:
        """Process and log request/response cycle.
        
        Args:
            request: The incoming request
            call_next: Function to call the next middleware/route handler
            
        Returns:
            The response from the route handler
        """
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Start timing
        start_time = time.time()
        
        # Extract request details
        request_details = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
            "path_params": dict(request.path_params),
            "query_params": dict(request.query_params)
        }
        
        # Log request
        logger.info(
            "Incoming request",
            extra=request_details
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful response
            logger.info(
                "Request completed",
                extra={
                    **request_details,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed request
            duration = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    **request_details,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_ms": round(duration * 1000, 2)
                }
            )
            raise

def setup_request_logging(app: FastAPI) -> None:
    """Set up request logging middleware for FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    app.add_middleware(RequestLoggingMiddleware) 